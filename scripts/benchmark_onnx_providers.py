"""Compare ONNX Runtime providers on one fixed tensor; this is not PAD accuracy."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np


def _shape(input_shape):
    """Use the model's fixed dimensions, replacing dynamic NCHW axes safely."""
    if len(input_shape) != 4:
        raise ValueError("Expected a four-dimensional NCHW model input")
    fallback = (1, 3, 80, 80)
    result = []
    for index, dimension in enumerate(input_shape):
        if isinstance(dimension, int) and dimension > 0:
            result.append(dimension)
        else:
            result.append(fallback[index])
    if result[0] != 1:
        raise ValueError("Benchmark uses a batch size of one")
    return tuple(result)


def _profile_assignments(profile_path):
    try:
        events = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    assignments = {}
    for event in events:
        provider = event.get("args", {}).get("provider")
        if isinstance(provider, str) and provider:
            assignments[provider] = assignments.get(provider, 0) + 1
    return assignments, bool(assignments)


def _measure(session, input_name, tensor, warmups, iterations):
    for _ in range(warmups):
        session.run(None, {input_name: tensor})
    durations = []
    output = None
    for _ in range(iterations):
        started = time.perf_counter_ns()
        output = session.run(None, {input_name: tensor})
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    return output, {
        "p50Ms": round(float(np.percentile(durations, 50)), 4),
        "p95Ms": round(float(np.percentile(durations, 95)), 4),
        "minMs": round(min(durations), 4),
        "maxMs": round(max(durations), 4),
    }


def benchmark(model_path, output_path, warmups=10, iterations=100,
              tolerance=1e-4, requested=None):
    import onnxruntime as ort

    available = ort.get_available_providers()
    providers = requested or [name for name in available if name != "CPUExecutionProvider"]
    if len(set(providers)) != len(providers):
        raise ValueError("Provider list contains duplicates")
    if "CPUExecutionProvider" in providers:
        raise ValueError("CPUExecutionProvider is the reference and must not be listed as a candidate")
    unknown = [name for name in providers if name not in available]
    if unknown:
        raise ValueError("Requested provider is not available: " + ", ".join(unknown))
    if warmups < 0 or not 1 <= iterations <= 10000:
        raise ValueError("Use non-negative warmups and 1..10000 iterations")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Tolerance must be finite and non-negative")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_path = model_path.resolve(strict=True)
    cpu = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    model_input = cpu.get_inputs()[0]
    if model_input.type != "tensor(float)":
        raise ValueError("Only FP32 model inputs are supported")
    shape = _shape(model_input.shape)
    tensor = np.random.default_rng(42017).standard_normal(shape, dtype=np.float32)
    baseline, cpu_timing = _measure(cpu, model_input.name, tensor, warmups, iterations)
    results = [{
        "provider": "CPUExecutionProvider",
        "activeProviders": cpu.get_providers(),
        "timing": cpu_timing,
        "maxAbsErrorVsCpu": 0.0,
        "providerAssignments": {},
        "acceleratedNodeAssignmentsObserved": None,
        "executionObserved": False,
    }]

    for provider in providers:
        options = ort.SessionOptions()
        options.enable_profiling = True
        options.profile_file_prefix = str(output_path.with_name(
            output_path.stem + "-" + provider.replace("ExecutionProvider", "")
        ))
        candidate = ort.InferenceSession(
            str(model_path), options, providers=[provider, "CPUExecutionProvider"]
        )
        output, timing = _measure(candidate, model_input.name, tensor, warmups, iterations)
        if len(output) != len(baseline):
            raise ValueError(provider + " returned a different output count from CPU")
        for actual, expected in zip(output, baseline):
            if actual.shape != expected.shape:
                raise ValueError(provider + " returned a different output shape from CPU")
            if actual.size == 0:
                raise ValueError(provider + " returned an empty output")
            if not np.isfinite(actual).all() or not np.isfinite(expected).all():
                raise ValueError(provider + " produced a non-finite output")
        max_error = max(float(np.max(np.abs(actual - expected)))
                        for actual, expected in zip(output, baseline))
        profile_path = candidate.end_profiling()
        assignments, observed = _profile_assignments(profile_path)
        results.append({
            "provider": provider,
            "activeProviders": candidate.get_providers(),
            "timing": timing,
            "maxAbsErrorVsCpu": max_error,
            "withinTolerance": max_error <= tolerance,
            "providerAssignments": assignments,
            "acceleratedNodeAssignmentsObserved": sum(
                count for name, count in assignments.items() if name != "CPUExecutionProvider"
            ) if observed else None,
            "executionObserved": observed,
            "profile": str(Path(profile_path).resolve()),
        })

    report = {
        "scope": "Same-input provider latency and numerical parity only; no camera, PAD accuracy, hardware attestation, or energy claim.",
        "model": model_path.name,
        "modelSha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "inputShape": list(shape),
        "availableProviders": available,
        "warmups": warmups,
        "iterations": iterations,
        "absoluteParityTolerance": tolerance,
        "results": results,
        "parityPassed": all(row.get("withinTolerance", True) for row in results),
        "accelerationObserved": any(
            isinstance(row.get("acceleratedNodeAssignmentsObserved"), int)
            and row["acceleratedNodeAssignmentsObserved"] > 0 for row in results
        ),
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("assets/models/minifasnet_v2.onnx"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", action="append", dest="providers",
                        help="Provider to compare; repeat to select multiple. Defaults to all installed non-CPU providers.")
    parser.add_argument("--warmups", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    args = parser.parse_args()
    try:
        report = benchmark(args.model, args.output, args.warmups, args.iterations,
                           args.tolerance, args.providers)
    except (ImportError, OSError, ValueError, RuntimeError) as failure:
        parser.error(str(failure))
    print(json.dumps({
        "output": str(args.output),
        "parityPassed": report["parityPassed"],
        "accelerationObserved": report["accelerationObserved"],
        "results": [{"provider": item["provider"], **item["timing"],
                     "maxAbsErrorVsCpu": item["maxAbsErrorVsCpu"],
                     "acceleratedNodeAssignmentsObserved": item["acceleratedNodeAssignmentsObserved"]}
                    for item in report["results"]],
    }, indent=2))
    return 0 if report["parityPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
