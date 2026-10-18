"""Offline passive PAD evaluation on a private manifest. Does not evaluate active challenges."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import time
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.face_detector import FaceQualityAssessor
from src.core.passive_pad import PassivePADDetector
from src.core.config import PADMode, PADVerdict


def summarize(rows):
    groups = {}
    for label in ("attack", "bona_fide"):
        selected = [r for r in rows if r["label"] == label]
        classified = [r for r in selected if r["accepted"] is not None]
        groups[label] = {"clips": len(selected), "classified": len(classified),
                         "nonResponses": len(selected) - len(classified)}
    attacks = [r for r in rows if r["label"] == "attack" and r["accepted"] is not None]
    bona = [r for r in rows if r["label"] == "bona_fide" and r["accepted"] is not None]
    groups["APCER"] = sum(r["accepted"] for r in attacks) / len(attacks) if attacks else None
    groups["BPCER"] = sum(not r["accepted"] for r in bona) / len(bona) if bona else None
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSONL rows: path, label attack|bona_fide, pai, split=test")
    parser.add_argument("--model", required=True)
    parser.add_argument("--threshold", type=float, default=.82)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--output", type=Path, default=Path("output/local/dataset-evaluation.json"))
    args = parser.parse_args()
    if not 0 < args.threshold < 1 or args.frames < 1:
        parser.error("Threshold must be 0..1 and frame count must be positive")
    detector = PassivePADDetector(args.model, mode=PADMode.ONNX_ONLY, high_confidence_threshold=args.threshold)
    if not detector._onnx_backend.is_available():
        parser.error("A compatible ONNX model and manifest are required")
    quality = FaceQualityAssessor()
    rows, latencies = [], []
    for line in args.manifest.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("split") != "test" or entry.get("label") not in ("attack", "bona_fide"):
            parser.error("Use test-only rows with an explicit attack or bona_fide label")
        if entry["label"] == "attack" and not entry.get("pai"):
            parser.error("Attack rows require a presentation attack instrument group, pai")
        cap = cv2.VideoCapture(str(args.manifest.parent / entry["path"]))
        scores = []
        try:
            for _ in range(args.frames):
                ok, frame = cap.read()
                if not ok:
                    break
                start = time.perf_counter()
                faces = quality.detect_faces(frame)
                if quality.assess_quality(frame, faces).is_acceptable:
                    face = faces[0]
                    result = detector.evaluate_passive_liveness(frame, (face.x, face.y, face.w, face.h))
                    if result.verdict != PADVerdict.PROCESSING_ERROR:
                        scores.append(result.liveness_score)
                latencies.append((time.perf_counter() - start) * 1000)
        finally:
            cap.release()
        rows.append({"label": entry["label"], "pai": entry.get("pai", "bona_fide"),
                     "validFrames": len(scores),
                     "accepted": bool(np.mean(scores) >= args.threshold) if scores else None})
    if not rows:
        parser.error("The manifest contains no clips")
    by_pai = defaultdict(list)
    for row in rows:
        if row["label"] == "attack":
            by_pai[row["pai"]].append(row)
    report = {"scope": "Passive model only. Mean valid-frame score per clip. Not ISO certification or active workflow accuracy.",
              "nonResponsePolicy": "Clips without valid frames excluded from APCER/BPCER and counted separately.",
              "threshold": args.threshold, "modelHash": detector._onnx_backend.get_metadata().model_hash,
              "countsAndRates": summarize(rows),
              "attackGroups": {k: summarize(v) for k, v in by_pai.items()},
              "frameLatencyMs": {"p50": float(np.median(latencies)), "p95": float(np.percentile(latencies, 95))} if latencies else None,
              "clips": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "countsAndRates": report["countsAndRates"]}, indent=2))


if __name__ == "__main__":
    main()
