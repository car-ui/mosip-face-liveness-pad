import pytest
import numpy as np
from src.devices.mock_l0_device import MockL0Device
from src.devices.base import DeviceStatus, DeviceType, MockScenario


def test_mock_device_lifecycle():
    device = MockL0Device(fps=30)
    assert not device.is_connected()
    assert device.is_available() is True
    
    # Test connection
    assert device.connect() is True
    assert device.is_connected() is True
    
    info = device.get_device_info()
    assert info.device_type == DeviceType.MOCK_L0_SIMULATOR
    assert info.is_l1_secure is True
    
    # Test frame read
    success, frame = device.read_frame()
    assert success is True
    assert frame is not None
    assert frame.width == 640
    assert frame.height == 480
    assert frame.image.shape == (480, 640, 3)
    
    # Test disconnect
    device.disconnect()
    assert not device.is_connected()


def test_mock_device_scenarios():
    scenarios = [
        MockScenario.BONA_FIDE_LIVE,
        MockScenario.STATIC_PHOTO_ATTACK,
        MockScenario.SCREEN_REPLAY_ATTACK,
        MockScenario.NO_FACE,
        MockScenario.MULTIPLE_FACES,
        MockScenario.POOR_LIGHTING_DARK,
        MockScenario.POOR_LIGHTING_BRIGHT,
        MockScenario.POOR_LIGHTING_UNEVEN,
        MockScenario.BLURRY_FRAME,
    ]
    
    for s in scenarios:
        device = MockL0Device(scenario=s)
        device.connect()
        success, frame = device.read_frame()
        assert success is True, f"Failed for scenario {s}"
        assert frame is not None
        assert frame.image.shape == (480, 640, 3)
        device.disconnect()


def test_mock_device_invalid_frame_scenario():
    device = MockL0Device(scenario=MockScenario.INVALID_FRAME)
    device.connect()
    success, frame = device.read_frame()
    assert success is False
    assert frame is None
    device.disconnect()


def test_mock_device_disconnect_scenario():
    device = MockL0Device(scenario=MockScenario.DEVICE_DISCONNECT, disconnect_after_frames=3)
    device.connect()
    
    # Frames 1, 2, 3 should succeed
    for _ in range(3):
        success, frame = device.read_frame()
        assert success is True
    
    # Beyond frame 3, device should simulate drop
    success, frame = device.read_frame()
    assert success is False
    assert not device.is_connected()


def test_mock_device_scripted_action():
    device = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    device.connect()
    device.script_action("BLINK", duration_frames=5)
    
    success, frame = device.read_frame()
    assert success is True
    assert frame is not None
    device.disconnect()


def test_device_capabilities_discovery():
    device = MockL0Device()
    caps = device.get_capabilities()
    assert caps.device_type == DeviceType.MOCK_L0_SIMULATOR
    assert caps.vendor == "MOSIP Open Source"
    assert caps.security_level == "L0_SIMULATED"
    assert "STREAM" in caps.supported_capture_modes
    assert (640, 480) in caps.supported_resolutions
    assert caps.liveness_capabilities["passive_pad"] is True


def test_vendor_l1_adapter_operations():
    from src.devices.base import VendorL1Adapter
    adapter = VendorL1Adapter(vendor_name="SupremaSecure", model_name="BioMiniL1")
    assert adapter.connect() is True
    assert adapter.is_connected() is True

    caps = adapter.get_capabilities()
    assert caps.vendor == "SupremaSecure"
    assert caps.security_level == "L1_SIMULATED"
    assert "CRYPTO_TOKEN" in caps.supported_capture_modes

    # Test cryptographic biometric token signing
    sample_biometric = b"SAMPLE_ISO_19794_5_BIOMETRIC_DATA"
    signature = adapter.sign_biometric_data(sample_biometric)
    assert len(signature) == 32  # SHA-256 HMAC digest length

    # Test hardware tamper status
    assert adapter.verify_tamper_status() is True
    adapter.simulate_tamper_alarm()
    assert adapter.verify_tamper_status() is False

    adapter.disconnect()
    assert not adapter.is_connected()
