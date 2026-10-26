# Face Liveness & Presentation Attack Detection

[![Python and Java CI](https://github.com/car-ui/mosip-face-liveness-pad/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/car-ui/mosip-face-liveness-pad/actions/workflows/ci.yml)
[![Android Camera SBI](https://github.com/car-ui/mosip-face-liveness-pad/actions/workflows/native-android.yml/badge.svg?branch=main)](https://github.com/car-ui/mosip-face-liveness-pad/actions/workflows/native-android.yml)

An offline research prototype for **MOSIP Decode 2026 · Problem 04**. It checks camera frames for face quality and presentation attacks, then requests random facial actions when the workflow requires additional verification.

The project includes a browser console, an OpenCV desktop demo, ONNX inference, workflow policies, signed offline model updates, evaluation tools, and patches for MOSIP clients and a reference camera SBI.

**[Quick start](#quick-start) · [Features](#features) · [Validation status](#validation-status) · [Native integration](#native-integration) · [Documentation](#documentation)**

> **Current scope:** A working research prototype with passing software and emulator checks. Live MOSIP workflows, physical device performance, representative PAD accuracy, and participant usability still need acceptance evidence. See the [submission status](docs/SUBMISSION_STATUS.md) and [requirement matrix](docs/REQUIREMENTS_MATRIX.md).

## Features

| Area | Included capabilities |
|---|---|
| Passive liveness and PAD | Local ONNX inference, face-quality checks, temporal evidence, and rejection on attacks or engine errors |
| Active verification | Random facial-action prompts, progress feedback, bounded retries, and action invalidation after face loss |
| Workflow policies | Separate resident, operator, and supervisor settings for thresholds, actions, timeouts, and retries |
| Demo interfaces | Browser console with preview and diagnostics; separate OpenCV desktop demo |
| Models and updates | Model provenance, checksum verification, signed offline updates, and downgrade protection |
| Evaluation and integration | Private dataset evaluation, threshold selection, capability checks, and pinned native client patches |

## Quick start

### Requirements

- **CPython 3.11** and Git.
- Internet access for the initial dependency installation. Inference and challenge generation run locally afterward.
- A webcam for physical-camera trials. The simulator works without one.

### Windows / PowerShell

```powershell
git clone https://github.com/car-ui/mosip-face-liveness-pad.git
cd mosip-face-liveness-pad
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python run_mds_service.py
```

<details>
<summary><strong>Linux and macOS setup</strong></summary>

```bash
git clone https://github.com/car-ui/mosip-face-liveness-pad.git
cd mosip-face-liveness-pad
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python run_mds_service.py
```

Linux desktop OpenCV may also require `libgl1` and `libglib2.0-0`.

</details>

Open **[http://127.0.0.1:4501](http://127.0.0.1:4501)** in your browser.

1. Choose a resident, operator, or supervisor workflow.
2. Select a simulator scenario or explicitly select **Physical webcam**.
3. Choose **Start verification** and follow the positioning and action prompts.
4. Inspect the result and local diagnostics.

The default source is a clearly labeled simulator. A disconnected physical camera returns an error. Settings are kept in memory unless offline persistence is configured.

### OpenCV desktop demo

```powershell
.\.venv\Scripts\python run_desktop_app.py --mock
```

Omit `--mock` to use a physical webcam. This window is the standalone prototype; native MOSIP integration is described below.

## Verification behavior

| Workflow | Acceptance policy |
|---|---|
| Resident registration | A sufficiently high passive score may pass after temporal checks; uncertainty requires active verification |
| Operator authentication | Active challenges are required, including when the passive score is high |
| Supervisor authentication | Active challenges are required under the supervisor policy |

- PAD continues during active verification. An action cannot override an attack or engine error.
- Suspect frames block capture immediately; a sustained attack verdict produces terminal rejection.
- Face loss or poor quality invalidates action progress and invokes the retry policy.
- Preview requests do not advance verification. Concurrent capture or configuration changes return HTTP 409.
- Simulator challenges require explicit test inputs; the capture service never marks them complete automatically.

A successful result from the Python demo returns an **application JPEG**. Official SBI signatures, ISO face records, registration packets, and identity matching belong to the native integration and require separate validation.

## Validation status

The latest verified source is [commit `450f877`](https://github.com/car-ui/mosip-face-liveness-pad/commit/450f877).

| Area | Available evidence | Remaining work |
|---|---|---|
| Python prototype | **227 tests passed locally**; Ubuntu and Windows CI passed | Representative human and attack evaluation |
| Java / ONNX | Portable gate and actual native inference checks passed in Ubuntu and Windows CI | Complete live client workflows and physical-device behavior |
| Reference camera SBI | Current source built and camera-disabled emulator instrumentation passed in [CI](https://github.com/car-ui/mosip-face-liveness-pad/actions/runs/40284447283) | Successful physical-camera actions, trusted device setup, and field testing |
| Android Registration Client | Pinned patch preparation and prior 17-test emulator evidence | Fresh current APK build and live camera-to-storage / identity flows |
| Desktop Registration Client | Pinned source reactor build and controlled controller / preview evidence | Live resident, operator, and supervisor UI acceptance |
| Performance and acceleration | Emulator baseline and host CPU/provider comparison | Physical ARM64 latency, memory, power, thermals, and actual GPU/NPU/NNAPI execution |

Software fixtures and camera-disabled emulator tests establish defined implementation behavior. They do not establish population accuracy, physical attack resistance, ISO certification, or production certificate trust. Earlier APK evidence predates some current source changes; [validation notes](docs/VALIDATION.md) record its scope.

## Native integration

The [native integration directory](integrations/native/README.md) contains shared Java engines, platform adapters, and patches for exact upstream revisions.

| Target | Upstream revision | Integration point |
|---|---|---|
| Desktop Registration Client | `935306e2fd38bff2803697468e595026b1d18cec` | Capture storage and role-specific authentication gates |
| Android Registration Client | `8f4643a694f3b5e66e0491f077a8630ab5667658` | Signed SBI response validation before capture storage |
| Reference camera SBI | `d1ec22a542294b798f5b9c5bb97428deabb2064b` | Camera-owned active session and exact-image evidence |

Prepare a **clean checkout at the corresponding revision**:

```powershell
python scripts/prepare_native_clients.py desktop path/to/registration-client
python scripts/prepare_native_clients.py android path/to/android-registration-client
python scripts/prepare_native_clients.py camera-sbi path/to/android-camera-mds
```

The Android client sends its cached face-capture policy through SBI `customOpts`. The reference SBI validates those settings and returns signed session evidence bound to the transaction and final image. The client independently checks that evidence against its current policy before storage. Both patched apps and a correctly provisioned, trusted test certificate are required.

For toolchains, build commands, trust requirements, and evidence limits, read the [native integration guide](docs/NATIVE_INTEGRATION.md), [camera SBI guide](docs/CAMERA_SBI_INTEGRATION.md), and [native policy guide](docs/NATIVE_POLICY.md).

## Configuration and API

| Environment variable | Purpose |
|---|---|
| `MOSIP_PAD_POLICY_FILE` | Enable validated offline policy persistence |
| `MOSIP_PAD_MODEL` | Select a compatible ONNX model file |
| `MOSIP_MDS_API_TOKEN` | Set the bearer token shared by the local service and external clients |

The console receives an ephemeral token from the local service. Mutating API endpoints require authentication. The service binds to `127.0.0.1:4501`, checks origins and hostnames, and disables response caching. Keep it local; another process running as the same user remains outside these protections.

- [API documentation](docs/API.md) and [local OpenAPI reference](http://127.0.0.1:4501/docs)
- [Offline configuration guide](docs/OFFLINE_POLICY.md)
- [Model card and preprocessing contract](docs/MODEL_CARD.md)

Models must match the declared input contract and pass integrity checks. The heuristic backend is a research fallback with no independent attack-accuracy claim. Signed model updates require approved keys; the development key needs deliberate opt-in. Audit logs omit images and redact sensitive fields, while their hash chain requires a separately trusted checkpoint to detect tampering.

## Run the checks

Run these commands from the repository root after installing the locked dependencies:

```powershell
.\.venv\Scripts\python -m pytest -q --junitxml=output/local/test-results.xml
.\.venv\Scripts\python scripts/verify_native_evidence.py
.\.venv\Scripts\python scripts/check_device_interoperability.py --output output/local/device-interoperability.json
```

On Linux or macOS, replace `.\.venv\Scripts\python` with `.venv/bin/python`. The interoperability check covers the webcam interface contract and simulated adapters; physical vendor support needs hardware verification.

<details>
<summary><strong>Portable Java capture-gate check</strong></summary>

Requires a JDK with support for `javac --release 8`:

```powershell
javac --release 8 -d output/local/java src/java_integration/*.java tests/java/NativeCaptureGateTest.java
java -cp output/local/java NativeCaptureGateTest
```

This checks session binding, challenge counts, rejection, payload binding, and one-use capture acceptance.

</details>

### Evaluate a private dataset

Use consented development and held-out test clips with separate participants and attack sources. The tooling validates the private manifest, selects a threshold using development results, and evaluates the frozen operating point on the test split. Reports include APCER/BPCER, class counts, nonresponses, attack groups, and processing latency.

Follow the [evaluation protocol](docs/EVALUATION_PROTOCOL.md) for the manifest and exact commands. Keep source videos and participant linkage private. The older `test_photo_spoof_simulation.py` contains fixture experiments whose results must not be presented as human liveness accuracy.

## Create a source package

```powershell
python scripts/package_release.py --worktree --output output/local/face-liveness-prototype.zip
```

The ZIP includes current source changes and non-ignored new files. Its manifest records the base commit, snapshot type, and every included file's SHA-256; the script verifies the archive and prints its checksum. Omit `--worktree` to package the committed tree.

`output/local/` and `tmp/` are ignored by Git. Keep private evaluation data there or outside the repository, and publish the source ZIP separately when a submission requires an artifact link.

## Documentation

| Topic | Read more |
|---|---|
| Completion and acceptance gaps | [Submission status](docs/SUBMISSION_STATUS.md) · [Requirement matrix](docs/REQUIREMENTS_MATRIX.md) · [Delivery status](docs/LOCAL_DELIVERY_STATUS.md) |
| Evaluation and scoring | [Evaluation protocol](docs/EVALUATION_PROTOCOL.md) · [Rubric scorecard](docs/EVALUATION_SCORECARD.md) |
| Architecture | [Technical design](docs/TECHNICAL_DESIGN.md) · [Sequence diagrams](docs/SEQUENCE_DIAGRAMS.md) |
| Native clients | [Integration guide](docs/NATIVE_INTEGRATION.md) · [Camera SBI](docs/CAMERA_SBI_INTEGRATION.md) · [Active challenges](docs/NATIVE_ACTIVE_CHALLENGES.md) |
| Evidence | [Validation notes](docs/VALIDATION.md) · [Native evidence report](integrations/native/validation.json) · [Android benchmark](docs/ANDROID_BENCHMARK.md) |
| Reliability and research | [Research review](docs/RESEARCH_AND_REBUILD.md) · [Reliability plan](docs/RELIABILITY_PLAN.md) |
| User experience | [Usability and accessibility protocol](docs/USABILITY_STUDY.md) |
| Presentation and submission | [Pitch deck](pitch/index.html) · [Demo and submission checklist](docs/DEMO_AND_SUBMISSION.md) · [Remaining work](docs/REMAINING_WORK_PLAN.md) |

## Third-party assets

See [third-party notices](THIRD_PARTY_NOTICES.md) and the [model card](docs/MODEL_CARD.md) for attribution and licenses. Model code and exported weights retain their upstream terms. Review the provenance of inherited sample images and the original facial landmark asset before redistributing a public submission package.
