"""
Master Face Liveness & PAD Orchestration Pipeline
Implements the hybrid passive-active workflow defined in MOSIP Decode Problem 04:
1. Receive incoming frame stream from L0/L1 device
2. Assess face positioning & biometric quality (ISO/IEC 19794-5)
3. Perform passive liveness and PAD assessment (ISO/IEC 30107)
4. Evaluate quality/confidence vs configured policy threshold
5. If passed, complete capture successfully
6. If below threshold, automatically initiate dynamic active challenge
7. Validate action response within timeout
8. Return biometric artifact or handle retry/failure gracefully
"""

import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import cv2
import numpy as np

from .config import LivenessConfig, WorkflowType, WorkflowPolicy, LivenessDecision
from .face_detector import FaceQualityAssessor, DetectedFace, QualityMetrics
from .passive_pad import PassivePADDetector, PADResult
from .active_liveness import ActiveLivenessDetector, ChallengeState
from .challenge_manager import ChallengeManager
from ..devices.base import VideoFrame


class PipelineState(str, Enum):
    IDLE = "IDLE"
    DETECTING_FACE = "DETECTING_FACE"
    EVALUATING_PASSIVE = "EVALUATING_PASSIVE"
    ACTIVE_CHALLENGE = "ACTIVE_CHALLENGE"
    ATTACK_REJECTED = "ATTACK_REJECTED"
    CAPTURE_SUCCESS = "CAPTURE_SUCCESS"
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
    can_retry: bool = True
    current_retry: int = 0
    max_retries: int = 3


class LivenessPipeline:
    def __init__(self, config: Optional[LivenessConfig] = None, workflow: WorkflowType = WorkflowType.RESIDENT_REGISTRATION):
        self.config = config or LivenessConfig()
        self.workflow = workflow
        self.policy: WorkflowPolicy = self.config.get_policy(workflow)

        self.quality_assessor = FaceQualityAssessor(
            min_brightness=self.config.min_lighting_score,
            max_brightness=self.config.max_lighting_score
        )
        self.pad_detector = PassivePADDetector()
        self.active_detector = ActiveLivenessDetector()
        self.challenge_manager = ChallengeManager(self.policy, self.config.supported_challenges)

        self.state: PipelineState = PipelineState.IDLE
        self._captured_biometric: Optional[np.ndarray] = None
        self._passive_frames_analyzed = 0
        self._passive_score_accum: float = 0.0
        self._state_start_time = time.time()
        self._last_face_box: Optional[Tuple[int, int, int, int]] = None

    def set_workflow(self, workflow: WorkflowType):
        self.workflow = workflow
        self.policy = self.config.get_policy(workflow)
        self.challenge_manager = ChallengeManager(self.policy, self.config.supported_challenges)
        self.reset()

    def reset(self):
        """Resets the pipeline for a new biometric capture session."""
        self.state = PipelineState.DETECTING_FACE
        self._captured_biometric = None
        self._passive_frames_analyzed = 0
        self._passive_score_accum = 0.0
        self._state_start_time = time.time()
        self.challenge_manager.reset()

    def process_frame(self, frame: VideoFrame) -> PipelineStepResult:
        bgr = frame.image
        h, w = bgr.shape[:2]

        # Extract landmarks and telemetry (MediaPipe 30 FPS)
        challenge_state = self.challenge_manager.active_challenge_state
        telemetry, updated_challenge = self.active_detector.process_frame(bgr, challenge_state)
        if challenge_state:
            self.challenge_manager.active_challenge_state = updated_challenge

        # 1. Face Detection & Quality Assessment (using fast known_box if available)
        known_box = telemetry.get("face_box")
        faces = self.quality_assessor.detect_faces(bgr, known_box=known_box)
        quality = self.quality_assessor.assess_quality(bgr, faces)

        # Handle face detection / quality errors
        if not quality.is_acceptable:
            if quality.face_count > 1:
                status_text = "Multiple Faces Detected"
            elif quality.is_poorly_lit:
                status_text = "Adjust Lighting"
            elif quality.is_blurry:
                status_text = "Hold Still"
            elif not quality.is_centered:
                status_text = "Center Your Face"
            else:
                status_text = "Positioning face..."

            # If during active challenge, keep active state but warn user
            if self.state == PipelineState.ACTIVE_CHALLENGE and self.challenge_manager.active_challenge_state:
                return PipelineStepResult(
                    state=self.state,
                    decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                    status_text=status_text,
                    detailed_guidance=quality.error_message or "Keep face centered in frame",
                    progress=self.challenge_manager.active_challenge_state.progress,
                    quality=quality,
                    active_challenge=self.challenge_manager.active_challenge_state,
                    can_retry=self.challenge_manager.can_retry(),
                    current_retry=self.challenge_manager.current_retry,
                    max_retries=self.policy.max_retries
                )
            
            return PipelineStepResult(
                state=PipelineState.DETECTING_FACE,
                decision=LivenessDecision.ERROR,
                status_text=status_text,
                detailed_guidance=quality.error_message or "Look directly at camera",
                progress=0.1,
                quality=quality,
                can_retry=self.challenge_manager.can_retry(),
                current_retry=self.challenge_manager.current_retry,
                max_retries=self.policy.max_retries
            )

        face = faces[0]
        face_box = (face.x, face.y, face.w, face.h)
        self._last_face_box = face_box

        # 2. State Machine Handling
        # If in DETECTING_FACE and face is well positioned, proceed to PASSIVE check
        if self.state in (PipelineState.IDLE, PipelineState.DETECTING_FACE):
            self.state = PipelineState.EVALUATING_PASSIVE
            self._passive_frames_analyzed = 0
            self._passive_score_accum = 0.0
            self._state_start_time = time.time()

        # 3. PASSIVE LIVENESS & PAD EVALUATION
        if self.state == PipelineState.EVALUATING_PASSIVE:
            pad_result = self.pad_detector.evaluate_passive_liveness(bgr, face_box)
            
            # Check for presentation attack: if active liveness is enabled, challenge the user to prove liveness
            if pad_result.attack_detected:
                if self.policy.active_liveness_enabled:
                    self.state = PipelineState.ACTIVE_CHALLENGE
                    self.challenge_manager.generate_next_challenge()
                else:
                    self.state = PipelineState.ATTACK_REJECTED
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.ATTACK_DETECTED,
                        status_text="Verification could not be completed",
                        detailed_guidance="Potential presentation attack detected. Please present a live face.",
                        progress=0.0,
                        quality=quality,
                        pad_result=pad_result,
                        can_retry=self.challenge_manager.can_retry(),
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )

            self._passive_frames_analyzed += 1
            self._passive_score_accum += pad_result.liveness_score
            avg_score = self._passive_score_accum / self._passive_frames_analyzed

            # Evaluate over a visible 1.5 second window (30 frames) per MOSIP Section 10.2
            max_passive_window = 30
            passive_progress = min(1.0, self._passive_frames_analyzed / float(max_passive_window))

            if self._passive_frames_analyzed >= max_passive_window:
                if avg_score >= self.policy.passive_threshold:
                    # High confidence passive liveness passed without requiring active action!
                    self.state = PipelineState.CAPTURE_SUCCESS
                    self._captured_biometric = bgr.copy()
                    self._state_start_time = time.time()
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
                    # Passive score insufficient -> Transition dynamically to Active Challenge per MOSIP Spec
                    if self.policy.active_liveness_enabled:
                        self.state = PipelineState.ACTIVE_CHALLENGE
                        self.challenge_manager.generate_next_challenge()
                    else:
                        self.state = PipelineState.RETRY_PENDING
                        self._state_start_time = time.time()

            return PipelineStepResult(
                state=self.state,
                decision=LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                status_text="Checking face liveness...",
                detailed_guidance="Hold still while analyzing facial characteristics (Passive Check)",
                progress=passive_progress * 0.5,
                quality=quality,
                pad_result=pad_result,
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

            # Check if active challenge timed out or failed
            if updated_challenge and not updated_challenge.is_active and not updated_challenge.is_completed:
                # Challenge failed
                self.challenge_manager.increment_retry()
                if self.challenge_manager.can_retry():
                    self.state = PipelineState.RETRY_PENDING
                    self._state_start_time = time.time()
                    return PipelineStepResult(
                        state=self.state,
                        decision=LivenessDecision.FAILED,
                        status_text="Challenge not completed",
                        detailed_guidance=f"Verification failed. Retry {self.challenge_manager.current_retry}/{self.policy.max_retries}.",
                        progress=0.0,
                        quality=quality,
                        active_challenge=updated_challenge,
                        telemetry=telemetry,
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
                        detailed_guidance="Maximum verification attempts exceeded. Please contact the registration supervisor.",
                        progress=0.0,
                        quality=quality,
                        active_challenge=updated_challenge,
                        telemetry=telemetry,
                        can_retry=False,
                        current_retry=self.challenge_manager.current_retry,
                        max_retries=self.policy.max_retries
                    )

            # Check if current challenge succeeded
            if updated_challenge and updated_challenge.is_completed:
                self.challenge_manager.record_challenge_success()
                
                # Check if all required challenges are met
                if self.challenge_manager.is_all_challenges_satisfied():
                    self.state = PipelineState.CAPTURE_SUCCESS
                    self._captured_biometric = bgr.copy()
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
                    # Generate next challenge in the dynamic sequence
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

        # 5. RETRY / TERMINAL STATES
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
                # Automatically resume capture for next retry attempt
                self.state = PipelineState.DETECTING_FACE
                self._passive_frames_analyzed = 0
                self._passive_score_accum = 0.0

        is_max = (self.state == PipelineState.MAX_RETRIES_EXCEEDED)
        return PipelineStepResult(
            state=self.state,
            decision=LivenessDecision.FAILED,
            status_text="Verification Limit Reached" if is_max else "Retrying in 2 seconds...",
            detailed_guidance="Please try again or seek supervisor assistance." if is_max else f"Attempt {self.challenge_manager.current_retry + 1} of {self.policy.max_retries}. Stay centered.",
            progress=0.0,
            can_retry=self.challenge_manager.can_retry(),
            current_retry=self.challenge_manager.current_retry,
            max_retries=self.policy.max_retries
        )
