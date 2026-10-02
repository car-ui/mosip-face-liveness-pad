"""
MOSIP Face Liveness & Presentation Attack Detection Configuration
Supports configurable thresholds, policies, timeouts, and workflows (Resident, Operator, Supervisor).
Online and offline operation support.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


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
    PASSED = "PASSED"
    FAILED = "FAILED"
    ACTIVE_CHALLENGE_REQUIRED = "ACTIVE_CHALLENGE_REQUIRED"
    ATTACK_DETECTED = "ATTACK_DETECTED"
    ERROR = "ERROR"


@dataclass
class WorkflowPolicy:
    workflow_type: WorkflowType
    passive_threshold: float = 0.85
    active_liveness_enabled: bool = True
    min_challenges: int = 1
    max_challenges: int = 2
    challenge_timeout_seconds: float = 6.0
    max_retries: int = 3
    enforce_face_centering: bool = True
    enforce_single_face: bool = True
    min_face_size_ratio: float = 0.20
    max_face_size_ratio: float = 0.80


@dataclass
class LivenessConfig:
    # General Settings
    liveness_enabled: bool = True
    offline_mode: bool = True
    
    # Supported Challenge Pool
    supported_challenges: List[ChallengeType] = field(default_factory=lambda: [
        ChallengeType.BLINK,
        ChallengeType.SMILE,
        ChallengeType.TURN_LEFT,
        ChallengeType.TURN_RIGHT
    ])
    
    # Workflow Policies
    resident_policy: WorkflowPolicy = field(default_factory=lambda: WorkflowPolicy(
        workflow_type=WorkflowType.RESIDENT_REGISTRATION,
        passive_threshold=0.80,
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
        min_challenges=1,
        max_challenges=2,
        challenge_timeout_seconds=5.0,
        max_retries=2
    ))
    
    supervisor_policy: WorkflowPolicy = field(default_factory=lambda: WorkflowPolicy(
        workflow_type=WorkflowType.SUPERVISOR_AUTHENTICATION,
        passive_threshold=0.90,
        active_liveness_enabled=True,
        min_challenges=2,
        max_challenges=3,
        challenge_timeout_seconds=5.0,
        max_retries=2
    ))
    
    # Biometric Image Standards
    iso_target_width: int = 640
    iso_target_height: int = 480
    min_lighting_score: float = 40.0
    max_lighting_score: float = 230.0
    
    def get_policy(self, workflow: WorkflowType) -> WorkflowPolicy:
        if workflow == WorkflowType.RESIDENT_REGISTRATION:
            return self.resident_policy
        elif workflow == WorkflowType.OPERATOR_AUTHENTICATION:
            return self.operator_policy
        elif workflow == WorkflowType.SUPERVISOR_AUTHENTICATION:
            return self.supervisor_policy
        return self.resident_policy
