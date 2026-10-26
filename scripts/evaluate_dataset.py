"""Offline passive PAD evaluation on a private manifest. Does not evaluate active challenges."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.face_detector import FaceQualityAssessor
from src.core.passive_pad import PassivePADDetector
from src.core.config import (PADMode, PADVerdict, MIN_PASSIVE_THRESHOLD,
                             MAX_PASSIVE_THRESHOLD)
from scripts.pad_manifest import load_private_manifest, ManifestError, SPLIT_AUDIT


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


def validate_threshold(threshold):
    """Require an operating point accepted by both API and native policies."""
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or not MIN_PASSIVE_THRESHOLD <= threshold <= MAX_PASSIVE_THRESHOLD):
        raise ValueError("Threshold must be within the supported range {:.2f}..{:.2f}".format(
            MIN_PASSIVE_THRESHOLD, MAX_PASSIVE_THRESHOLD))
    return float(threshold)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private master JSONL: path, label, split, subject_group; attacks also require pai and attack_source_group")
    parser.add_argument("--model", required=True)
    parser.add_argument("--threshold", type=float, default=.82)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--split", choices=("development", "test"), default="test",
                        help="Evaluate exactly this manifest split; use development reports only for calibration")
    parser.add_argument("--output", type=Path, default=Path("output/local/dataset-evaluation.json"))
    args = parser.parse_args()
    try:
        args.threshold = validate_threshold(args.threshold)
    except ValueError as failure:
        parser.error(str(failure))
    if args.frames < 1:
        parser.error("Frame count must be positive")
    detector = PassivePADDetector(args.model, mode=PADMode.ONNX_ONLY, high_confidence_threshold=args.threshold)
    if not detector._onnx_backend.is_available():
        parser.error("A compatible ONNX model and manifest are required")
    quality = FaceQualityAssessor()
    try:
        manifest_rows = load_private_manifest(args.manifest)
    except (OSError, UnicodeDecodeError, ManifestError) as failure:
        parser.error(str(failure))
    selected_entries = [entry for entry in manifest_rows if entry["split"] == args.split]
    rows, latencies = [], []
    for entry in selected_entries:
        cap = cv2.VideoCapture(str(entry["path"]))
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
        mean_score = float(np.mean(scores)) if scores else None
        rows.append({"label": entry["label"], "pai": entry["pai"],
                     "validFrames": len(scores),
                     "meanLiveScore": mean_score,
                     "accepted": bool(mean_score >= args.threshold) if mean_score is not None else None})
    if not rows:
        parser.error("The manifest contains no clips")
    by_pai = defaultdict(list)
    for row in rows:
        if row["label"] == "attack":
            by_pai[row["pai"]].append(row)
    report = {"scope": "Passive model only. Mean valid-frame score per clip. Not ISO certification or active workflow accuracy.",
              "dataSplit": args.split,
              "splitAudit": SPLIT_AUDIT,
              "nonResponsePolicy": "Clips without valid frames excluded from APCER/BPCER and counted separately.",
              "threshold": args.threshold, "framesPerClipLimit": args.frames,
              "modelHash": detector._onnx_backend.get_metadata().model_hash,
              "countsAndRates": summarize(rows),
              "attackGroups": {k: summarize(v) for k, v in by_pai.items()},
              "frameLatencyMs": {"p50": float(np.median(latencies)), "p95": float(np.percentile(latencies, 95))} if latencies else None,
              "clips": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "countsAndRates": report["countsAndRates"]}, indent=2))


if __name__ == "__main__":
    main()
