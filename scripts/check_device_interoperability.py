"""Run the portable capability contract against local reference adapters."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.devices.base import VendorL1Adapter
from src.devices.interop import validate_device_contract
from src.devices.mock_l0_device import MockL0Device
from src.devices.webcam_device import WebcamCaptureDevice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    devices = [
        MockL0Device(),
        WebcamCaptureDevice(),
        VendorL1Adapter(vendor_name="Reference Adapter A", device_id="SIM-L1-A"),
        VendorL1Adapter(vendor_name="Reference Adapter B", device_id="SIM-L1-B"),
    ]
    results = [validate_device_contract(device) for device in devices]
    report = {
        "scope": "Capability contract only. Simulated adapters do not establish physical L1 or vendor interoperability.",
        "valid": all(result.valid for result in results),
        "adapters": [asdict(result) for result in results],
    }
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
