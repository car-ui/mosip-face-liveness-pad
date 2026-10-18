"""Verify packaged native logs and measurement metadata without claiming hardware coverage."""
from pathlib import Path
import hashlib
import json
import math
import zipfile

ROOT = Path(__file__).resolve().parents[1] / "integrations/native"


def verify():
    validation = json.loads((ROOT / "validation.json").read_text(encoding="utf-8"))
    count = 0

    def digest(path, expected):
        nonlocal count
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Evidence checksum mismatch: {path.name}")
        count += 1

    for name, record in validation["checks"].items():
        path = ROOT / "evidence" / name
        if path.is_file() and "sha256" in record:
            digest(path, record["sha256"])
    for record in validation.values():
        if isinstance(record, dict) and "result_log" in record:
            digest(ROOT / record["result_log"], record["result_sha256"])
    report = json.loads((ROOT / "android-benchmark.json").read_text(encoding="utf-8"))
    adaptive = next(p for p in validation["adaptive_apks"] if p.get("abi") == "x86_64")
    if report["adaptive_app_sha256"] != adaptive["sha256"]:
        raise ValueError("Benchmark APK differs from current validated APK")
    for group, runs in report["runs"].items():
        if len(runs) != 3:
            raise ValueError("Expected three independent processes per build")
        for run in runs:
            path = ROOT / "evidence" / run["raw_log"]
            digest(path, run["raw_log_sha256"])
            text = path.read_text(encoding="utf-8")
            tests = "5 tests" if run["mode"] == "full_5_test_suite" else "1 test"
            if f"OK ({tests})" not in text or "FAILURES!!!" in text:
                raise ValueError(f"Instrumentation did not pass: {path.name}")
            prefix = "INSTRUMENTATION_RESULT: facepadBenchmarkJson="
            results = [json.loads(line[len(prefix):]) for line in text.splitlines() if line.startswith(prefix)]
            if len(results) != 1:
                raise ValueError(f"Expected one measured result: {path.name}")
            metrics = run["metrics"]
            if any(metrics.get(key) != value for key, value in results[0].items()):
                raise ValueError(f"Reported measurements differ from raw output: {path.name}")
            values = [metrics[key] for key in ["minMs", "p50Ms", "p95Ms", "maxMs"]]
            if not all(math.isfinite(v) and v >= 0 for v in values) or values != sorted(values):
                raise ValueError(f"Invalid latency observations: {path.name}")
            if metrics["modelSha256"] != validation["model_sha256"] or metrics["iterations"] != 100:
                raise ValueError(f"Model or sample count mismatch: {path.name}")
            if group == "adaptive_one_thread" and (metrics["availableProcessors"] != 1 or metrics["intraOpThreads"] != 1):
                raise ValueError(f"Adaptive run did not use one CPU/thread: {path.name}")
    models = ROOT.parents[1] / "assets/models"
    for name in ["face_landmarker.task", "facemesh_v2.onnx"]:
        manifest = json.loads((models / (name + ".json")).read_text(encoding="utf-8"))
        digest(models / name, manifest["sha256"])
        if name.endswith(".task"):
            with zipfile.ZipFile(models / name) as bundle:
                for member, record in manifest["components"].items():
                    if hashlib.sha256(bundle.read(member)).hexdigest() != record["sha256"]:
                        raise ValueError(f"Landmark bundle component changed: {member}")
    parity = json.loads((ROOT / "facemesh-parity.json").read_text(encoding="utf-8"))
    digest(models / "facemesh_v2.onnx", parity["onnx_sha256"])
    if len(parity["results"]) != 24 or any(not math.isfinite(v["max_abs_error"]) or v["max_abs_error"] > .002 for v in parity["results"]):
        raise ValueError("Landmark conversion parity record invalid")
    print(f"PASS {count} packaged evidence checksums; six Android measurement logs match reported values")
    print("Scope: evidence integrity only; no physical-device, camera or accuracy claim")


if __name__ == "__main__":
    verify()
