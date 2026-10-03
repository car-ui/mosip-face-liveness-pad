"""
Entry point to launch the MOSIP Desktop Registration Client
Supports:
- Live physical L0 webcam capture
- Mock biometric device simulation with 10 evaluator demonstration modes
"""

import sys
import argparse
from src.ui.desktop_client import DesktopRegistrationClient
from src.devices.base import MockScenario
from src.core.config import WorkflowType, PADMode


DEMO_MODES = {
    "1": ("Live Person (High Confidence Passive Pass)", MockScenario.BONA_FIDE_LIVE, 0.70),
    "2": ("Uncertain Passive -> Dynamic Active Challenge", MockScenario.BONA_FIDE_LIVE, 0.95),
    "3": ("Printed Photo Presentation Attack (PAD Rejection)", MockScenario.STATIC_PHOTO_ATTACK, 0.85),
    "4": ("Smartphone Screen Replay Attack (Moiré & Glare Rejection)", MockScenario.SCREEN_REPLAY_ATTACK, 0.85),
    "5": ("Static Photo against Active Challenge (Times Out & Fails)", MockScenario.STATIC_PHOTO_ATTACK, 0.95),
    "6": ("Multiple Faces Detection (Integrity Violation Rejection)", MockScenario.MULTIPLE_FACES, 0.85),
    "7": ("Poor Lighting Environment (Quality Rejection & User Guidance)", MockScenario.POOR_LIGHTING_DARK, 0.85),
    "8": ("Device Disconnect (Mid-stream Hardware Failure Handling)", MockScenario.DEVICE_DISCONNECT, 0.85),
    "9": ("Blurry Frame & Defocus (Sharpness Quality Rejection)", MockScenario.BLURRY_FRAME, 0.85),
    "10": ("No Face Detected (Positioning Guidance Prompt)", MockScenario.NO_FACE, 0.85)
}


def main():
    parser = argparse.ArgumentParser(description="MOSIP Desktop Registration Client - Face Liveness & PAD Subsystem")
    parser.add_argument("--mock", action="store_true", help="Launch using Mock L0 Simulator instead of physical webcam")
    parser.add_argument("--scenario", type=str, default="BONA_FIDE_LIVE",
                        choices=[s.value for s in MockScenario],
                        help="Select specific mock scenario (used with --mock)")
    parser.add_argument("--demo", type=str, default=None, choices=[str(i) for i in range(1, 11)],
                        help="Run an automated evaluator demonstration scenario (1 to 10)")
    parser.add_argument("--workflow", type=str, default="RESIDENT_REGISTRATION",
                        choices=["RESIDENT_REGISTRATION", "OPERATOR_AUTHENTICATION", "SUPERVISOR_AUTHENTICATION"],
                        help="Initial workflow profile")
    parser.add_argument("--resident-id", type=str, default=None,
                        help="Optional Resident ID for registration (e.g. RES-00123)")
    parser.add_argument("--diagnostic", action="store_true",
                        help="Launch directly in Evaluator Diagnostic Mode with technical telemetry HUD")
    parser.add_argument("--max-frames", type=int, default=None,
                        help="Optional maximum number of frames to process before auto-exit (for automated verification)")
    args = parser.parse_args()

    use_mock = args.mock or (args.demo is not None)
    mock_scenario = MockScenario.BONA_FIDE_LIVE

    if args.demo:
        label, scenario, threshold = DEMO_MODES[args.demo]
        print("=" * 65)
        print(f"LAUNCHING EVALUATOR DEMO #{args.demo}: {label}")
        print("=" * 65)
        mock_scenario = scenario
    elif args.scenario:
        try:
            mock_scenario = MockScenario(args.scenario)
        except ValueError:
            mock_scenario = MockScenario.BONA_FIDE_LIVE

    wf = WorkflowType(args.workflow)

    client = DesktopRegistrationClient(
        use_mock_device=use_mock,
        mock_scenario=mock_scenario,
        initial_workflow=wf,
        diagnostic_mode=args.diagnostic,
        resident_id=args.resident_id
    )

    if args.demo:
        _, _, threshold = DEMO_MODES[args.demo]
        client.pipeline.policy.passive_threshold = threshold

    client.start(max_frames=args.max_frames)


if __name__ == "__main__":
    main()
