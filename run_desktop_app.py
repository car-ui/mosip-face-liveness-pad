"""Launch the face-liveness research prototype with a webcam or explicit simulator.

This program is separate from the official MOSIP Registration Client.
"""

import sys
import argparse
from src.ui.desktop_client import DesktopRegistrationClient
from src.devices.base import MockScenario
from src.core.config import WorkflowType, PADMode


DEMO_MODES = {
    "1": ("Simulated portrait fixture; result depends on policy", MockScenario.BONA_FIDE_LIVE, 0.70),
    "2": ("Simulated fixture with a stricter passive threshold", MockScenario.BONA_FIDE_LIVE, 0.95),
    "3": ("Synthetic printed-photo fixture", MockScenario.STATIC_PHOTO_ATTACK, 0.85),
    "4": ("Synthetic screen-replay fixture", MockScenario.SCREEN_REPLAY_ATTACK, 0.85),
    "5": ("Static fixture against active verification", MockScenario.STATIC_PHOTO_ATTACK, 0.95),
    "6": ("Synthetic multiple-face fixture", MockScenario.MULTIPLE_FACES, 0.85),
    "7": ("Synthetic low-light fixture", MockScenario.POOR_LIGHTING_DARK, 0.85),
    "8": ("Simulated device disconnect", MockScenario.DEVICE_DISCONNECT, 0.85),
    "9": ("Synthetic blurred fixture", MockScenario.BLURRY_FRAME, 0.85),
    "10": ("Synthetic no-face fixture", MockScenario.NO_FACE, 0.85)
}


def main():
    parser = argparse.ArgumentParser(description="Face liveness research prototype; separate from the official MOSIP Registration Client")
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
        print(f"LAUNCHING SIMULATED PROTOTYPE DEMO #{args.demo}: {label}")
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
