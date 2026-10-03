"""
Centralized Error Taxonomy and Safe Feedback Mapping
Conforms to biometric privacy and security guidelines:
- Internal diagnostic error codes for system telemetry and audit logs
- User-safe feedback messages that prevent information leakage to potential attackers
"""

from enum import Enum
from typing import Dict


class BiometricErrorCode(str, Enum):
    # Device errors
    DEVICE_UNAVAILABLE = "DEVICE_UNAVAILABLE"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    CAMERA_UNAVAILABLE = "CAMERA_UNAVAILABLE"
    INVALID_FRAME = "INVALID_FRAME"
    
    # Biometric quality errors (ISO/IEC 19794-5)
    NO_FACE = "NO_FACE"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    POOR_LIGHTING_DARK = "POOR_LIGHTING_DARK"
    POOR_LIGHTING_BRIGHT = "POOR_LIGHTING_BRIGHT"
    POOR_LIGHTING_UNEVEN = "POOR_LIGHTING_UNEVEN"
    BLURRY_FACE = "BLURRY_FACE"
    FACE_TOO_SMALL = "FACE_TOO_SMALL"
    FACE_TOO_LARGE = "FACE_TOO_LARGE"
    FACE_NOT_CENTERED = "FACE_NOT_CENTERED"
    
    # Liveness & PAD errors (ISO/IEC 30107)
    PASSIVE_LIVENESS_FAILED = "PASSIVE_LIVENESS_FAILED"
    PAD_ATTACK_DETECTED = "PAD_ATTACK_DETECTED"
    SCREEN_REPLAY_DETECTED = "SCREEN_REPLAY_DETECTED"
    PRINT_PHOTO_DETECTED = "PRINT_PHOTO_DETECTED"
    
    # Active challenge errors
    ACTIVE_CHALLENGE_TIMEOUT = "ACTIVE_CHALLENGE_TIMEOUT"
    ACTIVE_CHALLENGE_FAILED = "ACTIVE_CHALLENGE_FAILED"
    WRONG_DIRECTION = "WRONG_DIRECTION"
    STATIC_FACE_DETECTED = "STATIC_FACE_DETECTED"
    
    # Workflow / Session errors
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    ENGINE_ERROR = "ENGINE_ERROR"


# Map internal technical errors to user-safe feedback messages
# SECURITY NOTICE: Never reveal internal PAD heuristic thresholds or specific spoof vectors to end users.
SAFE_USER_MESSAGES: Dict[BiometricErrorCode, str] = {
    BiometricErrorCode.DEVICE_UNAVAILABLE: "Capture device unavailable. Please check device connection.",
    BiometricErrorCode.DEVICE_DISCONNECTED: "Device was disconnected during capture. Please reconnect.",
    BiometricErrorCode.CAMERA_UNAVAILABLE: "Camera feed interrupted. Please check hardware.",
    BiometricErrorCode.INVALID_FRAME: "Video frame reception error. Please try again.",
    
    BiometricErrorCode.NO_FACE: "Face not detected. Please look directly into the camera.",
    BiometricErrorCode.MULTIPLE_FACES: "Multiple faces detected. Only one person should be in frame.",
    BiometricErrorCode.POOR_LIGHTING_DARK: "Environment too dark. Please face a light source or turn on a light.",
    BiometricErrorCode.POOR_LIGHTING_BRIGHT: "Lighting too harsh or glare on face. Avoid strong direct light.",
    BiometricErrorCode.POOR_LIGHTING_UNEVEN: "Uneven lighting / shadows on face. Please face the light directly.",
    BiometricErrorCode.BLURRY_FACE: "Image is blurry. Please hold still during verification.",
    BiometricErrorCode.FACE_TOO_SMALL: "Face is too far. Please move closer to the camera.",
    BiometricErrorCode.FACE_TOO_LARGE: "Face is too close. Please step back slightly.",
    BiometricErrorCode.FACE_NOT_CENTERED: "Please position your face inside the central guide oval.",
    
    # Security-safe liveness failure message
    BiometricErrorCode.PASSIVE_LIVENESS_FAILED: "Liveness verification could not be completed. Please try again.",
    BiometricErrorCode.PAD_ATTACK_DETECTED: "Face verification could not be completed. Please present a live face.",
    BiometricErrorCode.SCREEN_REPLAY_DETECTED: "Face verification could not be completed. Please try again.",
    BiometricErrorCode.PRINT_PHOTO_DETECTED: "Face verification could not be completed. Please try again.",
    
    BiometricErrorCode.ACTIVE_CHALLENGE_TIMEOUT: "Challenge response timed out. Please try again.",
    BiometricErrorCode.ACTIVE_CHALLENGE_FAILED: "Action was not recognized. Please follow the on-screen prompt.",
    BiometricErrorCode.WRONG_DIRECTION: "Wrong direction. Please follow the indicated arrow.",
    BiometricErrorCode.STATIC_FACE_DETECTED: "Please perform the requested action naturally.",
    
    BiometricErrorCode.MAX_RETRIES_EXCEEDED: "Maximum verification attempts exceeded. Please contact the registration supervisor.",
    BiometricErrorCode.SESSION_TIMEOUT: "Session timed out. Please restart biometric verification.",
    BiometricErrorCode.ENGINE_ERROR: "An unexpected error occurred during biometric processing."
}


def get_safe_user_message(code: BiometricErrorCode) -> str:
    """Returns safe user-facing instruction without leaking technical PAD internals."""
    return SAFE_USER_MESSAGES.get(code, "Face verification could not be completed. Please try again.")
