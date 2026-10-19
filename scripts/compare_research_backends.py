"""Compare detection and crop/model sensitivity; never report this as PAD accuracy.

Default inputs are the attributed static NASA fixture, a two-face composite and
a blank image. --camera explicitly reads a bounded live stream without saving
images. Scores are observations with unknown attack labels, not acceptance proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core.active_liveness import ActiveLivenessDetector
from src.core.face_detector import FaceQualityAssessor
from src.core.passive_pad import PassivePADDetector
from src.core.config import PADMode
from src.devices.webcam_device import WebcamCaptureDevice


def summarize(rows):
    summary = {}
    for name in ("haar", "yunet"):
        selected = [r for r in rows if r["detector"] == name]
        scores = [r["v2_score"] for r in selected if "v2_score" in r]
        summary[name] = {
            "frames": len(selected),
            "zeroFaces": sum(r["face_count"] == 0 for r in selected),
            "oneFace": sum(r["face_count"] == 1 for r in selected),
            "multipleFaces": sum(r["face_count"] > 1 for r in selected),
            "detectionMsP50": float(np.median([r["detection_ms"] for r in selected])) if selected else None,
            "detectionMsP95": float(np.percentile([r["detection_ms"] for r in selected], 95)) if selected else None,
            "v2ScoreRange": [min(scores), max(scores)] if scores else None,
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.frames <= 600:
        parser.error("Use 1 to 600 frames")
    detectors = {name: FaceQualityAssessor(detector_backend=name) for name in ("haar", "yunet")}
    models = {name: PassivePADDetector(str(ROOT / f"assets/models/minifasnet_{name}.onnx"),
                                      mode=PADMode.ONNX_ONLY) for name in ("v2", "v1se")}
    if any(not model._onnx_backend.is_available() for model in models.values()):
        parser.error("Both verified model files and manifests are required")
    active = ActiveLivenessDetector()
    rows = []
    camera = WebcamCaptureDevice() if args.camera else None
    photo = cv2.imread(str(ROOT / "tests/sample_images/astronaut.png"))
    small = cv2.resize(photo, (320, 320))
    fixtures = [("static_photo", photo), ("two_photo_faces", np.concatenate([small, small], axis=1)),
                ("blank", np.zeros((480, 640, 3), np.uint8))]
    try:
        if camera and not camera.connect():
            raise RuntimeError("Camera unavailable")
        for i in range(args.frames if camera else len(fixtures)):
            if camera:
                ok, frame = camera.read_frame()
                if not ok:
                    raise RuntimeError("Camera disconnected")
                label, image = "unlabelled_camera", frame.image
            else:
                label, image = fixtures[i]
            telemetry, _ = active.process_frame(image)
            for name, detector in detectors.items():
                started = time.perf_counter()
                faces = detector.detect_faces(image, landmark_boxes=telemetry["face_boxes"])
                row = {"frame": i, "source": label, "detector": name, "face_count": len(faces),
                       "landmark_face_count": len(telemetry["face_boxes"]),
                       "detection_ms": round((time.perf_counter() - started) * 1000, 3)}
                if len(faces) == 1:
                    face = faces[0]
                    box = (face.x, face.y, face.w, face.h)
                    row["quality_ok"] = detector.assess_quality(image, faces).is_acceptable
                    for variant, model in models.items():
                        result = model.evaluate_passive_liveness(image, box)
                        row[f"{variant}_score"] = result.liveness_score
                        row[f"{variant}_verdict"] = result.verdict.value
                    row["research_mean_live_score"] = (row["v2_score"] + row["v1se_score"]) / 2
                    # Crop sensitivity is measured on the same frame/model.
                    scores = []
                    for offset in (-4, 0, 4):
                        perturbed = (face.x + offset, face.y, face.w, face.h)
                        scores.append(models["v2"].evaluate_passive_liveness(image, perturbed).liveness_score)
                    row["v2_crop_shift_score_range"] = [min(scores), max(scores)]
                rows.append(row)
    finally:
        if camera:
            camera.disconnect()
        active.close()
    report = {"scope": "Detection and model/crop diagnostics only. No physical PAD labels, APCER/BPCER, identity or completed challenge proof.",
              "imagesSaved": False, "input": "camera" if args.camera else "static fixtures",
              "modelHashes": {n: hashlib.sha256((ROOT / f"assets/models/minifasnet_{n}.onnx").read_bytes()).hexdigest()
                              for n in models},
              "summary": summarize(rows), "observations": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
