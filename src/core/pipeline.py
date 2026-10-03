"""
Master Face Liveness & PAD Orchestration Pipeline
Implements the hybrid passive-active workflow defined in MOSIP Decode Problem 04:
1. Frame reception & device health check
2. Biometric quality assessment (ISO/IEC 19794-5)
3. Modular Passive Liveness & PAD assessment (ISO/IEC 30107) with temporal consistency window
4. Hybrid decision evaluation:
   - High Confidence Live -> Immediate CAPTURE_SUCCESS
   - Presentation Attack Detected -> REJECTED (Zero biometric leakage)
   - Uncertain / Borderline -> Automatic transition to dynamic active challenge
5. Dynamic active challenge execution with anti-replay baseline verification
6. Audit logging and privacy protection
"""

import time
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import cv2
import numpy as np

from .config import LivenessConfig, WorkflowType, WorkflowPolicy, LivenessDecision, PADVerdict, PADMode
from .face_detector import FaceQualityAssessor, DetectedFace, QualityMetrics
from .passive_pad import PassivePADDetector, PADResult
from .active_liveness import ActiveLivenessDetector, ChallengeState
from .challenge_manager import ChallengeManager
from .temporal_buffer import TemporalLivenessBuffer, TemporalAnalysisResult
from .errors import BiometricErrorCode, get_safe_user_message
from .audit_logger import BiometricAuditLogger, AuditEventType
from ..devices.base import VideoFrame


class PipelineState(str, Enum):
    IDLE = "IDLE"
    DEVICE_CONNECTING = "DEVICE_CONNECTING"
    FACE_DETECTION = "FACE_DETECTION"
    QUALITY_CHECK = "QUALITY_CHECK"
    PASSIVE_LIVENESS = "PASSIVE_LIVENESS"
    ACTIVE_CHALLENGE = "ACTIVE_CHALLENGE"
    CHALLENGE_VALIDATION = "CHALLENGE_VALIDATION"
    CAPTURE_SUCCESS = "CAPTURE_SUCCESS"
    ATTACK_REJECTED = "ATTACK_REJECTED"
    QUALITY_FAILURE = "QUALITY_FAILURE"
    ACTIVE_CHALLENGE_FAILURE = "ACTIVE_CHALLENGE_FAILURE"
    RETRY_PENDING = "RETRY_PENDING"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    DEVICE_ERROR = "DEVICE_ERROR"


@dataclass
class PipelineStepResult:
    state: PipelineState
    decision: LivenessDecision
    status_text: str
    detailed_guidance: str
    progress: float  # 0.0 to 1.0
    quality: Optional[QualityMetrics] = None
    pad_result: Optional[PADResult] = None
    active_challenge: Optional[ChallengeState] = None
    captured_face_image: Optional[np.ndarray] = None
    telemetry: Optional[Dict[str, Any]] = None
    error_code: Optional[BiometricErrorCode] = None
    can_retry: bool = True
    current_retry: int = 0
    max_retries: int = 3


class LivenessPipeline:
    def __init__(self,
                 config: Optional[LivenessConfig] = None,
                 workflow: WorkflowType = WorkflowType.RESIDENT_REGISTRATION,
                 session_id: Optional[str] = None):
        self.config = config or LivenessConfig()
        self.workflow = workflow
        self.policy: WorkflowPolicy = self.config.get_policy(workflow)
        self.session_id = session_id or str(uuid.uuid4())

        self.quality_assessor = FaceQualityAssessor(
            min_sharpness=self.config.min_sharpness,
            min_brightness=self.config.min_lighting_score,
            max_brightness=self.config.max_lighting_score
        )
        self.pad_detector = PassivePADDetector(
            onnx_model_path=self.config.onnx_model_path,
            mode=self.config.pad_mode,
            high_confidence_threshold=self.policy.passive_threshold,
            attack_threshold=self.config.pad_attack_rejection_threshold
        )
        self.active_detector = ActiveLivenessDetector()
        self.challenge_manager = ChallengeManager(self.policy, self.config.supported_challenges)
        self.temporal_buffer = TemporalLivenessBuffer(
            window_size=self.config.temporal_window_size,
            min_motion_threshold=self.config.min_motion_threshold
        )
        self.audit_logger = BiometricAuditLogger.get_logger()

        self.state: PipelineState = PipelineState.IDLE
        self._captured_biometric: Optional[np.ndarray] = None
        self._passive_frames_analyzed = 0
        self._state_start_time = time.time()
        self._last_face_box: Optional[Tuple[int, int, int, int]] = None

    def set_workflow(self, workflow: WorkflowType) -> None:
        self.workflow = workflow
        self.policy = self.config.get_policy(workflow)
        self.challenge_manager = ChallengeManager(self.policy, self.config.supported_challenges)
        self.reset()

    def reset(self) -> None:
        """Resets the pipeline for a fresh biometric verification session."""
        self.session_id = str(uuid.uuid4())
        self.state = PipelineState.FACE_DETECTION
        self._captured_biometric = None
        self._passive_frames_analyzed = 0
        self._state_start_time = time.time()
        self.challenge_manager.reset()
        self.temporal_buffer.clear()
        
        self.audit_logger.log_event(
            AuditEventType.CAPTURE_STARTED,
            session_id=self.session_id,
            workflow=self.workflow.value,
            details={"policy_passive_threshold": self.policy.passive_threshold}
        )

    def process_frame(self, frame: VideoFrame) -> PipelineStepResult:
        # 0. Frame Validation
        if frame is None or frame.image is None or frame.image.size == 0:
            self.state = PipelineState.DEVICE_ERROR
            return PipelineStepResult(
                state=self.state,
                decision=LivenessDecision.ERROR,
                status_text="Device Frame Error",
                detailed_guidance=get_safe_user_message(BiometricErrorCode.INVALID_FRAME),
                progress=0.0,
                error_code=BiometricErrorCode.INVALID_FRAME,
                can_retry=self.challenge_manager.can_retry(),
                current_retry=self.challenge_manager.current_retry,
                max_retries=self.policy.max_retries
            )

        bgr = frame.image
        h, w = bgr.shape[:2]

        # Extract landmarks and telemetry (MediaPipe 30 FPS)
        challenge_state = self.challenge_manager.active_challenge_state
        telemetry, updated_challenge = self.active_detector.process_frame(bgr, challenge_state)
        if challenge_state:
            self.challenge_manager.active_challenge_state = updated_challenge

        # 1. Face Detection & Quality Assessment (ISO/IEC 19794-5)
        known_box = telemetry.get("face_box")
        faces = self.quality_assessor.detect_faces(bgr, known_box=known_box)
        quality = self.quality_assessor.assess_quality(bgr, faces)

        # Handle face detection / quality errors
        if not quality.is_acceptable:
            err_code = BiometricErrorCode.NO_FACE
            if quality.face_count > 1:
                err_code = BiometricErrorCode.MULTIPLE_FACES
                status_text = "Multiple Faces Detected"
            elif quality.is_poorly_lit:
                err_code = BiometricErrorCode.POOR_LIGHTING_DARK
                status_text = "Adjust Lighting"
            elif quality.is_blurry:
                err_code = BiometricErrorCode.BLURRY_FACE
                status_text = "Hold Still"
            elif not quality.is_centered:
                err_code = BiometricErrorCode.FACE_NOT_CENTERED
                status_text = "Center Your Face"
            else:
                status_text = "Positioning face..."

            safe_guidance = quality.error_message or get_safe_user_message(err_code)

            if self.state == PipelineState.ACTIVE_CHALLENGE and self.challenge_manager.active_challenge_state:
                return PipelineStepResult(
                    state=self.state,
                    decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                    status_text=status_text,
                    detailed_guidance=safe_guidance,
                    progress=self.challenge_manager.active_challenge_state.progress,
                    quality=quality,
                    active_challenge=self.challenge_manager.active_challenge_state,
                    error_code=err_code,
                    can_retry=self.challenge_manager.can_retry(),
                    current_retry=self.challenge_manager.current_retry,
                    max_retries=self.policy.max_retries
                )

            self.state = PipelineState.FACE_DETECTION
            return PipelineStepResult(
                state=self.state,
                decision=LivenessDecision.ERROR,
                status_text=status_text,
                detailed_guidance=safe_guidance,
                progress=0.1,
                quality=quality,
                error_code=err_code,
                can_retry=self.challenge_manager.can_retry(),
                current_retry=self.challenge_manager.current_retry,
                max_retries=self.policy.max_retries
            )

        face = faces[0]
        face_box = (face.x, face.y, face.w, face.h)
        self._last_face_box = face_box

        # 2. State Machine: Transition from FACE_DETECTION to PASSIVE_LIVENESS
        if self.state in (PipelineState.IDLE, PipelineState.FACE_DETECTION):
            self.state = PipelineState.PASSIVE_LIVENESS
            self._passive_frames_analyzed = 0
            self._state_start_time = time.time()
            self.temporal_buffer.clear()

        # 3. PASSIVE LIVENESS & PAD EVALUATION
        if self.state == PipelineState.PASSIVE_LIVENESS:
            pad_result = self.pad_detector.evaluate_passive_liveness(bgr, face_box)

            # Update temporal sliding buffer
            self.temporal_buffer.add_frame(
                timestamp=time.time(),
                liveness_score=pad_result.liveness_score,
                is_live=pad_result.is_live,
                attack_detected=pad_result.attack_detected,
                ear=telemetry.get("ear", 0.3),
                smile_score=telemetry.get("smile_score", 0.0),
                yaw=telemetry.get("yaw", 0.0),
                pitch=telemetry.get("pitch", 0.0),
                face_center=telemetry.get("face_center", (w / 2.0, h / 2.0))
            )
            temp_analysis = self.temporal_buffer.analyze()

            # 1. Definite Presentation Attack -> REJECT immediately
            if pad_result.verdict == PADVerdict.PRESENTATION_ATTACK:
                self.audit_logger.log_event(
                    AuditEventType.PAD_ATTACK_DETECTED,
                    session_id=self.session_id,
                    workflow=self.workflow.value,
                    details={
                        "attack_type": pad_result.attack_type,
                        "liveness_score": pad_result.liveness_score,
                        "mode": pad_result.mode_used
                    }
                )

                # Only if explicitly configured via policy does a definite attack escalate to active challenges
                if getattr(self.policy, "escalate_attacks_to_active", False) and self.policy.active_liveness_enabled:
                    self.state = PipelineState.ACTIVE_CHALLENGE
                    challenge = self.challenge_manager.generate_next_challenge()
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                        status_text=f"Please {challenge.challenge_type.value.lower().replace('_', ' ')}",
                        detailed_guidance="Verification requires a quick interactive response.",
                        progress=0.3,
                        quality=quality,
                        pad_result=pad_result,
                        active_challenge=challenge,
                        can_retry=self.challenge_manager.can_retry(),
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )
                else:
                    self.state = PipelineState.ATTACK_REJECTED
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.ATTACK_DETECTED,
                        status_text="Verification Incomplete",
                        detailed_guidance=get_safe_user_message(BiometricErrorCode.PAD_ATTACK_DETECTED),
                        progress=0.0,
                        quality=quality,
                        pad_result=pad_result,
                        error_code=BiometricErrorCode.PAD_ATTACK_DETECTED,
                        can_retry=self.challenge_manager.can_retry(),
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )

            # 2. Processing Error -> Handle gracefully with retry guidance
            elif pad_result.verdict == PADVerdict.PROCESSING_ERROR:
                return PipelineStepResult(
                    state=self.state,
                    decision=LivenessDecision.ERROR,
                    status_text="Processing Frame",
                    detailed_guidance="Please adjust your position so your face is clearly visible.",
                    progress=0.05,
                    quality=quality,
                    pad_result=pad_result,
                    error_code=BiometricErrorCode.INVALID_FRAME,
                    can_retry=self.challenge_manager.can_retry(),
                    current_retry=self.challenge_manager.current_retry,
                    max_retries=self.policy.max_retries
                )

            self._passive_frames_analyzed += 1
            max_passive_window = 25  # ~0.8-1.0 second visible evaluation
            passive_progress = min(1.0, self._passive_frames_analyzed / float(max_passive_window))

            if self._passive_frames_analyzed >= max_passive_window:
                # Evaluate temporal rolling score rather than single frame
                rolling_score = temp_analysis.rolling_liveness_score

                if rolling_score >= self.policy.passive_threshold and temp_analysis.temporal_stability >= 0.60:
                    # High confidence passive liveness passed!
                    self.state = PipelineState.CAPTURE_SUCCESS
                    self._captured_biometric = bgr.copy()
                    
                    self.audit_logger.log_event(
                        AuditEventType.CAPTURE_SUCCESS,
                        session_id=self.session_id,
                        workflow=self.workflow.value,
                        details={"path": "PASSIVE_DIRECT", "score": rolling_score}
                    )
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.PASSED,
                        status_text="Face verified successfully!",
                        detailed_guidance="Passive liveness confirmed. Biometric capture complete.",
                        progress=1.0,
                        quality=quality,
                        pad_result=pad_result,
                        captured_face_image=self._captured_biometric,
                        can_retry=False,
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )
                else:
                    # Uncertain / borderline score -> escalate to active challenges
                    if self.policy.active_liveness_enabled:
                        self.state = PipelineState.ACTIVE_CHALLENGE
                        challenge = self.challenge_manager.generate_next_challenge()
                        self.audit_logger.log_event(
                            AuditEventType.ACTIVE_CHALLENGE_STARTED,
                            session_id=self.session_id,
                            workflow=self.workflow.value,
                            details={"reason": "PASSIVE_UNCERTAIN", "rolling_score": rolling_score}
                        )
                        return PipelineStepResult(
                            state=self.state,
                            decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                            status_text=f"Please {challenge.challenge_type.value.lower().replace('_', ' ')}",
                            detailed_guidance="Verification requires a quick interactive response.",
                            progress=0.4,
                            quality=quality,
                            pad_result=pad_result,
                            active_challenge=challenge,
                            can_retry=self.challenge_manager.can_retry(),
                            current_retry=self.challenge_manager.current_retry,
                            max_retries=self.policy.max_retries
                        )
                    else:
                        self.state = PipelineState.RETRY_PENDING
                        self._state_start_time = time.time()

            return PipelineStepResult(
                state=self.state,
                decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED if self.state == PipelineState.ACTIVE_CHALLENGE else LivenessDecision.IN_PROGRESS,
                status_text="Please complete the active challenge" if self.state == PipelineState.ACTIVE_CHALLENGE else "Checking face liveness...",
                detailed_guidance="Follow on-screen instructions" if self.state == PipelineState.ACTIVE_CHALLENGE else "Analyzing facial biometric characteristics (Passive Check)",
                progress=passive_progress * 0.5,
                quality=quality,
                pad_result=pad_result,
                active_challenge=self.challenge_manager.active_challenge_state,
                can_retry=self.challenge_manager.can_retry(),
                current_retry=self.challenge_manager.current_retry,
                max_retries=self.policy.max_retries
            )

        # 4. ACTIVE LIVENESS CHALLENGE EVALUATION
        if self.state == PipelineState.ACTIVE_CHALLENGE:
            challenge_state = self.challenge_manager.active_challenge_state
            if challenge_state is None:
                challenge_state = self.challenge_manager.generate_next_challenge()
            telemetry, updated_challenge = self.active_detector.process_frame(bgr, challenge_state)
            self.challenge_manager.active_challenge_state = updated_challenge

            # Check challenge timeout or failure
            if updated_challenge and not updated_challenge.is_active and not updated_challenge.is_completed:
                self.challenge_manager.increment_retry()
                self.audit_logger.log_event(
                    AuditEventType.ACTIVE_CHALLENGE_FAILED,
                    session_id=self.session_id,
                    workflow=self.workflow.value,
                    details={"retry": self.challenge_manager.current_retry, "max": self.policy.max_retries}
                )

                if self.challenge_manager.can_retry():
                    self.state = PipelineState.RETRY_PENDING
                    self._state_start_time = time.time()
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.FAILED,
                        status_text="Challenge not completed",
                        detailed_guidance=f"Verification attempt failed. Retry {self.challenge_manager.current_retry}/{self.policy.max_retries}.",
                        progress=0.0,
                        quality=quality,
                        active_challenge=updated_challenge,
                        telemetry=telemetry,
                        error_code=BiometricErrorCode.ACTIVE_CHALLENGE_TIMEOUT,
                        can_retry=True,
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )
                else:
                    self.state = PipelineState.MAX_RETRIES_EXCEEDED
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.FAILED,
                        status_text="Verification Limit Reached",
                        detailed_guidance=get_safe_user_message(BiometricErrorCode.MAX_RETRIES_EXCEEDED),
                        progress=0.0,
                        quality=quality,
                        active_challenge=updated_challenge,
                        telemetry=telemetry,
                        error_code=BiometricErrorCode.MAX_RETRIES_EXCEEDED,
                        can_retry=False,
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )

            # Check if active challenge succeeded
            if updated_challenge and updated_challenge.is_completed:
                self.challenge_manager.record_challenge_success()
                self.audit_logger.log_event(
                    AuditEventType.ACTIVE_CHALLENGE_PASSED,
                    session_id=self.session_id,
                    workflow=self.workflow.value,
                    details={"challenge": updated_challenge.challenge.value}
                )

                if self.challenge_manager.is_all_challenges_satisfied():
                    self.state = PipelineState.CAPTURE_SUCCESS
                    self._captured_biometric = bgr.copy()
                    
                    self.audit_logger.log_event(
                        AuditEventType.CAPTURE_SUCCESS,
                        session_id=self.session_id,
                        workflow=self.workflow.value,
                        details={"path": "ACTIVE_CHALLENGES_VERIFIED"}
                    )

                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.PASSED,
                        status_text="Good, face captured successfully!",
                        detailed_guidance="All active challenges verified. Registration complete.",
                        progress=1.0,
                        quality=quality,
                        active_challenge=updated_challenge,
                        captured_face_image=self._captured_biometric,
                        telemetry=telemetry,
                        can_retry=False,
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )
                else:
                    # Proceed to next challenge
                    self.challenge_manager.generate_next_challenge()

            return PipelineStepResult(
                state=self.state,
                decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                status_text=updated_challenge.feedback_message if updated_challenge else "Follow instruction",
                detailed_guidance=f"Challenge {len(self.challenge_manager.completed_challenges) + 1} of {self.policy.min_challenges}",
                progress=0.5 + (updated_challenge.progress * 0.5) if updated_challenge else 0.5,
                quality=quality,
                active_challenge=updated_challenge,
                telemetry=telemetry,
                can_retry=self.challenge_manager.can_retry(),
                current_retry=self.challenge_manager.current_retry,
                max_retries=self.policy.max_retries
            )

        # 5. TERMINAL & RETRY STATES
        if self.state == PipelineState.CAPTURE_SUCCESS:
            return PipelineStepResult(
                state=self.state,
                decision=LivenessDecision.PASSED,
                status_text="Biometric Accepted - Capture Complete!",
                detailed_guidance="Face liveness verified. Press [R] to test a new session or [Q] to quit.",
                progress=1.0,
                captured_face_image=self._captured_biometric,
                can_retry=False,
                current_retry=self.challenge_manager.current_retry,
                max_retries=self.policy.max_retries
            )

        if self.state == PipelineState.RETRY_PENDING:
            if time.time() - self._state_start_time > 2.0:
                self.state = PipelineState.FACE_DETECTION
                self._passive_frames_analyzed = 0
                self.temporal_buffer.clear()

        is_max = (self.state == PipelineState.MAX_RETRIES_EXCEEDED)
        return PipelineStepResult(
            state=self.state,
            decision=LivenessDecision.FAILED,
            status_text="Verification Limit Reached" if is_max else "Retrying in 2 seconds...",
            detailed_guidance=get_safe_user_message(BiometricErrorCode.MAX_RETRIES_EXCEEDED) if is_max else f"Attempt {self.challenge_manager.current_retry + 1} of {self.policy.max_retries}. Stay centered.",
            progress=0.0,
            can_retry=self.challenge_manager.can_retry(),
            current_retry=self.challenge_manager.current_retry,
            max_retries=self.policy.max_retries
        )
