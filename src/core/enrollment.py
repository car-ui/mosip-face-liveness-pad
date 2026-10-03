"""
MOSIP Lightweight Resident Biometric Enrollment Subsystem
Handles resident registration sessions, Resident ID generation/assignment,
biometric verification progression, token hash generation, and privacy-preserving record storage.

Privacy Guarantee:
No raw facial images are stored in enrollment records or audit logs.
Biometric frames exist transiently in volatile memory only during the active verification cycle
and are immediately discarded upon feature extraction.
"""

import time
import secrets
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .config import WorkflowType, LivenessDecision
from .pipeline import PipelineState, PipelineStepResult
from ..devices.base import DeviceCapabilities


class EnrollmentStage(str, Enum):
    READY = "READY"                      # Awaiting resident check-in / start
    POSITIONING = "POSITIONING"          # Face alignment and quality check
    LIVENESS_CHECK = "LIVENESS_CHECK"    # Passive PAD and active challenge
    ENROLLED = "ENROLLED"                # Biometric enrollment completed successfully
    REJECTED = "REJECTED"                # Biometric enrollment rejected (Attack detected)
    FAILED = "FAILED"                    # Biometric enrollment failed (Max retries / timeout)


@dataclass
class ResidentEnrollmentRecord:
    """
    Lightweight, privacy-preserving enrollment record.
    Never stores raw biometric facial images or pixel arrays.
    """
    resident_id: str
    session_id: str
    timestamp: float
    iso_timestamp: str
    stage: EnrollmentStage
    liveness_verified: bool
    liveness_path: Optional[str] = None          # "PASSIVE_DIRECT" or "ACTIVE_CHALLENGES_VERIFIED"
    status_message: str = "In Progress"
    rejection_reason: Optional[str] = None
    device_id: str = "UNKNOWN"
    device_security_level: str = "L0_BASIC"      # "L0_BASIC", "L0_SIMULATED", "L1_SIMULATED", or "L1_SECURE_HARDWARE"
    model_backend: str = "heuristic_multi_cue"
    model_version: str = "v1.2.0-heuristic"
    model_hash: str = "N/A"
    biometric_token_hash: Optional[str] = None   # SHA-256 hash of captured biometric template
    telemetry: Dict[str, Any] = field(default_factory=dict)


class ResidentEnrollmentManager:
    """
    Orchestrates the lightweight resident enrollment experience:
    START -> Check-in -> Face Positioning -> Quality -> Passive PAD -> Active Challenge -> Complete.
    """

    def __init__(self, default_resident_id: Optional[str] = None):
        self._rng = secrets.SystemRandom()
        self.resident_id: str = default_resident_id or self.generate_resident_id()
        self.stage: EnrollmentStage = EnrollmentStage.READY
        self.session_id: str = f"ENROLL-{secrets.token_hex(6).upper()}"
        self.current_record: Optional[ResidentEnrollmentRecord] = None
        self.face_positioned: bool = False
        self.quality_passed: bool = False
        self.passive_completed: bool = False
        self.active_completed: bool = False

    def generate_resident_id(self) -> str:
        """Generates a cryptographically random, realistic MOSIP Resident ID (RES-XXXXX)."""
        num = self._rng.randint(10000, 99999)
        return f"RES-{num}"

    def set_resident_id(self, resident_id: str) -> None:
        """Sets a specific Resident ID entered by the operator/resident."""
        clean_id = resident_id.strip().upper()
        if not clean_id.startswith("RES-"):
            clean_id = f"RES-{clean_id}"
        self.resident_id = clean_id

    def start_enrollment(self, resident_id: Optional[str] = None) -> None:
        """Transitions from READY to active biometric positioning and verification."""
        if resident_id:
            self.set_resident_id(resident_id)
        self.stage = EnrollmentStage.POSITIONING
        self.session_id = f"ENROLL-{secrets.token_hex(6).upper()}"
        self.face_positioned = False
        self.quality_passed = False
        self.passive_completed = False
        self.active_completed = False
        self.current_record = None

    def update_from_pipeline(self,
                             step_result: PipelineStepResult,
                             device_capabilities: Optional[DeviceCapabilities] = None) -> EnrollmentStage:
        """
        Updates enrollment progression based on the pipeline's frame analysis.
        """
        # Quality & positioning tracking
        if step_result.quality:
            self.face_positioned = (step_result.quality.face_count == 1 and step_result.quality.is_centered)
            self.quality_passed = step_result.quality.is_acceptable

        # State mapping
        if step_result.state in (PipelineState.PASSIVE_LIVENESS,):
            self.stage = EnrollmentStage.LIVENESS_CHECK
            if step_result.progress >= 0.4:
                self.passive_completed = True

        elif step_result.state in (PipelineState.ACTIVE_CHALLENGE, PipelineState.CHALLENGE_VALIDATION):
            self.stage = EnrollmentStage.LIVENESS_CHECK
            self.passive_completed = True

        elif step_result.state == PipelineState.CAPTURE_SUCCESS:
            self.stage = EnrollmentStage.ENROLLED
            self.passive_completed = True
            self.active_completed = True
            
            # Generate cryptographic token hash of the biometric image (Zero raw storage!)
            token_hash = None
            if step_result.captured_face_image is not None:
                token_hash = hashlib.sha256(step_result.captured_face_image.tobytes()).hexdigest()

            meta = step_result.pad_result.model_metadata if step_result.pad_result else None
            dev_id = device_capabilities.device_id if device_capabilities else "DEV-L0-DEFAULT"
            sec_lvl = device_capabilities.security_level if device_capabilities else "L0_BASIC"

            self.current_record = ResidentEnrollmentRecord(
                resident_id=self.resident_id,
                session_id=self.session_id,
                timestamp=time.time(),
                iso_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                stage=EnrollmentStage.ENROLLED,
                liveness_verified=True,
                liveness_path="ACTIVE_CHALLENGES_VERIFIED" if step_result.active_challenge else "PASSIVE_DIRECT",
                status_message="Biometric Enrollment Complete",
                device_id=dev_id,
                device_security_level=sec_lvl,
                model_backend=meta.backend_name if meta else "heuristic_multi_cue",
                model_version=meta.version if meta else "v1.2.0-heuristic",
                model_hash=meta.model_hash if meta else "N/A",
                biometric_token_hash=token_hash,
                telemetry={
                    "current_retry": step_result.current_retry,
                    "max_retries": step_result.max_retries
                }
            )

        elif step_result.state == PipelineState.ATTACK_REJECTED:
            self.stage = EnrollmentStage.REJECTED
            meta = step_result.pad_result.model_metadata if step_result.pad_result else None
            dev_id = device_capabilities.device_id if device_capabilities else "DEV-L0-DEFAULT"
            sec_lvl = device_capabilities.security_level if device_capabilities else "L0_BASIC"

            self.current_record = ResidentEnrollmentRecord(
                resident_id=self.resident_id,
                session_id=self.session_id,
                timestamp=time.time(),
                iso_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                stage=EnrollmentStage.REJECTED,
                liveness_verified=False,
                rejection_reason="Presentation Attack Detected",
                status_message="Enrollment Rejected - Biometric Spoof Detected",
                device_id=dev_id,
                device_security_level=sec_lvl,
                model_backend=meta.backend_name if meta else "heuristic_multi_cue",
                model_version=meta.version if meta else "v1.2.0-heuristic",
                model_hash=meta.model_hash if meta else "N/A",
                biometric_token_hash=None
            )

        elif step_result.state == PipelineState.MAX_RETRIES_EXCEEDED:
            self.stage = EnrollmentStage.FAILED
            self.current_record = ResidentEnrollmentRecord(
                resident_id=self.resident_id,
                session_id=self.session_id,
                timestamp=time.time(),
                iso_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                stage=EnrollmentStage.FAILED,
                liveness_verified=False,
                rejection_reason="Maximum Verification Retries Exceeded",
                status_message="Enrollment Failed - Please seek Operator Assistance"
            )

        return self.stage

    def reset(self, new_resident: bool = True) -> None:
        """Resets the enrollment state for a new resident or a retry."""
        if new_resident:
            self.resident_id = self.generate_resident_id()
        self.stage = EnrollmentStage.READY
        self.session_id = f"ENROLL-{secrets.token_hex(6).upper()}"
        self.face_positioned = False
        self.quality_passed = False
        self.passive_completed = False
        self.active_completed = False
        self.current_record = None
