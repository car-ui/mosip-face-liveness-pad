"""
Common Face Capture Device Interface and Device Adapter Pattern
Ensures independence from any specific biometric hardware vendor.
Supports L0/L1 compliant streams, physical webcams, and mock devices.
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
        """Check if device is ready and healthy."""
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
