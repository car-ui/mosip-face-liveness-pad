"""
Common Face Capture Device Interface and Device Adapter Pattern
Conforms to MOSIP Device Service (MDS) hardware abstraction requirements:
- Complete vendor neutrality
- Decouples biometric processing from physical capture hardware
- Supports Physical L0 Webcams, L1 Secure Hardware Sensors, and Mock Simulators
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Generator, Tuple, Dict, Any
import numpy as np


class DeviceType(str, Enum):
    PHYSICAL_L0_WEBCAM = "PHYSICAL_L0_WEBCAM"
    HARDWARE_L1_BIOMETRIC = "HARDWARE_L1_BIOMETRIC"
    MOCK_L0_SIMULATOR = "MOCK_L0_SIMULATOR"


class DeviceStatus(str, Enum):
    CONNECTED = "CONNECTED"
    STREAMING = "STREAMING"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class MockScenario(str, Enum):
    BONA_FIDE_LIVE = "BONA_FIDE_LIVE"
    STATIC_PHOTO_ATTACK = "STATIC_PHOTO_ATTACK"
    SCREEN_REPLAY_ATTACK = "SCREEN_REPLAY_ATTACK"
    NO_FACE = "NO_FACE"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    POOR_LIGHTING_DARK = "POOR_LIGHTING_DARK"
    POOR_LIGHTING_BRIGHT = "POOR_LIGHTING_BRIGHT"
    POOR_LIGHTING_UNEVEN = "POOR_LIGHTING_UNEVEN"
    BLURRY_FRAME = "BLURRY_FRAME"
    DEVICE_DISCONNECT = "DEVICE_DISCONNECT"
    INVALID_FRAME = "INVALID_FRAME"


@dataclass
class DeviceInfo:
    device_id: str
    device_name: str
    device_type: DeviceType
    serial_number: str
    firmware_version: str
    is_l1_secure: bool
    status: DeviceStatus


@dataclass
class VideoFrame:
    frame_id: int
    timestamp_ms: float
    image: np.ndarray  # BGR format numpy array
    width: int
    height: int
    is_key_frame: bool = False
    metadata: Optional[Dict[str, Any]] = None


class FaceCaptureDevice(ABC):
    """
    Abstract Base Interface for all Face Capture Devices conforming to MOSIP Device Service (MDS).
    """

    @abstractmethod
    def connect(self) -> bool:
        """Initialize connection with the biometric device."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Release device resources safely."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if device is currently connected and active."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if device hardware is available on the system."""
        pass

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """Retrieve device hardware and firmware metadata."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        """Read a single incoming frame from the video stream."""
        pass

    @abstractmethod
    def start_stream(self) -> Generator[VideoFrame, None, None]:
        """Continuous generator yielding video frames."""
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """Halt active streaming."""
        pass
