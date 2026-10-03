"""
Common Face Capture Device Interface and Multi-Vendor Interoperability Framework
Conforms to MOSIP Device Service (MDS) hardware abstraction requirements:
- Complete vendor neutrality and device interoperability
- Decouples biometric processing from physical capture hardware
- Distinct L0 and L1 device abstraction hierarchy
- Structured capability discovery
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Generator, Tuple, Dict, Any, List
import numpy as np
import hashlib
import time


class DeviceType(str, Enum):
    PHYSICAL_L0_WEBCAM = "PHYSICAL_L0_WEBCAM"
    HARDWARE_L1_BIOMETRIC = "HARDWARE_L1_BIOMETRIC"
    MOCK_L0_SIMULATOR = "MOCK_L0_SIMULATOR"
    VENDOR_L1_ADAPTER = "VENDOR_L1_ADAPTER"


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
class DeviceCapabilities:
    """Structured hardware capability discovery for multi-vendor MOSIP interoperability."""
    device_type: DeviceType
    device_id: str
    vendor: str
    model: str
    firmware_version: str
    security_level: str  # "L0_BASIC", "L1_SECURE_HARDWARE"
    supported_capture_modes: List[str] = field(default_factory=lambda: ["STREAM", "STILL_FRAME"])
    supported_resolutions: List[Tuple[int, int]] = field(default_factory=lambda: [(640, 480), (1280, 720)])
    liveness_capabilities: Dict[str, Any] = field(default_factory=lambda: {
        "passive_pad": True,
        "active_challenge": True,
        "hardware_liveness": False
    })


@dataclass
class VideoFrame:
    frame_id: int
    timestamp_ms: float
    image: np.ndarray  # BGR format numpy array
    width: int
    height: int
    is_key_frame: bool = False
    metadata: Optional[Dict[str, Any]] = None


class BaseBiometricDevice(ABC):
    """
    Abstract Root Interface for all biometric capture devices in MOSIP.
    Ensures complete independence between biometric algorithms and physical sensors.
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
    def get_capabilities(self) -> DeviceCapabilities:
        """Retrieve structured hardware capabilities for multi-vendor interoperability."""
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


class L0Device(BaseBiometricDevice):
    """
    L0 Biometric Device Abstraction.
    Standard optical capture device without onboard cryptographic tamper protection.
    Used for general webcams and basic digital video cameras.
    """
    pass


class L1Device(BaseBiometricDevice):
    """
    L1 Biometric Device Abstraction.
    Secure biometric sensor featuring onboard tamper protection, cryptographic signing,
    and trusted hardware execution environments (TEE / SE).
    """

    @abstractmethod
    def sign_biometric_data(self, data: bytes) -> bytes:
        """Cryptographically sign captured biometric data using device private key."""
        pass

    @abstractmethod
    def verify_tamper_status(self) -> bool:
        """Check hardware tamper sensors and physical casing integrity."""
        pass


class VendorL1Adapter(L1Device):
    """
    Vendor L1 Biometric Hardware Adapter.
    Architectural integration point for vendor biometric hardware SDKs (e.g. Suprema, Idemia, Dermalog, Mantra).
    VendorL1Adapter demonstrates the integration contract and simulator behavior; actual L1 hardware
    requires vendor SDK/device integration. Provides simulated L1 cryptographic token signing and tamper
    verification in development and evaluation environments.
    """

    def __init__(self,
                 vendor_name: str = "GenericMOSIP_Vendor",
                 model_name: str = "SecureBioL1_v2",
                 device_id: str = "DEV-L1-VENDOR-001",
                 firmware_version: str = "v3.4.1"):
        self.vendor_name = vendor_name
        self.model_name = model_name
        self.device_id = device_id
        self.firmware_version = firmware_version
        self._is_connected = False
        self._is_streaming = False
        self._frame_count = 0
        self._tamper_compromised = False
        self._secret_key = b"MOSIP_L1_VENDOR_SECURE_TOKEN_2026"

    def connect(self) -> bool:
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        self._is_connected = False
        self._is_streaming = False

    def is_connected(self) -> bool:
        return self._is_connected

    def is_available(self) -> bool:
        return True

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            device_id=self.device_id,
            device_name=f"{self.vendor_name} {self.model_name} (Simulated L1)",
            device_type=DeviceType.VENDOR_L1_ADAPTER,
            serial_number=f"SN-{hashlib.sha256(self.device_id.encode()).hexdigest()[:8].upper()}",
            firmware_version=self.firmware_version,
            is_l1_secure=True,
            status=DeviceStatus.CONNECTED if self._is_connected else DeviceStatus.DISCONNECTED
        )

    def get_capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            device_type=DeviceType.VENDOR_L1_ADAPTER,
            device_id=self.device_id,
            vendor=self.vendor_name,
            model=self.model_name,
            firmware_version=self.firmware_version,
            security_level="L1_SIMULATED",
            supported_capture_modes=["STREAM", "STILL_FRAME", "CRYPTO_TOKEN"],
            supported_resolutions=[(640, 480), (1280, 720), (1920, 1080)],
            liveness_capabilities={
                "passive_pad": True,
                "active_challenge": True,
                "hardware_liveness": True,
                "subdermal_ir": False
            }
        )

    def sign_biometric_data(self, data: bytes) -> bytes:
        """Simulates on-chip cryptographic signature generation using HMAC-SHA256."""
        import hmac
        return hmac.new(self._secret_key, data, hashlib.sha256).digest()

    def verify_tamper_status(self) -> bool:
        """Returns True if device casing and tamper sensors report nominal status."""
        return not self._tamper_compromised

    def simulate_tamper_alarm(self) -> None:
        """Simulate hardware tamper compromise for testing."""
        self._tamper_compromised = True

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        if not self._is_connected:
            return False, None
        self._frame_count += 1
        # Generates a standard simulated frame with L1 watermark
        frame_img = np.full((480, 640, 3), 128, dtype=np.uint8)
        return True, VideoFrame(
            frame_id=self._frame_count,
            timestamp_ms=time.time() * 1000.0,
            image=frame_img,
            width=640,
            height=480,
            metadata={"l1_signed": True, "device_id": self.device_id}
        )

    def start_stream(self) -> Generator[VideoFrame, None, None]:
        self._is_streaming = True
        while self._is_streaming and self._is_connected:
            success, frame = self.read_frame()
            if success and frame:
                yield frame
            time.sleep(0.033)

    def stop_stream(self) -> None:
        self._is_streaming = False


# Backward compatibility alias
FaceCaptureDevice = BaseBiometricDevice
