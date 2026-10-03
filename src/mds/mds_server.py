"""
MOSIP Device Service (MDS) Server
Conforms to the MOSIP Device Service (MDS) REST architecture:
- GET  /info       : Device discovery, status, L0/L1 level, digital ID
- GET  /stream     : Multipart JPEG video frame stream with real-time UI guidance overlay
- POST /capture    : Biometric capture endpoint returning ISO biometric data & PAD token
- POST /configure  : Runtime configuration for thresholds and workflows
- POST /switch-device : Switch between Physical Webcam (L0) and Mock L0 Simulator
"""

import base64
import time
import hashlib
import cv2
import numpy as np
from fastapi import FastAPI, Response, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from ..devices.base import FaceCaptureDevice, DeviceType, DeviceStatus, MockScenario, VendorL1Adapter
from ..devices.webcam_device import WebcamCaptureDevice
from ..devices.mock_l0_device import MockL0Device
from ..core.pipeline import LivenessPipeline, PipelineState, LivenessDecision
from ..core.config import LivenessConfig, WorkflowType, PADMode
from ..core.errors import BiometricErrorCode
from ..ui.desktop_client import DesktopRegistrationClient

app = FastAPI(
    title="MOSIP Device Service (MDS) - Face Liveness & PAD Subsystem",
    description="Local biometric device service adapter aligning with MOSIP Device Service 0.9.5 / 1.2.0 principles",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global device and pipeline instances
device: FaceCaptureDevice = MockL0Device()
pipeline = LivenessPipeline()
ui_renderer = DesktopRegistrationClient(use_mock_device=True)


class CaptureRequest(BaseModel):
    workflow: str = Field(default="RESIDENT_REGISTRATION", description="RESIDENT_REGISTRATION, OPERATOR_AUTHENTICATION, or SUPERVISOR_AUTHENTICATION")
    resident_id: Optional[str] = Field(default=None, description="Resident identifier for registration workflow (e.g. RES-00123)")
    timeout_seconds: int = Field(default=15, ge=2, le=60, description="Session timeout in seconds")


class ConfigureRequest(BaseModel):
    passive_threshold: Optional[float] = Field(default=None, ge=0.1, le=0.99)
    min_challenges: Optional[int] = Field(default=None, ge=1, le=5)
    challenge_timeout: Optional[float] = Field(default=None, ge=2.0, le=30.0)
    max_retries: Optional[int] = Field(default=None, ge=1, le=5)
    pad_mode: Optional[str] = Field(default=None, description="AUTO, HEURISTIC, or ONNX")


class DeviceSwitchRequest(BaseModel):
    device_mode: str = Field(default="MOCK", description="'MOCK' or 'WEBCAM'")
    scenario: Optional[str] = Field(default="BONA_FIDE_LIVE", description="Mock scenario if switching to MOCK")


@app.on_event("startup")
def startup_event():
    global device
    device.connect()


@app.on_event("shutdown")
def shutdown_event():
    global device
    device.disconnect()


@app.get("/", response_class=HTMLResponse)
def index_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>MOSIP Liveness & PAD Console</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1117; color: #e1e4ea; margin: 0; padding: 24px; }
            .container { max-width: 1040px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3139; padding-bottom: 16px; margin-bottom: 24px; }
            .logo { font-size: 24px; font-weight: 700; color: #ff5722; }
            .badge { background: #262c36; color: #00e676; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600; }
            .main-grid { display: grid; grid-template-columns: 1fr 340px; gap: 24px; }
            .video-card { background: #181b22; border-radius: 12px; padding: 16px; border: 1px solid #262c36; text-align: center; }
            .video-card img { width: 100%; max-height: 480px; border-radius: 8px; border: 1px solid #333a46; }
            .controls-card { background: #181b22; border-radius: 12px; padding: 20px; border: 1px solid #262c36; }
            .section-title { font-size: 13px; text-transform: uppercase; color: #8b949e; letter-spacing: 0.5px; margin-bottom: 8px; font-weight: 600; }
            .btn { width: 100%; padding: 11px; border-radius: 6px; border: none; font-weight: 600; font-size: 13px; cursor: pointer; margin-bottom: 8px; transition: 0.2s; }
            .btn-primary { background: #ff5722; color: #fff; }
            .btn-primary:hover { background: #f4511e; }
            .btn-secondary { background: #262c36; color: #e1e4ea; border: 1px solid #3a4250; }
            .btn-secondary:hover { background: #323a46; }
            .metric-box { background: #0f1117; padding: 10px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #262c36; }
            .metric-label { font-size: 11px; color: #8b949e; }
            .metric-val { font-size: 16px; font-weight: 600; margin-top: 4px; color: #00e676; }
            select { width: 100%; padding: 9px; background: #0f1117; border: 1px solid #3a4250; color: #fff; border-radius: 6px; margin-bottom: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <span class="logo">MOSIP DEC{}DE</span>
                    <span style="color: #8b949e; margin-left: 12px; font-size: 15px;">Face Liveness & PAD Subsystem</span>
                </div>
                <span class="badge">● L0/L1 MDS ONLINE</span>
            </div>
            <div class="main-grid">
                <div class="video-card">
                    <img src="/stream" alt="Live MOSIP Video Stream">
                    <p style="color: #8b949e; font-size: 13px; margin-top: 12px;">Conforms to ISO/IEC 30107 & ISO/IEC 19794-5 Principles</p>
                </div>
                <div class="controls-card">
                    <div class="section-title">Workflow Profile</div>
                    <select id="wfSelect">
                        <option value="RESIDENT_REGISTRATION">Resident Registration</option>
                        <option value="OPERATOR_AUTHENTICATION">Operator Authentication</option>
                        <option value="SUPERVISOR_AUTHENTICATION">Supervisor Authentication</option>
                    </select>

                    <div class="section-title">Resident ID (Enrollment)</div>
                    <input type="text" id="resIdInput" value="RES-00123" style="width: 95%; padding: 8px; background: #0f1117; border: 1px solid #3a4250; color: #fff; border-radius: 6px; margin-bottom: 12px; font-weight: 600;">

                    <div class="section-title">Device Source</div>
                    <button class="btn btn-secondary" onclick="switchDevice('MOCK', 'BONA_FIDE_LIVE')">Mock Simulator (Live Face)</button>
                    <button class="btn btn-secondary" onclick="switchDevice('MOCK', 'STATIC_PHOTO_ATTACK')">Mock Simulator (Photo Spoof)</button>
                    <button class="btn btn-secondary" onclick="switchDevice('WEBCAM', '')">Switch to Live Webcam L0</button>
                    <button class="btn btn-secondary" onclick="switchDevice('L1', '')">Switch to Vendor L1 Adapter (Simulated)</button>

                    <div class="section-title" style="margin-top: 14px;">Biometric Capture</div>
                    <button class="btn btn-primary" onclick="triggerCapture()">Trigger POST /capture</button>

                    <div class="section-title" style="margin-top: 14px;">Capture Result</div>
                    <div class="metric-box">
                        <div class="metric-label">Status</div>
                        <div class="metric-val" id="resStatus">Ready</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Decision</div>
                        <div class="metric-val" id="resDecision" style="font-size: 13px; color: #fff;">-</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Enrollment Record</div>
                        <div class="metric-val" id="resEnroll" style="font-size: 13px; color: #fff;">-</div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            async function switchDevice(mode, scenario) {
                await fetch('/switch-device', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_mode: mode, scenario: scenario})
                });
                location.reload();
            }
            async function triggerCapture() {
                const wf = document.getElementById('wfSelect').value;
                const residentId = document.getElementById('resIdInput').value;
                document.getElementById('resStatus').innerText = 'Capturing...';
                document.getElementById('resStatus').style.color = '#ff9800';
                try {
                    const res = await fetch('/capture', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({workflow: wf, resident_id: residentId, timeout_seconds: 15})
                    });
                    const data = await res.json();
                    document.getElementById('resStatus').innerText = data.responseStatus;
                    document.getElementById('resDecision').innerText = data.decision || data.reason || 'Completed';
                    document.getElementById('resEnroll').innerText = (data.residentId ? data.residentId + ' [' + (data.enrollmentStatus || 'DONE') + ']' : '-');
                    if (data.responseStatus === 'SUCCESS') {
                        document.getElementById('resStatus').style.color = '#00e676';
                    } else {
                        document.getElementById('resStatus').style.color = '#f44336';
                    }
                } catch(e) {
                    document.getElementById('resStatus').innerText = 'ERROR';
                    document.getElementById('resStatus').style.color = '#f44336';
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/info")
def get_device_info():
    """
    MOSIP Device Discovery endpoint (/info).
    Reports device hardware specifications, capabilities, and security level.
    """
    info = device.get_device_info()
    caps = device.get_capabilities()
    return {
        "deviceId": info.device_id,
        "deviceSubId": [1],
        "deviceStatus": info.status.value,
        "deviceType": info.device_type.value,
        "vendor": caps.vendor,
        "model": caps.model,
        "firmware": info.firmware_version,
        "serialNumber": info.serial_number,
        "certification": "L1" if info.is_l1_secure else "L0",
        "securityLevel": caps.security_level,
        "serviceVersion": "MDS_1.3.0",
        "specVersion": "MOSIP_MDS_0.9.5",
        "purpose": ["REGISTRATION", "AUTH"],
        "supportedCaptureModes": caps.supported_capture_modes,
        "supportedResolutions": caps.supported_resolutions,
        "livenessCapability": {
            "passivePAD": caps.liveness_capabilities.get("passive_pad", True),
            "padOperationalMode": pipeline.pad_detector.operational_mode,
            "activeChallenges": ["BLINK", "SMILE", "TURN_LEFT", "TURN_RIGHT"],
            "hardwareLiveness": caps.liveness_capabilities.get("hardware_liveness", False),
            "offlineCapable": True
        }
    }


@app.post("/switch-device")
def switch_device(req: DeviceSwitchRequest):
    """Switch between Physical Webcam (L0), Vendor L1 Adapter, and Mock L0 Simulator."""
    global device
    device.disconnect()
    mode = req.device_mode.upper()
    if mode == "WEBCAM":
        device = WebcamCaptureDevice(0)
    elif mode in ("L1", "L1_VENDOR", "VENDOR_L1"):
        device = VendorL1Adapter()
    else:
        try:
            scenario_enum = MockScenario(req.scenario)
        except ValueError:
            scenario_enum = MockScenario.BONA_FIDE_LIVE
        device = MockL0Device(scenario=scenario_enum)

    device.connect()
    return {"status": "SUCCESS", "current_device": device.get_device_info().device_id}


@app.post("/configure")
def configure_subsystem(req: ConfigureRequest):
    """Update runtime thresholds and policies."""
    if req.passive_threshold is not None:
        pipeline.policy.passive_threshold = req.passive_threshold
    if req.min_challenges is not None:
        pipeline.policy.min_challenges = req.min_challenges
    if req.challenge_timeout is not None:
        pipeline.policy.challenge_timeout_seconds = req.challenge_timeout
    if req.max_retries is not None:
        pipeline.policy.max_retries = req.max_retries
    if req.pad_mode is not None:
        try:
            pipeline.pad_detector.mode = PADMode(req.pad_mode.upper())
        except ValueError:
            pass

    return {
        "status": "SUCCESS",
        "configured_policy": {
            "passive_threshold": pipeline.policy.passive_threshold,
            "min_challenges": pipeline.policy.min_challenges,
            "challenge_timeout": pipeline.policy.challenge_timeout_seconds,
            "max_retries": pipeline.policy.max_retries,
            "pad_mode": pipeline.pad_detector.operational_mode
        }
    }


@app.get("/stream")
def stream_frames():
    """Multipart MJPEG video stream with real-time biometric guidance overlay."""
    def frame_generator():
        for frame in device.start_stream():
            step_result = pipeline.process_frame(frame)
            ui_renderer.use_mock_device = (device.get_device_info().device_type == DeviceType.MOCK_L0_SIMULATOR)
            ui_renderer.workflow = pipeline.workflow
            display = ui_renderer.draw_ui_overlay(frame.image, step_result)

            ret, buffer = cv2.imencode('.jpg', display)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/capture")
def capture_biometric(request: CaptureRequest):
    """
    MOSIP Biometric Capture Endpoint.
    Executes hybrid Passive -> Active verification loop.
    Returns ISO 19794-5 image and PAD token on success.
    """
    try:
        wf = WorkflowType(request.workflow)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow '{request.workflow}'. Allowed: {[w.value for w in WorkflowType]}"
        )

    if not device.is_connected():
        if not device.connect():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Biometric capture device is disconnected or unavailable."
            )

    pipeline.set_workflow(wf)
    pipeline.reset()

    start_time = time.time()
    last_result = None

    while (time.time() - start_time) < request.timeout_seconds:
        success, frame = device.read_frame()
        if not success or frame is None:
            time.sleep(0.02)
            continue

        result = pipeline.process_frame(frame)
        last_result = result

        # In mock simulator mode, automatically simulate successful challenge completion
        if isinstance(device, MockL0Device) and device.scenario == MockScenario.BONA_FIDE_LIVE:
            if result.state == PipelineState.ACTIVE_CHALLENGE and pipeline.challenge_manager.active_challenge_state:
                pipeline.challenge_manager.active_challenge_state.is_completed = True

        if result.state == PipelineState.CAPTURE_SUCCESS:
            _, buffer = cv2.imencode('.jpg', result.captured_face_image)
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            token_hash = hashlib.sha256(result.captured_face_image.tobytes()).hexdigest()
            meta = result.pad_result.model_metadata if result.pad_result else None
            
            return {
                "responseStatus": "SUCCESS",
                "decision": result.decision.value,
                "residentId": request.resident_id or "RES-00123",
                "enrollmentStatus": "COMPLETED" if wf == WorkflowType.RESIDENT_REGISTRATION else "AUTHENTICATED",
                "biometrics": [{
                    "specVersion": "ISO_19794_5",
                    "specFormat": "ISO/IEC 19794-5-aligned representation (Application JPEG/Base64)",
                    "data": img_b64,
                    "mimeType": "image/jpeg",
                    "tokenHash": token_hash,
                    "livenessVerified": True,
                    "passiveConfidence": result.pad_result.liveness_score if result.pad_result else 0.92,
                    "presentationAttackDetected": False
                }],
                "telemetry": {
                    "totalDurationSeconds": round(time.time() - start_time, 2),
                    "challengesCompleted": [c.value for c in pipeline.challenge_manager.completed_challenges],
                    "workflow": wf.value,
                    "padMode": result.pad_result.mode_used if result.pad_result else "HEURISTIC",
                    "modelProvenance": {
                        "backend": meta.backend_name if meta else "heuristic_multi_cue",
                        "version": meta.version if meta else "v1.2.0-heuristic",
                        "modelHash": meta.model_hash if meta else "N/A",
                        "provider": meta.inference_provider if meta else "CPU"
                    }
                }
            }

        elif result.state in (PipelineState.ATTACK_REJECTED, PipelineState.MAX_RETRIES_EXCEEDED):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "responseStatus": "FAILURE",
                    "decision": result.decision.value,
                    "residentId": request.resident_id or "RES-00123",
                    "enrollmentStatus": "REJECTED" if result.state == PipelineState.ATTACK_REJECTED else "FAILED",
                    "reason": result.status_text,
                    "detailedGuidance": result.detailed_guidance,
                    "attackType": result.pad_result.attack_type if result.pad_result else "UNKNOWN",
                    "biometrics": []
                }
            )

        time.sleep(0.01)

    # Session timeout
    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content={
            "responseStatus": "TIMEOUT",
            "decision": LivenessDecision.FAILED.value,
            "reason": "Biometric capture session timed out.",
            "biometrics": []
        }
    )


def start_server(host: str = "127.0.0.1", port: int = 4501):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
