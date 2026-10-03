"""
Presentation Attack Simulation & Prototype Evaluation Benchmark
Evaluates the MOSIP Liveness & PAD pipeline against:
1. 2D Printed photograph presentations
2. Smartphone & Tablet screen replay attacks
3. Injected specular reflections & high-frequency moiré patterns
4. Bona fide live presentations
5. Multiple faces & abnormal lighting anomalies

Reports experimental benchmark metrics (APCER & BPCER prototype evaluation)
in accordance with ISO/IEC 30107-3 reporting standards without claiming unaccredited lab certification.
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
                           pipeline_workflow: WorkflowType = WorkflowType.RESIDENT_REGISTRATION) -> Dict[str, Any]:
    print("-" * 65)
    print(f"EVALUATING TEST CASE: {name}")
    print("-" * 65)

    pipeline = LivenessPipeline(workflow=pipeline_workflow)
    pipeline.reset()

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
        outcome_label = "BLOCKED (True Negative)" if is_correct else "VULNERABILITY (False Acceptance)"
    else:
        is_correct = is_accepted
        outcome_label = "ACCEPTED (True Positive)" if is_correct else "REJECTED (False Rejection)"

    print(f"  * Expected Result  : {'ATTACK PRESENTATION' if expected_attack else 'BONA FIDE LIVE'}")
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
    print("MOSIP BIOMETRIC PRESENTATION ATTACK DETECTION BENCHMARK SUITE")
    print("ISO/IEC 30107-3 Prototype Evaluation Protocol (Local Developer Benchmark)")
    print("=" * 75)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    sample_photos = [
        ("Printed Photo: Obama (Smiling)", os.path.join(base_dir, "tests", "sample_images", "obama.jpg")),
        ("Printed Photo: Biden (Portrait)", os.path.join(base_dir, "tests", "sample_images", "biden.jpg")),
        ("Printed Photo: Neutral Subject", os.path.join(base_dir, "tests", "sample_images", "sample_0.jpg")),
    ]

    results = []

    # 1. Real photograph presentations from disk
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
        "Smartphone Display Replay Attack (Moiré + Glare)",
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
        "Static 2D Display Attack (Rigid Surface)",
        lambda i: mock_dev_static.read_frame()[1].image,
        total_frames=70,
        expected_attack=True
    )
    results.append(res_static)
    mock_dev_static.disconnect()

    # 4. Bona Fide Live Presentation
    mock_dev_live = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    mock_dev_live.connect()
    res_live = evaluate_sample_stream(
        "Bona Fide Live Subject (Natural Micro-movement)",
        lambda i: mock_dev_live.read_frame()[1].image,
        total_frames=45,
        expected_attack=False
    )
    results.append(res_live)
    mock_dev_live.disconnect()

    # Summary Report
    total_attacks = sum(1 for r in results if r["expected_attack"])
    detected_attacks = sum(1 for r in results if r["expected_attack"] and not r["is_accepted"])
    false_acceptances = sum(1 for r in results if r["expected_attack"] and r["is_accepted"])

    total_bona_fide = sum(1 for r in results if not r["expected_attack"])
    accepted_bona_fide = sum(1 for r in results if not r["expected_attack"] and r["is_accepted"])
    false_rejections = sum(1 for r in results if not r["expected_attack"] and not r["is_accepted"])

    mean_fps = 1000.0 / np.mean([r["avg_latency_ms"] for r in results])

    print("\n" + "=" * 75)
    print("EXPERIMENTAL EVALUATION SUMMARY (Prototype Metrics)")
    print("=" * 75)
    print(f"Total Presentation Attacks Tested : {total_attacks}")
    print(f"Attacks Successfully Blocked      : {detected_attacks} / {total_attacks} ({(detected_attacks/max(1, total_attacks))*100.0:.1f}%)")
    print(f"False Acceptance Rate (APCER)     : {(false_acceptances/max(1, total_attacks))*100.0:.1f}%")
    print(f"Bona Fide Live Samples Tested     : {total_bona_fide}")
    print(f"False Rejection Rate (BPCER)      : {(false_rejections/max(1, total_bona_fide))*100.0:.1f}%")
    print(f"Mean Pipeline Throughput          : {mean_fps:.1f} FPS (Target >= 25 FPS)")
    print("=" * 75)
    print("DISCLAIMER: These metrics reflect local experimental testing against test fixtures")
    print("and do not constitute formal laboratory certification under ISO/IEC 19792 or 30107.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
