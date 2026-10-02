"""
Entry point to launch the MOSIP Desktop Registration Client
"""

import sys
import argparse
from src.ui.desktop_client import DesktopRegistrationClient


def main():
    parser = argparse.ArgumentParser(description="MOSIP Desktop Registration Client - Face Liveness & PAD")
    parser.add_argument("--mock", action="store_true", help="Launch directly using Mock L0 Simulator instead of live webcam")
    args = parser.parse_args()

    client = DesktopRegistrationClient(use_mock_device=args.mock)
    client.start()


if __name__ == "__main__":
    main()
