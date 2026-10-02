import pytest
from src.devices.mock_l0_device import MockL0Device
from src.devices.base import DeviceStatus, DeviceType


def test_mock_device_lifecycle():
    device = MockL0Device(fps=30)
    assert not device.is_connected()
    
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
