# Validation evidence

Local checks were run on Windows on 18 October 2026 with CPython 3.11.15 and the declared runtime dependencies. The source initially contained 64 tests; the revised suite contains 120. The latest completed run passed all 120 tests in a fresh dependency environment in 17.54 seconds. An earlier source ZIP extraction passed all 119 tests before the final timeout regression was added. A Starlette warning notes its future TestClient preference for `httpx2`; the currently pinned `httpx` TestClient checks pass.

## Commands and scope

| Check | Observed result | What it establishes |
|---|---|---|
| `python -m pytest -q --junitxml=tmp/test-results.xml` | 120 passed | Python regression properties, detector fixtures, API contracts, model contract, update verification. Injected-score tests are labelled explicitly. |
| `javac --release 8 ...` followed by `java NativeCaptureGateTest` | 20 checks passed | Portable policy/transport checks, including session binding, required action counts, replayed sequence rejection, exact-payload and single-use acceptance. |
| `scripts/export_minifasnet.py` | Six conversion comparisons passed; maximum absolute logit difference `2.6226043701171875e-06` | ONNX/PyTorch conversion parity on deterministic tensors. Not attack accuracy. |
| Packaged ONNX tests | Model loads, BGR 0..255 input verified, class index 1 verified, altered manifest checksum rejected | Packaged inference contract and basic runtime execution. |
| Browser console | Simulator screen-replay fixture rejected with safe user guidance and restart control | Local browser-to-service rejection using a fixture. Not a real physical screen attack. |
| Console diagnostics | Model mode shown after service restart; simulated device and `NOT_CERTIFIED` shown | Runtime mode visibility and source transparency. |
| Narrow console rendering | Stacked layout rendered without horizontal overflow at the tool-reported viewport | Responsive layout inspection. A requested 390-pixel override was not honored by the embedded browser, which reported 834 pixels, so a 390-pixel device test is not claimed. |
| Pitch | All nine slides inspected in browser; no content outside slide bounds | Rendered deck readability and layout. |

## Security regressions

The suite checks that an active action cannot override PAD attack or processing failure, mandatory operator/supervisor actions cannot be skipped by high passive scores, face loss clears partial evidence, terminal attack rejection cannot restart automatically, invalid pixel layouts and detector exceptions fail closed, strict ONNX errors cannot silently invoke heuristics, and invalid/nonfinite scores cannot pass.

API checks cover bearer/origin/hostname rejection, one capture owner, nonmutating preview, exact JPEG digest, post-capture image-reference clearing, invalid configuration atomicity, explicit simulated L1 disclosure, and the absence of automatic mock action completion. Model update checks cover metadata tampering, invalid versions, path traversal, persisted downgrade protection, explicit key requirements, and Ed25519 verification. Audit checks exercise nested redaction and hash linkage. Metric tests verify denominators and empty-data behavior.

## Limits

No physical L1 device, native MOSIP client E2E, human active-challenge completion, independent PAD dataset, ISO conformance evaluation, or Android performance/energy measurement is established by these checks. No camera subject or attack session is manufactured from a simulator label. The dataset evaluation tool has denominator tests, but it has not been run on a consented representative physical attack dataset.

## Native checkpoint follow-up

The additional [native validation report](../integrations/native/validation.json) records compilation of the patched official desktop reactor and execution of its actual resident and authentication controllers with synthetic ISO input. The identity matcher is an explicit test double, and the rejected inputs never reach it. A high-passive-score portrait also fails operator/supervisor authentication because active evidence is missing. The Java inference check executes the packaged ONNX graph and compares its output with Python. The Android app and test APKs build, and four API 34 emulator tests pass, covering actual ONNX inference and rejection before resident/operator-onboarding storage. The SBI parser and repositories are explicit test doubles. These are stronger integration checks than the standalone Java policy component, but do not establish complete native camera/UI workflows or physical attack accuracy. See the [native build notes](../integrations/native/README.md) for pins, reproducible preparation, and incomplete behavior.

The pitch's evidence row now reflects the native checks. Its layout is unchanged. A fresh browser rendering check for that text revision was unavailable because local browser access was disabled in Work settings; the earlier deck revision had been visually reviewed.

GitHub Actions run [39144395667](https://github.com/car-ui/mosip-face-liveness-pad/actions/runs/39144395667) completed successfully for code commit `ad9be3392396fc2d02a122b16df6a4e0eb8f4cb7`. Both `test (ubuntu-latest)` and `test (windows-latest)` succeeded. The status was read from GitHub's authenticated API. The source ZIP for that commit contained 80 tracked files plus its release manifest, passed ZIP integrity and all 80 per-file SHA-256 checks, and passed all 119 Python tests after fresh extraction. Final evidence-only commits can change document/archive hashes without changing the tested implementation.

## CPU model timing

A separate warm benchmark ran 100 evaluations after ten warmups using one synthetic 80x80 crop, ONNX Runtime CPU, and two inference threads. Median evaluation time was 2.63 ms and p95 was 3.70 ms. This includes model preprocessing but excludes camera IO, face detection, full-workflow latency, Android performance, and attack accuracy. Exact measurements are in `model-runtime-benchmark.json`.

## Browser verification expiry

The packaged model scored the synthetic replay fixture highly, so it is not a demonstrated passive replay detector. Motion/action checks prevented acceptance. Browser testing also exposed transparent retries of HTTP 408. Verification expiry now returns HTTP 200 with `responseStatus: TIMEOUT` and empty biometrics. After the fix, one 30-second browser attempt completed, the Start verification button became available, metrics showed exactly one TIMEOUT session, and `captureBusy` was false. No automatic second capture started.
