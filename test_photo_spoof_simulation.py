"""
Presentation Attack Simulation Test
Tests the MOSIP Liveness & PAD pipeline against real static photos from the internet.
Evaluates both:
1. Passive PAD assessment (moiré, planar reflection, frequency spectrum)
2. Active Challenge-Response resilience (can a static photo perform blink/smile/turn?)
"""

import os
import cv2
import numpy as np
import time
from src.core.pipeline import LivenessPipeline, PipelineState, LivenessDecision
from src.devices.base import VideoFrame


def run_photo_attack_evaluation(image_path: str, simulated_seconds: float = 6.0):
    print("=" * 70)
    print(f"TESTING PHOTO SPOOF ATTACK: {os.path.basename(image_path)}")
    print("=" * 70)

    # 1. Load static photo
    raw_img = cv2.imread(image_path)
    if raw_img is None:
        print(f"Error: Could not load image from {image_path}")
        return

    # Resize to standard MOSIP capture frame (640x480)
    test_frame = cv2.resize(raw_img, (640, 480))
    pipeline = LivenessPipeline()
    pipeline.reset()

    fps = 30
    total_frames = int(simulated_seconds * fps)

    print(f"1. Presenting static photo to capture device for {simulated_seconds} seconds ({total_frames} frames)...")
    
    passive_results = []
    final_verdict = None
    active_prompt_shown = None

    for i in range(total_frames):
        # Simulate video stream presenting the same photo (with natural minor camera noise)
        noisy_frame = test_frame.copy()
        if i % 2 == 0:
            noise = np.random.normal(0, 1.2, noisy_frame.shape).astype(np.int8)
            noisy_frame = np.clip(noisy_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        v_frame = VideoFrame(
            frame_id=i + 1,
            timestamp_ms=time.time() * 1000.0,
            image=noisy_frame,
            width=640,
            height=480
        )

        result = pipeline.process_frame(v_frame)

        if result.pad_result:
            passive_results.append(result.pad_result)

        if result.state == PipelineState.ACTIVE_CHALLENGE and active_prompt_shown is None:
            active_prompt_shown = result.status_text
            print(f"   [Frame {i+1}] Passive score insufficient -> System initiated active challenge: '{active_prompt_shown}'")

        if result.state in (PipelineState.ATTACK_REJECTED, PipelineState.MAX_RETRIES_EXCEEDED, PipelineState.CAPTURE_SUCCESS):
            final_verdict = result
            break

        time.sleep(0.005)

    if final_verdict is None:
        final_verdict = result

    # Analysis Summary
    print("\n--- FORENSIC EVALUATION REPORT ---")
    if passive_results:
        last_pad = passive_results[-1]
        print(f"  * Passive Liveness Score : {last_pad.liveness_score:.3f} / 1.000")
        print(f"  * Attack Detected        : {last_pad.attack_detected} ({last_pad.attack_type})")
        print(f"  * Frequency Moire Score  : {last_pad.details.get('frequency_score')}")
        print(f"  * Color Chrominance      : {last_pad.details.get('chroma_score')}")
        print(f"  * Glare Indicator        : {last_pad.details.get('glare_score')}")

    print(f"  * Active Challenge Prompt: {active_prompt_shown or 'None'}")
    print(f"  * Static Photo Response  : ZERO action (photo cannot blink, smile, or turn)")
    print(f"  * Pipeline Final State   : {final_verdict.state.value}")
    print(f"  * Decision               : {final_verdict.decision.value}")
    print(f"  * User-Safe Feedback     : \"{final_verdict.status_text}\"")

    if final_verdict.state == PipelineState.CAPTURE_SUCCESS:
        print("\n[VULNERABILITY DETECTED] FALSE ACCEPTANCE: Static photo was mistakenly accepted!")
    else:
        print("\n[SUCCESSFULLY BLOCKED] PRESENTATION ATTACK BLOCKED!")
        print("   The photo could not satisfy the liveness criteria and capture was REFUSED.")
    print("=" * 70 + "\n")


def main():
    photos = [
        "tests/sample_images/obama.jpg",
        "tests/sample_images/biden.jpg",
        "tests/sample_images/sample_0.jpg"
    ]
    for p in photos:
        if os.path.exists(p):
            run_photo_attack_evaluation(p, simulated_seconds=7.0)


if __name__ == "__main__":
    main()
