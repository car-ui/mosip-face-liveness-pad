# Face liveness and presentation attack detection

An offline research prototype for MOSIP Decode 2026, Problem 04. It processes camera frames, checks face quality and passive PAD, and asks for randomly selected facial actions when policy requires them. An attack, engine error, or failed challenge prevents the prototype from returning a captured image.

The repository includes a local browser console, an OpenCV desktop demo, mock device adapters, workflow policies, ONNX inference, offline signed model updates, evaluation tools, and native client patches. The recorded native build milestone passed 17 Android Registration Client instrumentation tests and eight reference camera-SBI tests on an API 34 emulator with cameras disabled. Desktop controller and preview checks also passed. Later working-source changes add signed evidence version 2, configurable camera action policies, a development-only threshold selector, and a portable device capability-contract check. The pinned Desktop source now builds locally with a JDK compatibility override; the retained APKs predate these changes, so Android and SBI still need a fresh platform build.

**Native integration remains incomplete.** The source includes operator/supervisor active-action checkpoints, an Android signed-evidence path, and the pinned Android client now serializes cached resident/operator settings into the standard SBI `customOpts` request. Successful human actions, production device-certificate trust, complete live client UI flows, physical Android/L1 hardware, ISO conformance and physical attack accuracy still need validation. The latest client/SBI source changes have not been rebuilt. See the [camera SBI integration](docs/CAMERA_SBI_INTEGRATION.md) and [requirement matrix](docs/REQUIREMENTS_MATRIX.md) for evidence boundaries.

Current submission readiness, completed prototype work, and remaining partial
acceptance criteria are summarized in the [submission status](docs/SUBMISSION_STATUS.md).

## Run locally

The latest laptop trials exposed apparent live-person rejection and face-count
instability. The [research and rebuild review](docs/RESEARCH_AND_REBUILD.md)
compares existing solutions, records reproducible failures and explains the
YuNet detector change, action preparation phase and optional two-model research
comparison. Physical reliability is not established by the automated tests.

The subsequent [reliability plan and execution record](docs/RELIABILITY_PLAN.md)
documents the bounded video evidence policy, camera settling period, optional
MobileNetV3 comparison and remaining accuracy work. Suspect frames block capture
immediately; terminal PAD rejection now requires sustained evidence. Engine
failures remain immediate errors. Neither a suspect frame nor an inconclusive
session can produce a verified image.

Use CPython 3.11. The application binds to `127.0.0.1:4501`. Internet access is needed for initial dependency installation; inference and challenge generation run locally afterward.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python run_mds_service.py
```

On Linux or macOS, use `.venv/bin/python` instead. Linux desktop OpenCV may also need `libgl1` and `libglib2.0-0`.

Open [the local verification console](http://127.0.0.1:4501). The default source is a simulator. Select a scenario and choose **Start verification**. Select **Physical webcam** explicitly for camera use. A disconnected camera produces an error rather than switching silently to simulated success.

The console provides positioning guidance, progress, active prompts, retry messages, device diagnostics, and policy settings. Diagnostic controls apply to the selected workflow. Settings are in memory by default. Set `MOSIP_PAD_POLICY_FILE` to enable validated offline persistence; see [the policy guide](docs/OFFLINE_POLICY.md).

To create a hash-verified source archive that includes the current working changes and non-ignored new files, run `python scripts/package_release.py --worktree --output output/local/face-liveness-prototype.zip`. The manifest identifies this as a working-tree package and records each included file's SHA-256. A normal run without `--worktree` continues to package the committed tree.

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
.\.venv\Scripts\python scripts/check_device_interoperability.py --output output/local/device-interoperability.json
javac --release 8 -d output/local/java src/java_integration/*.java tests/java/NativeCaptureGateTest.java
java -cp output/local/java NativeCaptureGateTest
```

The Java suite checks session binding, challenge counts, rejection, payload binding, and single-use capture acceptance. The interoperability CLI validates capability consistency across the webcam contract, mock device, and two simulated vendor adapters; it does not establish physical vendor support. The Python suite separates control-flow tests with injected scores/actions from detector tests on image fixtures. Neither suite measures real-world attack accuracy. [Validation notes](docs/VALIDATION.md) record the commands and evidence boundaries.

For private, independently collected data, evaluate the development split and select a threshold first:

```powershell
.\.venv\Scripts\python scripts/evaluate_dataset.py path/to/pad-master.jsonl --split development --model assets/models/minifasnet_v2.onnx --output output/local/pad-development.json
.\.venv\Scripts\python scripts/select_pad_threshold.py output/local/pad-development.json --max-apcer 0.05 --minimum-per-class 20 --output output/local/pad-threshold.json
.\.venv\Scripts\python scripts/evaluate_dataset.py path/to/pad-master.jsonl --split test --model assets/models/minifasnet_v2.onnx --threshold SELECTED_THRESHOLD --output output/local/pad-test.json
```

Replace `SELECTED_THRESHOLD` with the value in `pad-threshold.json`. Both commands use the same private master manifest, which includes development and test rows plus pseudonymous subject and attack-source groups; the loader rejects group overlap and out-of-folder paths. Keep the manifest private because it contains split linkage. The [evaluation protocol](docs/EVALUATION_PROTOCOL.md) defines the manifest, denominators, attack groups, nonresponses, and limits. The older `test_photo_spoof_simulation.py` remains a developer-fixture experiment. Its figures must not be presented as human live-versus-spoof accuracy.

## Build the native checkpoints

The [native integration directory](integrations/native/README.md) contains small patches for exact official Android, camera-SBI, and desktop source commits, a shared Java ONNX engine, and platform-specific ISO decoding adapters. Apply them to a clean upstream checkout:

```powershell
python scripts/prepare_native_clients.py desktop path/to/registration-client
python scripts/prepare_native_clients.py android path/to/android-registration-client
```

The Desktop and Android checkpoints run before capture storage or identity matching. Operator/supervisor paths require active evidence in the current source. The Android client attaches its cached resident/operator policy to face `CaptureRequest.customOpts`; the reference SBI parses the bounded action count, blink/turn pool, timeout and retry policy and passes them to its camera activity. These current Android/SBI edits apply to the pinned upstream commits, but need fresh APK builds and end-to-end verification. The [native evidence report](integrations/native/validation.json) separates retained build evidence from live UI and physical attack testing.

## API and local security

See [API documentation](docs/API.md) and the running service's [OpenAPI reference](http://127.0.0.1:4501/docs). Mutating endpoints require a bearer token. The same-origin console receives an ephemeral token from the local service. For a Java or command-line client, set the same explicit `MOSIP_MDS_API_TOKEN` in the service and client environments. Never commit it.

The service checks browser origins and hostnames, disables response caching, and binds to loopback. These controls do not protect against another malicious process running as the same user. Do not expose this research service through a public tunnel.

Audit logs omit image buffers and redact nested sensitive fields. Their hash chain detects edits only when a trusted checkpoint is kept separately. It is not an externally anchored, immutable audit system. Model-update verification supports Ed25519 public keys and an explicit shared-key HMAC mode. The development key requires deliberate opt-in.

## Submission material

- [Requirement matrix](docs/REQUIREMENTS_MATRIX.md), covering all mandatory, good-to-have, and bonus task groups.
- [Evaluation scorecard](docs/EVALUATION_SCORECARD.md), mapping the official weighted rubric to retained evidence and remaining gaps.
- [Technical design](docs/TECHNICAL_DESIGN.md), [sequence diagrams](docs/SEQUENCE_DIAGRAMS.md), and [native integration contract](docs/NATIVE_INTEGRATION.md).
- [Pitch deck](pitch/index.html), a self-contained browser presentation with keyboard navigation.
- [Demo script and submission checklist](docs/DEMO_AND_SUBMISSION.md).
- [Native usability and accessibility study protocol](docs/USABILITY_STUDY.md); participant results are still required.
- [Remaining acceptance work and time estimate](docs/REMAINING_WORK_PLAN.md).
- Official problem statement, evaluation criteria, and submission guidelines PDFs in the repository root.

The rubric assigns 40% to functionality, 40% to deliverable quality, 10% to user experience, and 10% to presentation. Native source checkpoints and emulator evidence are present; the highest-value remaining work is live client/device validation and representative attack testing. See the [rubric evidence map](docs/EVALUATION_SCORECARD.md). Winning probability cannot be inferred from unit-test counts.

## Third-party assets

See [third-party notices](THIRD_PARTY_NOTICES.md). Original sample images and the original facial landmark asset were inherited from the starting repository. Their individual provenance needs review before redistributing a public submission package. Model code and exported weights retain their upstream license and attribution.
