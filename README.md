# Face liveness and presentation attack detection

An offline research prototype for MOSIP Decode 2026, Problem 04. It processes camera frames, checks face quality and passive PAD, and asks for randomly selected facial actions when policy requires them. An attack, engine error, or failed challenge prevents the prototype from returning a captured image.

The repository includes a local browser console, an OpenCV desktop demo, a mock device, workflow policies, an ONNX adapter, offline signed model updates, automated tests, and native client patches. The patched official desktop client compiles, and synthetic ISO captures are rejected inside its resident and authentication controllers. The patched Android client passes 12 emulator tests, including real RSA fixture verification through its existing SBI parser, native PAD, and one-use acceptance before operator-onboarding storage. The reference camera SBI adds Camera2 action evaluation and exact-JPEG ISO capture, with six passing emulator tests. Its active metadata is included inside the existing signed SBI payload.

**Native integration remains incomplete.** Successful human actions, production device-certificate trust, complete live client UI flows, physical Android/L1 hardware, ISO conformance and physical attack accuracy still need validation. See the [camera SBI integration](docs/CAMERA_SBI_INTEGRATION.md) for the custom extension and test boundaries. See the [requirement-by-requirement evidence matrix](docs/REQUIREMENTS_MATRIX.md) before presenting coverage claims.

## Run locally

Use CPython 3.11. The application binds to `127.0.0.1:4501`. Internet access is needed for initial dependency installation; inference and challenge generation run locally afterward.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python run_mds_service.py
```

On Linux or macOS, use `.venv/bin/python` instead. Linux desktop OpenCV may also need `libgl1` and `libglib2.0-0`.

Open [the local verification console](http://127.0.0.1:4501). The default source is a simulator. Select a scenario and choose **Start verification**. Select **Physical webcam** explicitly for camera use. A disconnected camera produces an error rather than switching silently to simulated success.

The console provides positioning guidance, progress, active prompts, retry messages, device diagnostics, and policy settings. Diagnostic controls apply to the selected workflow. Settings are held in memory and reset when the service restarts.

For the separate OpenCV desktop demo:

```powershell
.\.venv\Scripts\python run_desktop_app.py --mock
```

Run without `--mock` to request a physical webcam. This desktop window is a prototype application, not the official MOSIP Registration Client.

## What a successful result means

- Resident policy can accept a high passive score after temporal checks. Uncertain results require an active action.
- Operator and supervisor policies require active challenges even when passive scores are high.
- PAD runs during active verification. An action cannot override a PAD attack or processing error.
- Face loss or poor quality during an action clears action progress and consumes a retry.
- Preview requests observe the capture output without advancing liveness decisions. Concurrent capture or configuration changes receive HTTP 409.
- The returned payload is an application JPEG. It is not an ISO/IEC 19794-5 interchange record, signed SBI response, registration packet, or proof of identity matching.
- A simulator is always identified as simulated. Mock challenges are never automatically marked complete by the capture service.

## Model contract

The research ONNX adapter supports a declared MiniFASNet V2 profile with checksum verification. The [model card](docs/MODEL_CARD.md) describes preprocessing, provenance, conversion checks, and limitations. The facial landmark model detects actions; it is not itself a trained PAD model.

Set `MOSIP_PAD_MODEL` to a compatible ONNX file to select a different model path. Model updates must be validated before restarting the service with the approved model. Do not drop arbitrary ONNX models into this adapter and assume that input normalization or class ordering will match.

The heuristic backend is a research fallback. Texture, glare, color, and frequency cues do not establish reliable detection of all printed photos, screen replays, masks, or injected video. No independent attack dataset accuracy is claimed.

## Reproduce checks

```powershell
.\.venv\Scripts\python -m pytest -q --junitxml=output/local/test-results.xml
javac --release 8 -d output/local/java src/java_integration/*.java tests/java/NativeCaptureGateTest.java
java -cp output/local/java NativeCaptureGateTest
```

The Java suite checks session binding, challenge counts, rejection, payload binding, and single-use capture acceptance. The Python suite separates control-flow tests with injected scores/actions from detector tests on image fixtures. Neither suite measures real-world attack accuracy. [Validation notes](docs/VALIDATION.md) record the commands and evidence boundaries.

For a private, independently collected test set:

```powershell
.\.venv\Scripts\python scripts/evaluate_dataset.py path/to/test-manifest.jsonl --model assets/models/minifasnet_v2.onnx --output output/local/dataset-evaluation.json
```

The [evaluation protocol](docs/EVALUATION_PROTOCOL.md) defines the manifest, denominators, attack groups, nonresponses, and limits. The older `test_photo_spoof_simulation.py` remains a developer-fixture experiment. Its figures must not be presented as human live-versus-spoof accuracy.

## Build the native checkpoints

The [native integration directory](integrations/native/README.md) contains small patches for exact official Android and desktop source commits, a shared Java ONNX engine, and platform-specific ISO decoding adapters. Apply them to a clean upstream checkout:

```powershell
python scripts/prepare_native_clients.py desktop path/to/registration-client
python scripts/prepare_native_clients.py android path/to/android-registration-client
```

The desktop check runs before resident capture storage and operator/supervisor identity matching. Android checks before resident or operator-onboarding storage. Required active evidence is not connected to these adapters yet, so native operator/supervisor captures reject even when passive scores are high. The [native evidence report](integrations/native/validation.json) distinguishes actual upstream controller execution from live UI and physical attack testing.

## API and local security

See [API documentation](docs/API.md) and the running service's [OpenAPI reference](http://127.0.0.1:4501/docs). Mutating endpoints require a bearer token. The same-origin console receives an ephemeral token from the local service. For a Java or command-line client, set the same explicit `MOSIP_MDS_API_TOKEN` in the service and client environments. Never commit it.

The service checks browser origins and hostnames, disables response caching, and binds to loopback. These controls do not protect against another malicious process running as the same user. Do not expose this research service through a public tunnel.

Audit logs omit image buffers and redact nested sensitive fields. Their hash chain detects edits only when a trusted checkpoint is kept separately. It is not an externally anchored, immutable audit system. Model-update verification supports Ed25519 public keys and an explicit shared-key HMAC mode. The development key requires deliberate opt-in.

## Submission material

- [Requirement matrix](docs/REQUIREMENTS_MATRIX.md), covering all mandatory, good-to-have, and bonus task groups.
- [Technical design](docs/TECHNICAL_DESIGN.md), [sequence diagrams](docs/SEQUENCE_DIAGRAMS.md), and [native integration contract](docs/NATIVE_INTEGRATION.md).
- [Pitch deck](pitch/index.html), a self-contained browser presentation with keyboard navigation.
- [Demo script and submission checklist](docs/DEMO_AND_SUBMISSION.md).
- Official problem statement, evaluation criteria, and submission guidelines PDFs in the repository root.

The rubric assigns 40% to functionality, 40% to deliverable quality, 10% to user experience, and 10% to presentation. The highest-value remaining work is real native integration and representative attack testing. Winning probability cannot be inferred from unit-test counts.

## Third-party assets

See [third-party notices](THIRD_PARTY_NOTICES.md). Original sample images and the original facial landmark asset were inherited from the starting repository. Their individual provenance needs review before redistributing a public submission package. Model code and exported weights retain their upstream license and attribution.
