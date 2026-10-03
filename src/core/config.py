"""
MOSIP Face Liveness & Presentation Attack Detection Configuration
Supports configurable thresholds, policies, timeouts, and workflows (Resident, Operator, Supervisor).
Strictly offline-first with zero external network dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class WorkflowType(str, Enum):
    RESIDENT_REGISTRATION = "RESIDENT_REGISTRATION"
    OPERATOR_AUTHENTICATION = "OPERATOR_AUTHENTICATION"
    SUPERVISOR_AUTHENTICATION = "SUPERVISOR_AUTHENTICATION"


class ChallengeType(str, Enum):
    BLINK = "BLINK"
    SMILE = "SMILE"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    LOOK_UP = "LOOK_UP"
    LOOK_DOWN = "LOOK_DOWN"


class LivenessDecision(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ACTIVE_CHALLENGE_REQUIRED = "ACTIVE_CHALLENGE_REQUIRED"
    ATTACK_DETECTED = "ATTACK_DETECTED"
    ERROR = "ERROR"


class PADMode(str, Enum):
    AUTO = "AUTO"                # Uses ONNX model if present & valid; falls back to heuristic engine
    HEURISTIC_ONLY = "HEURISTIC" # Pure deterministic multi-cue physical heuristics
    ONNX_ONLY = "ONNX"           # Strict Deep Learning model inference only


class PADVerdict(str, Enum):
    BONA_FIDE_LIVE = "BONA_FIDE_LIVE"
    UNCERTAIN = "UNCERTAIN"
    PRESENTATION_ATTACK = "PRESENTATION_ATTACK"
    PROCESSING_ERROR = "PROCESSING_ERROR"


@dataclass
class WorkflowPolicy:
    workflow_type: WorkflowType
    passive_threshold: float = 0.82
    active_liveness_enabled: bool = True
    min_challenges: int = 1
    max_challenges: int = 2
    challenge_timeout_seconds: float = 6.0
    max_retries: int = 3
    enforce_face_centering: bool = True
    enforce_single_face: bool = True
    min_face_size_ratio: float = 0.04
    max_face_size_ratio: float = 0.85
    escalate_attacks_to_active: bool = False


@dataclass
class LivenessConfig:
    # General Settings
    liveness_enabled: bool = True
    offline_mode: bool = True
    
    # PAD Engine Settings
    pad_mode: PADMode = PADMode.AUTO
    onnx_model_path: Optional[str] = None
    pad_high_confidence_threshold: float = 0.85
    pad_attack_rejection_threshold: float = 0.45
    
    # Temporal Analysis Settings
    temporal_window_size: int = 15
    consecutive_frames_required: int = 3
    min_motion_threshold: float = 0.35
    
    # Active Challenge Detection Parameters
    blink_ear_closed: float = 0.22
    blink_ear_open: float = 0.28
    smile_delta_min: float = 0.15
    smile_score_min: float = 0.35
    yaw_turn_threshold: float = 14.0
    yaw_return_threshold: float = 7.0
    
    # Supported Challenge Pool
    supported_challenges: List[ChallengeType] = field(default_factory=lambda: [
        ChallengeType.BLINK,
        ChallengeType.SMILE,
        ChallengeType.TURN_LEFT,
        ChallengeType.TURN_RIGHT
    ])
    
    # Quality & Image Standards (ISO/IEC 19794-5)
    iso_target_width: int = 640
    iso_target_height: int = 480
    min_sharpness: float = 30.0
    min_lighting_score: float = 48.0
    max_lighting_score: float = 215.0
    max_shadow_delta: float = 40.0
    
    # Workflow Policies
    resident_policy: WorkflowPolicy = field(default_factory=lambda: WorkflowPolicy(
        workflow_type=WorkflowType.RESIDENT_REGISTRATION,
        passive_threshold=0.82,
        active_liveness_enabled=True,
        min_challenges=1,
        max_challenges=2,
        challenge_timeout_seconds=7.0,
        max_retries=3
    ))
    
    operator_policy: WorkflowPolicy = field(default_factory=lambda: WorkflowPolicy(
        workflow_type=WorkflowType.OPERATOR_AUTHENTICATION,
        passive_threshold=0.88,
        active_liveness_enabled=True,
        min_challenges=2,
        max_challenges=2,
        challenge_timeout_seconds=5.0,
        max_retries=2
    ))
    
    supervisor_policy: WorkflowPolicy = field(default_factory=lambda: WorkflowPolicy(
        workflow_type=WorkflowType.SUPERVISOR_AUTHENTICATION,
        passive_threshold=0.92,
        active_liveness_enabled=True,
        min_challenges=2,
        max_challenges=3,
        challenge_timeout_seconds=5.0,
        max_retries=2
    ))
    
    def get_policy(self, workflow: WorkflowType) -> WorkflowPolicy:
        if workflow == WorkflowType.RESIDENT_REGISTRATION:
            return self.resident_policy
        elif workflow == WorkflowType.OPERATOR_AUTHENTICATION:
            return self.operator_policy
        elif workflow == WorkflowType.SUPERVISOR_AUTHENTICATION:
            return self.supervisor_policy
        return self.resident_policy
