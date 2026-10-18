"""Developer simulation of pipeline decisions on a recorded photo and effects.

No input is a physical attack or a bona fide live subject. Results describe
fixture behavior only, and cannot estimate APCER, BPCER or ISO compliance.
"""

import os
import cv2
import numpy as np
import time
from typing import Dict, List, Any, Optional

from src.core.pipeline import LivenessPipeline, PipelineState, LivenessDecision
from src.core.config import WorkflowType, LivenessConfig
from src.devices.base import VideoFrame, MockScenario
from src.devices.mock_l0_device import MockL0Device


def evaluate_sample_stream(name: str,
                           generator_func,
                           total_frames: int = 90,
                           expected_attack: bool = True,
                           pipeline_workflow: WorkflowType = WorkflowType.RESIDENT_REGISTRATION,
                           passive_threshold: Optional[float] = None) -> Dict[str, Any]:
    print("-" * 65)
    print(f"EVALUATING TEST CASE: {name}")
    print("-" * 65)

    pipeline = LivenessPipeline(workflow=pipeline_workflow)
    pipeline.reset()
    if passive_threshold is not None:
        pipeline.policy.passive_threshold = passive_threshold

    latencies = []
    final_result = None
    active_prompt_seen = None

    for i in range(total_frames):
        t0 = time.perf_counter()
        frame_img = generator_func(i)
        if frame_img is None or frame_img.size == 0:
            continue

        v_frame = VideoFrame(
            frame_id=i + 1,
            timestamp_ms=time.time() * 1000.0,
            image=frame_img,
            width=frame_img.shape[1],
            height=frame_img.shape[0]
        )

        res = pipeline.process_frame(v_frame)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt)

        if res.state == PipelineState.ACTIVE_CHALLENGE and active_prompt_seen is None:
            active_prompt_seen = res.status_text

        if res.state in (PipelineState.CAPTURE_SUCCESS, PipelineState.ATTACK_REJECTED, PipelineState.MAX_RETRIES_EXCEEDED):
            final_result = res
            break

    if final_result is None:
        final_result = res

    is_accepted = (final_result.state == PipelineState.CAPTURE_SUCCESS)
    avg_latency = float(np.mean(latencies)) if latencies else 0.0

    # Decision correctness
    if expected_attack:
        is_correct = not is_accepted
        outcome_label = "FIXTURE REJECTED" if is_correct else "FIXTURE ACCEPTED"
    else:
        is_correct = is_accepted
        outcome_label = "SIMULATED SUCCESS" if is_correct else "SIMULATED SUCCESS NOT REACHED"

    print(f"  * Expected Result  : {'REJECT SIMULATED INPUT' if expected_attack else 'SIMULATED ACCEPTANCE'}")
    print(f"  * Pipeline State   : {final_result.state.value}")
    print(f"  * Decision Verdict : {final_result.decision.value}")
    print(f"  * Avg Latency      : {avg_latency:.2f} ms/frame (~{1000.0/max(0.1, avg_latency):.1f} FPS)")
    print(f"  * Outcome          : {outcome_label}")

    return {
        "name": name,
        "expected_attack": expected_attack,
        "is_accepted": is_accepted,
        "is_correct": is_correct,
        "state": final_result.state.value,
        "avg_latency_ms": avg_latency
    }


def main():
    print("=" * 75)
    print("MOSIP PIPELINE DEVELOPER SIMULATION")
    print("Recorded photo and synthetic effects; no physical or live-person evaluation")
    print("=" * 75)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    sample_photos = [
        ("Recorded NASA photo with synthetic noise", os.path.join(base_dir, "tests", "sample_images", "astronaut.png")),
    ]

    results = []

    # 1. Recorded photograph read from disk, not a printed-photo presentation.
    for label, path in sample_photos:
        if os.path.exists(path):
            img = cv2.imread(path)
            resized = cv2.resize(img, (640, 480))
            
            def make_photo_feeder(frame_idx, base_img=resized):
                noisy = base_img.copy()
                if frame_idx % 2 == 0:
                    noise = np.random.normal(0, 1.2, noisy.shape).astype(np.int8)
                    noisy = np.clip(noisy.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                return noisy

            res = evaluate_sample_stream(label, make_photo_feeder, total_frames=80, expected_attack=True)
            results.append(res)

    # 2. Simulated Smartphone Screen Replay Attack
    mock_dev_screen = MockL0Device(scenario=MockScenario.SCREEN_REPLAY_ATTACK)
    mock_dev_screen.connect()
    res_screen = evaluate_sample_stream(
        "Synthetic replay effects on recorded photo",
        lambda i: mock_dev_screen.read_frame()[1].image,
        total_frames=70,
        expected_attack=True
    )
    results.append(res_screen)
    mock_dev_screen.disconnect()

    # 3. Simulated Static Mock Presentation
    mock_dev_static = MockL0Device(scenario=MockScenario.STATIC_PHOTO_ATTACK)
    mock_dev_static.connect()
    res_static = evaluate_sample_stream(
        "Synthetic static-photo scenario",
        lambda i: mock_dev_static.read_frame()[1].image,
        total_frames=70,
        expected_attack=True
    )
    results.append(res_static)
    mock_dev_static.disconnect()

    # 4. Simulated success scenario. The source remains a recorded photograph.
    mock_dev_live = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    mock_dev_live.connect()
    res_live = evaluate_sample_stream(
        "Simulated success scenario using photo motion",
        lambda i: mock_dev_live.read_frame()[1].image,
        total_frames=45,
        expected_attack=False,
        passive_threshold=0.68
    )
    results.append(res_live)
    mock_dev_live.disconnect()

    # Summary Report
    total_attacks = sum(1 for r in results if r["expected_attack"])
    detected_attacks = sum(1 for r in results if r["expected_attack"] and not r["is_accepted"])
    false_acceptances = sum(1 for r in results if r["expected_attack"] and r["is_accepted"])

    mean_fps = 1000.0 / np.mean([r["avg_latency_ms"] for r in results])

    print("\n" + "=" * 75)
    print("SIMULATED FIXTURE RESULTS")
    print("=" * 75)
    print(f"Rejection fixtures                : {total_attacks}")
    print(f"Rejection fixtures rejected       : {detected_attacks} / {total_attacks}")
    print(f"Rejection fixtures accepted       : {false_acceptances}")
    print(f"Mean simulated throughput         : {mean_fps:.1f} FPS")
    print("=" * 75)
    print("No live subjects or physical attacks were tested.")
    print("These results cannot estimate population accuracy, APCER or BPCER.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
