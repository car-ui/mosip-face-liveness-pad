# Validation evidence

Local checks were run on Windows on 18 October 2026 with CPython 3.11.15 and the declared runtime dependencies. The source initially contained 64 tests; the revised suite contains 117. The latest completed run passed all 117 tests in a fresh dependency environment in 22.63 seconds. A Starlette warning notes its future TestClient preference for `httpx2`; the currently pinned `httpx` TestClient checks pass.

## Commands and scope

| Check | Observed result | What it establishes |
|---|---|---|
| `python -m pytest -q --junitxml=tmp/test-results.xml` | 117 passed | Python regression properties, detector fixtures, API contracts, model contract, update verification. Injected-score tests are labelled explicitly. |
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

CI is configured for Linux and Windows, including the Python suite and Java checks. Remote CI status must be checked for the actual pushed commit. Local passing results must not be described as a completed remote run.
