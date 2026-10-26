"""Portable capability-contract checks shared by capture-device adapters.

Passing this validator establishes that an adapter describes its capabilities
consistently. It does not certify the hardware or prove an L1 trust chain.
"""

from dataclasses import dataclass
from typing import Tuple

from .base import BaseBiometricDevice, DeviceType


SUPPORTED_CAPTURE_MODES = {"STREAM", "STILL_FRAME", "CRYPTO_TOKEN"}
REQUIRED_LIVENESS_FLAGS = {"passive_pad", "active_challenge", "hardware_liveness"}


@dataclass(frozen=True)
class DeviceContractResult:
    device_id: str
    device_type: str
    valid: bool
    errors: Tuple[str, ...]


def validate_device_contract(device: BaseBiometricDevice) -> DeviceContractResult:
    """Check identity, capability shape, and security-level consistency."""
    errors = []
    try:
        info = device.get_device_info()
        caps = device.get_capabilities()
    except Exception as failure:
        return DeviceContractResult("", type(device).__name__, False,
                                    ("capability discovery failed: " + type(failure).__name__,))

    device_id = getattr(info, "device_id", "")
    device_type = getattr(info, "device_type", None)
    if not isinstance(device_id, str) or not device_id.strip() or len(device_id) > 128:
        errors.append("device info has an invalid device_id")
    if caps.device_id != device_id:
        errors.append("device info and capabilities use different device_id values")
    if caps.device_type != device_type:
        errors.append("device info and capabilities use different device types")
    for name in ("vendor", "model", "firmware_version", "security_level"):
        value = getattr(caps, name, None)
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            errors.append("capabilities have an invalid " + name)

    modes = caps.supported_capture_modes
    if not isinstance(modes, list) or not modes:
        errors.append("supported_capture_modes must be a non-empty list without duplicates")
    elif any(not isinstance(mode, str) for mode in modes):
        errors.append("supported_capture_modes contains a non-string mode")
    elif len(set(modes)) != len(modes):
        errors.append("supported_capture_modes contains a duplicate mode")
    elif any(mode not in SUPPORTED_CAPTURE_MODES for mode in modes):
        errors.append("supported_capture_modes contains an unknown mode")

    resolutions = caps.supported_resolutions
    if not isinstance(resolutions, list) or not resolutions:
        errors.append("supported_resolutions must be a non-empty list")
    else:
        for resolution in resolutions:
            if (not isinstance(resolution, tuple) or len(resolution) != 2
                    or any(not isinstance(value, int) or isinstance(value, bool)
                           or value < 1 or value > 8192 for value in resolution)):
                errors.append("supported_resolutions contains an invalid width/height pair")
                break

    flags = caps.liveness_capabilities
    if not isinstance(flags, dict) or not REQUIRED_LIVENESS_FLAGS.issubset(flags):
        errors.append("liveness_capabilities is missing required boolean flags")
    elif any(not isinstance(flags[name], bool) for name in REQUIRED_LIVENESS_FLAGS):
        errors.append("liveness_capabilities contains a non-boolean required flag")

    is_l1_secure = getattr(info, "is_l1_secure", None)
    if not isinstance(is_l1_secure, bool):
        errors.append("device info has an invalid is_l1_secure flag")
        is_l1_secure = False

    if device_type == DeviceType.PHYSICAL_L0_WEBCAM:
        if caps.security_level != "L0_BASIC" or is_l1_secure:
            errors.append("L0 webcam cannot claim L1 security")
        if isinstance(flags, dict) and flags.get("hardware_liveness") is True:
            errors.append("L0 webcam cannot claim hardware liveness")
    elif device_type == DeviceType.MOCK_L0_SIMULATOR:
        if caps.security_level != "L0_SIMULATED" or is_l1_secure:
            errors.append("L0 simulator must be marked simulated and non-secure")
        if isinstance(flags, dict) and flags.get("hardware_liveness") is True:
            errors.append("L0 simulator cannot claim hardware liveness")
    elif device_type == DeviceType.VENDOR_L1_ADAPTER:
        if caps.security_level != "L1_SIMULATED" or is_l1_secure:
            errors.append("development vendor adapter must be marked simulated and non-secure")
        if isinstance(flags, dict) and flags.get("hardware_liveness") is True:
            errors.append("simulated vendor adapter cannot claim hardware liveness")
    elif device_type == DeviceType.HARDWARE_L1_BIOMETRIC:
        if caps.security_level != "L1_SECURE_HARDWARE" or not is_l1_secure:
            errors.append("physical L1 device must report its verified secure level")
        if "CRYPTO_TOKEN" not in modes:
            errors.append("physical L1 device must expose its signing capability")
        if not callable(getattr(device, "sign_biometric_data", None)):
            errors.append("physical L1 device has no signing method")
        if not callable(getattr(device, "verify_tamper_status", None)):
            errors.append("physical L1 device has no tamper-status method")
    else:
        errors.append("device type is not supported by this interoperability contract")

    return DeviceContractResult(
        device_id if isinstance(device_id, str) else "",
        getattr(device_type, "value", str(device_type)),
        not errors,
        tuple(errors),
    )
