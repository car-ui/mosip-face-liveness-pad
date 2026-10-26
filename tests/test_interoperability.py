from src.devices.base import DeviceType, VendorL1Adapter
from src.devices.interop import validate_device_contract
from src.devices.mock_l0_device import MockL0Device
from src.devices.webcam_device import WebcamCaptureDevice


def test_reference_device_capability_contracts_are_consistent():
    devices = [MockL0Device(), WebcamCaptureDevice(),
               VendorL1Adapter(vendor_name="Adapter A", device_id="SIM-A"),
               VendorL1Adapter(vendor_name="Adapter B", device_id="SIM-B")]
    results = [validate_device_contract(device) for device in devices]
    assert all(result.valid for result in results), [result.errors for result in results]
    assert all(not device.get_device_info().is_l1_secure for device in devices)
    assert all(device.get_capabilities().liveness_capabilities["hardware_liveness"] is False
               for device in devices)


def test_inconsistent_or_unknown_capability_claims_fail_closed():
    class MisreportingCamera(WebcamCaptureDevice):
        def get_capabilities(self):
            capabilities = super().get_capabilities()
            capabilities.device_type = DeviceType.HARDWARE_L1_BIOMETRIC
            capabilities.security_level = "L1_SECURE_HARDWARE"
            capabilities.supported_capture_modes.append("UNKNOWN_MODE")
            return capabilities

    result = validate_device_contract(MisreportingCamera())
    assert not result.valid
    assert any("different device types" in error for error in result.errors)
    assert any("unknown mode" in error for error in result.errors)
    assert any("L0 webcam cannot claim L1 security" in error for error in result.errors)


def test_simulated_l1_signing_is_per_instance_and_refuses_tampered_state():
    first = VendorL1Adapter(device_id="SIM-A")
    second = VendorL1Adapter(device_id="SIM-B")
    first.connect()
    second.connect()
    data = b"fixture biometric bytes"
    assert first.sign_biometric_data(data) != second.sign_biometric_data(data)
    first.simulate_tamper_alarm()
    try:
        first.sign_biometric_data(data)
        raise AssertionError("tampered simulated adapter signed data")
    except RuntimeError:
        pass
