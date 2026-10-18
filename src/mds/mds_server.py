"""Loopback research API. This service is not a certified MOSIP SBI implementation."""
import base64
import copy
import hashlib
import os
import secrets
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Literal

import cv2
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..devices.base import DeviceType, MockScenario, VendorL1Adapter
from ..devices.webcam_device import WebcamCaptureDevice
from ..devices.mock_l0_device import MockL0Device
from ..core.pipeline import LivenessPipeline, PipelineState
from ..core.config import LivenessConfig, WorkflowType, PADMode, ChallengeType
from ..core.metrics import OperationalMetrics

API_TOKEN = os.environ.get("MOSIP_MDS_API_TOKEN") or secrets.token_urlsafe(32)
device = MockL0Device()
_packaged_model = Path(__file__).resolve().parents[2] / "assets/models/minifasnet_v2.onnx"
_model_path = os.environ.get("MOSIP_PAD_MODEL", str(_packaged_model))
_model_present = Path(_model_path).is_file()
pipeline = LivenessPipeline(LivenessConfig(
    onnx_model_path=_model_path if _model_present else None,
    pad_mode=PADMode(os.environ.get("MOSIP_PAD_MODE", "ONNX" if _model_present or "MOSIP_PAD_MODEL" in os.environ else "HEURISTIC")),
))
metrics = OperationalMetrics()
_device_lock = threading.RLock()
_capture_lock = threading.Lock()
_latest_jpeg = None
_status = {"state": "IDLE", "guidance": "Choose a device and start verification.", "progress": 0}
_origins = ["http://127.0.0.1:4501", "http://localhost:4501"]


@asynccontextmanager
async def lifespan(app):
    device.connect()
    try:
        yield
    finally:
        device.disconnect()
        pipeline._captured_biometric = None
        pipeline.active_detector.close()


app = FastAPI(title="Face liveness research API", version="2.0.0", lifespan=lifespan,
              description="Custom offline research API. No claim of MOSIP SBI conformance.")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])


@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    for name, value in {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                        "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"}.items():
        response.headers[name] = value
    return response


_bearer = HTTPBearer(auto_error=False, scheme_name="LocalApiToken")


def authorize(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)):
    if request.headers.get("origin") and request.headers["origin"] not in _origins:
        raise HTTPException(403, "This origin is not allowed.")
    if credentials is None or not secrets.compare_digest(credentials.credentials, API_TOKEN):
        raise HTTPException(401, "A local API bearer token is required.")


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaptureRequest(StrictRequest):
    workflow: str = "RESIDENT_REGISTRATION"
    resident_id: Optional[str] = Field(default=None, max_length=64)
    timeout_seconds: int = Field(default=15, ge=2, le=60)


class ConfigureRequest(StrictRequest):
    liveness_enabled: Optional[bool] = None
    guidance_messages: Optional[dict[str, str]] = Field(default=None, max_length=16)
    workflow: WorkflowType = WorkflowType.RESIDENT_REGISTRATION
    passive_threshold: Optional[float] = Field(default=None, ge=0.46, le=0.99)
    min_challenges: Optional[int] = Field(default=None, ge=1, le=5)
    challenge_timeout: Optional[float] = Field(default=None, ge=2, le=30)
    max_retries: Optional[int] = Field(default=None, ge=0, le=5)
    pad_mode: Optional[PADMode] = None
    active_liveness_enabled: Optional[bool] = None
    require_active_challenges: Optional[bool] = None
    supported_challenges: Optional[list[ChallengeType]] = Field(default=None, min_length=1, max_length=6)

    @field_validator("guidance_messages")
    @classmethod
    def valid_guidance(cls, value):
        if value is not None and any(k not in {s.value for s in PipelineState} or len(v) > 300 for k, v in value.items()):
            raise ValueError("Use pipeline state names and guidance of at most 300 characters")
        return value


class DeviceSwitchRequest(StrictRequest):
    device_mode: Literal["MOCK", "WEBCAM", "L1"] = "MOCK"
    scenario: MockScenario = MockScenario.BONA_FIDE_LIVE


@app.get("/", response_class=HTMLResponse)
def index_page():
    return Path(__file__).with_name("console.html").read_text(encoding="utf-8").replace("__API_TOKEN__", API_TOKEN)


@app.get("/info")
def get_device_info():
    with _device_lock:
        info, caps = device.get_device_info(), device.get_capabilities()
        return {"deviceId": info.device_id, "deviceStatus": info.status.value,
            "deviceType": info.device_type.value, "vendor": caps.vendor, "model": caps.model,
            "securityLevel": caps.security_level, "certification": "NOT_CERTIFIED",
            "supportedCaptureModes": caps.supported_capture_modes,
            "supportedResolutions": caps.supported_resolutions, "serviceVersion": "2.0.0",
            "specVersion": "CUSTOM_RESEARCH_API_2", "nativeMosipIntegrationVerified": False,
            "simulation": info.device_type in (DeviceType.MOCK_L0_SIMULATOR, DeviceType.VENDOR_L1_ADAPTER),
            "captureBusy": _capture_lock.locked(),
            "livenessCapability": {"passivePAD": True,
                "padOperationalMode": pipeline.pad_detector.operational_mode,
                "padModelAvailable": pipeline.pad_detector._onnx_backend.is_available(),
                "activeChallenges": [c.value for c in pipeline.config.supported_challenges],
                "hardwareLiveness": False, "offlineCapable": True}}


@app.get("/status")
def capture_status():
    with _device_lock:
        return dict(_status)


@app.get("/metrics")
def operational_metrics():
    return metrics.snapshot()


@app.get("/configuration")
def configuration():
    return asdict(pipeline.config)


@app.post("/switch-device", dependencies=[Depends(authorize)])
def switch_device(req: DeviceSwitchRequest):
    global device, _latest_jpeg, _status
    if not _capture_lock.acquire(blocking=False):
        raise HTTPException(409, "Finish the current capture before changing devices.")
    try:
        with _device_lock:
            if req.device_mode == "WEBCAM" and isinstance(device, WebcamCaptureDevice):
                if not device.is_connected() and not device.connect():
                    raise HTTPException(503, "Camera unavailable. Check its connection and permissions.")
                pipeline.reset()
                _latest_jpeg = None
                return {"status": "SUCCESS", "current_device": device.get_device_info().device_id}
            candidate = (WebcamCaptureDevice(0) if req.device_mode == "WEBCAM" else
                         VendorL1Adapter() if req.device_mode == "L1" else MockL0Device(scenario=req.scenario))
            if not candidate.connect():
                candidate.disconnect()
                raise HTTPException(503, "Camera unavailable. Check its connection and permissions.")
            device.disconnect()
            device = candidate
            pipeline.reset()
            _latest_jpeg = None
            _status = {"state": "IDLE", "guidance": "Device ready. Start verification.", "progress": 0}
            return {"status": "SUCCESS", "current_device": device.get_device_info().device_id}
    finally:
        _capture_lock.release()


@app.post("/configure", dependencies=[Depends(authorize)])
def configure_subsystem(req: ConfigureRequest):
    if not _capture_lock.acquire(blocking=False):
        raise HTTPException(409, "Finish capture before changing policy.")
    try:
        with _device_lock:
            config = copy.deepcopy(pipeline.config)
            if req.liveness_enabled is not None:
                config.liveness_enabled = req.liveness_enabled
            if req.guidance_messages is not None:
                config.guidance_messages = req.guidance_messages
            policy = config.get_policy(req.workflow)
            changes = req.model_dump(exclude_none=True)
            for name in ("passive_threshold", "min_challenges", "max_retries",
                         "active_liveness_enabled", "require_active_challenges"):
                if name in changes:
                    setattr(policy, name, changes[name])
            if req.challenge_timeout is not None:
                policy.challenge_timeout_seconds = req.challenge_timeout
            policy.max_challenges = max(policy.max_challenges, policy.min_challenges)
            if policy.require_active_challenges and not policy.active_liveness_enabled:
                raise HTTPException(422, "Required active challenges cannot be disabled.")
            if req.supported_challenges is not None:
                config.supported_challenges = list(dict.fromkeys(req.supported_challenges))
            if req.pad_mode is not None:
                config.pad_mode = req.pad_mode
            pipeline.config = config
            pipeline.pad_detector.mode = config.pad_mode
            pipeline.set_workflow(req.workflow)
            return {"status": "SUCCESS", "configured_policy": {**asdict(policy),
                "challenge_timeout": policy.challenge_timeout_seconds,
                "pad_mode": pipeline.pad_detector.operational_mode,
                "supported_challenges": config.supported_challenges}}
    finally:
        _capture_lock.release()


@app.get("/stream")
def stream_frames():
    """Preview observes capture output without advancing liveness decisions."""
    def frames():
        while device.is_connected():
            with _device_lock:
                jpeg = _latest_jpeg if _capture_lock.locked() else None
                if not _capture_lock.locked():
                    ok, frame = device.read_frame()
                    if ok and frame is not None and frame.image.size:
                        encoded, buf = cv2.imencode(".jpg", frame.image)
                        if encoded:
                            jpeg = buf.tobytes()
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            time.sleep(1 / 15)
    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/capture", dependencies=[Depends(authorize)])
def capture_biometric(request: CaptureRequest):
    global _latest_jpeg, _status
    try:
        wf = WorkflowType(request.workflow)
    except ValueError:
        raise HTTPException(400, "Unknown capture workflow.")
    if not _capture_lock.acquire(blocking=False):
        raise HTTPException(409, "Another capture is already running.")
    start = time.monotonic()
    outcome, retries, challenge_seconds = "ERROR", 0, 0.0
    try:
        with _device_lock:
            if not device.is_connected() and not device.connect():
                raise HTTPException(503, "The capture device is unavailable.")
            pipeline.set_workflow(wf)
            simulation = device.get_device_info().device_type in (DeviceType.MOCK_L0_SIMULATOR, DeviceType.VENDOR_L1_ADAPTER)
        challenge_start = None
        while time.monotonic() - start < request.timeout_seconds:
            with _device_lock:
                ok, frame = device.read_frame()
                if not ok or frame is None:
                    outcome = "DEVICE_ERROR"
                    return JSONResponse(status_code=503, content={"responseStatus": outcome,
                        "reason": "Camera disconnected. Reconnect and start again.", "biometrics": [], "simulation": simulation})
                result = pipeline.process_frame(frame)
                retries = pipeline.challenge_manager.current_retry
                encoded, buf = cv2.imencode(".jpg", frame.image) if frame.image.size else (False, None)
                if encoded:
                    _latest_jpeg = buf.tobytes()
                challenge = pipeline.challenge_manager.active_challenge_state
                _status = {"state": result.state.value, "guidance": result.detailed_guidance,
                    "prompt": challenge.feedback_message if challenge else result.status_text,
                    "progress": result.progress, "retry": retries, "maxRetries": pipeline.policy.max_retries,
                    "simulation": simulation}
                if result.state == PipelineState.ACTIVE_CHALLENGE and challenge_start is None:
                    challenge_start = time.monotonic()
                if challenge_start is not None:
                    challenge_seconds = time.monotonic() - challenge_start
                if result.state == PipelineState.CAPTURE_SUCCESS:
                    encoded, image = cv2.imencode(".jpg", result.captured_face_image)
                    if not encoded:
                        raise HTTPException(503, "Captured image could not be encoded.")
                    payload, pad = image.tobytes(), result.pad_result
                    outcome = "SUCCESS"
                    return {"responseStatus": outcome, "decision": result.decision.value,
                        "residentId": request.resident_id, "simulation": simulation, "identityMatchPerformed": False,
                        "enrollmentStatus": "CAPTURED" if wf == WorkflowType.RESIDENT_REGISTRATION else "LIVENESS_VERIFIED",
                        "biometrics": [{"specVersion": "APPLICATION_JPEG", "mimeType": "image/jpeg",
                            "data": base64.b64encode(payload).decode("ascii"),
                            "tokenHash": hashlib.sha256(payload).hexdigest(), "livenessVerified": True,
                            "passiveConfidence": pad.liveness_score if pad else None, "presentationAttackDetected": False}],
                        "telemetry": {"workflow": wf.value, "totalDurationSeconds": time.monotonic() - start,
                            "challengesCompleted": [c.value for c in pipeline.challenge_manager.completed_challenges],
                            "padMode": pad.mode_used if pad else "UNKNOWN",
                            "modelProvenance": asdict(pad.model_metadata) if pad and pad.model_metadata else None}}
                if result.state in (PipelineState.ATTACK_REJECTED, PipelineState.MAX_RETRIES_EXCEEDED, PipelineState.DEVICE_ERROR):
                    outcome = "FAILURE"
                    return {"responseStatus": outcome, "decision": result.decision.value,
                        "reason": "Face verification could not be completed. Start a new session.",
                        "biometrics": [], "simulation": simulation}
            time.sleep(0.01)
        outcome = "TIMEOUT"
        # This is a completed verification outcome, not an HTTP request timeout.
        # Chromium can transparently retry HTTP 408, which would restart capture.
        return JSONResponse(status_code=200, content={"responseStatus": outcome,
            "reason": "Verification timed out. Follow the prompt and try again.", "biometrics": []})
    except HTTPException:
        raise
    except Exception:
        outcome = "ERROR"
        return JSONResponse(status_code=503, content={"responseStatus": outcome,
            "reason": "The capture device or engine is unavailable. Restart capture and check the device.",
            "biometrics": []})
    finally:
        with _device_lock:
            pipeline._captured_biometric = None
            _latest_jpeg = None
            _status = {**_status, "state": outcome, "progress": 1 if outcome == "SUCCESS" else 0}
        metrics.record(outcome, time.monotonic() - start, retries, challenge_seconds)
        _capture_lock.release()


def start_server(host="127.0.0.1", port=4501):
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError("The research service must bind to loopback.")
    import uvicorn
    uvicorn.run(app, host=host, port=port)
