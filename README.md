# MOSIP Face Liveness Detection and Presentation Attack Detection (Decode 2026 - Problem 04)

[![Tests: 64 Passed](https://img.shields.io/badge/Tests-64%20Passed-brightgreen.svg)]()
[![Platform: Offline-First](https://img.shields.io/badge/Architecture-100%25%20Offline-blue.svg)]()
[![Standard: ISO/IEC 30107 & 19794-5 Aligned](https://img.shields.io/badge/Standards-ISO%2FIEC%2030107%20%7C%2019794--5-orange.svg)]()
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![Java: 21 Ready](https://img.shields.io/badge/Java-21%20Ready-red.svg)]()

A robust, enterprise-grade, hardware-agnostic solution for **Face Liveness Detection** and **Presentation Attack Detection (PAD)** designed for the **MOSIP (Modular Open Source Identity Platform)** Desktop and Android Registration Clients.

> **Design Philosophy & Academic Integrity**: Built for production readiness and academic rigor. The architecture modularly isolates deep-learning ONNX model inference from deterministic multi-cue physical heuristics. The system operates 100% offline, logs zero raw biometrics, and explicitly reports whether decisions are driven by `MODEL` or `HEURISTIC` engines. All experimental numbers are clearly presented as local developer test benchmarks, with zero unsubstantiated laboratory certification claims.

---

## 🚀 Key Architectural Highlights

1. **Lightweight Resident Enrollment Experience & Strict Data Privacy**:
   * **Predictable Resident ID Tracking**: Generates or accepts standard `RES-XXXXX` tokens via `ResidentEnrollmentManager`.
   * **Live 3-Step Dynamic HUD Checklist**: Guides residents intuitively through `1. Position Face` $\rightarrow$ `2. Liveness Check` $\rightarrow$ `3. Enrolled`.
   * **Strict Data Privacy**: Verifies liveness purely in ephemeral memory; enrollment records and structured audit logs store strictly zero raw facial images or pixel arrays, retaining only a cryptographic SHA-256 hash of the captured biometric frame payload for token verification (not a feature template vector).

2. **Modular Passive PAD Engine (ISO/IEC 30107 Aligned)**:
   * **Pluggable ONNX Inference Interface**: Allows dropping in pre-trained ONNX liveness models (`.onnx`) with zero code modifications; safe fallback in `ONNX_ONLY` mode when models are missing.
   * **Deterministic Multi-Cue Heuristic Fallback**: Analyzes 2D Discrete Fourier Transform (DFT) high-frequency moiré harmonics, YCrCb/HSV chrominance distribution, specular glass/screen reflection glare, and Sobel micro-texture gradient depth.
   * **Calibrated Confidence**: Computes dispersion across cues and exposes a 4-way verdict: `BONA_FIDE_LIVE`, `UNCERTAIN`, `PRESENTATION_ATTACK`, or `PROCESSING_ERROR`.
   * **Operational Mode Transparency**: Never fakes deep-learning inference; explicitly signals `operational_mode` (`MODEL` or `HEURISTIC`) and model provenance with millisecond runtime timers in results and audit logs.

3. **Clean Hybrid Decision Logic**:
   * `BONA_FIDE_LIVE` $\rightarrow$ Proceed to `CAPTURE_SUCCESS` directly if temporal stability holds.
   * `UNCERTAIN` $\rightarrow$ Escalate to interactive `ACTIVE_CHALLENGE` to resolve ambiguity.
   * `PRESENTATION_ATTACK` $\rightarrow$ Immediate rejection (`ATTACK_REJECTED`); definite attacks are blocked without escalating to active challenges.
   * `PROCESSING_ERROR` $\rightarrow$ Non-punitive user guidance and retry cooldown.

4. **Temporal Consistency Window (`TemporalLivenessBuffer`)**:
   * Evaluates rolling weighted confidence, min/max score bounds, variance, and micro-motion trajectory across a configurable sliding frame window (default: 15–25 frames).
   * Prevents single aberrant frames from triggering false accepts or false rejections.
   * Detects completely frozen/static presentation attacks (zero micro-motion variance).

5. **Dynamic Unpredictable Active Challenges**:
   * **Cryptographically Unpredictable**: Dynamic selection using `secrets.SystemRandom()` with non-repeating memory pool.
   * **Temporal State Machines**:
     * **Blink**: Strict three-phase `OPEN -> CLOSED -> OPEN` Eye Aspect Ratio (EAR) sequence with duration validation.
     * **Smile**: Baseline-neutral differential calculation ($\Delta \ge 0.15$) held over $N \ge 3$ consecutive frames.
     * **Head Turn**: Temporal yaw progression (`CENTER -> TURN -> CENTER`) using Perspective-n-Point (SolvePnP) 3D head pose estimation.
   * **Anti-Replay Protection**: Rejects static photos and non-responsive replays.

6. **L0/L1 Multi-Vendor Device Abstraction**:
   * Clear inheritance hierarchy: `BaseBiometricDevice` $\rightarrow$ `L0Device` (`WebcamCaptureDevice`, `MockL0Device`) & `L1Device` (`VendorL1Adapter`).
   * **Capability Discovery (`DeviceCapabilities`)**: Structured query of supported capture modes, resolutions, security level (`L0_BASIC`, `L0_SIMULATED`, `L1_SIMULATED`), and hardware capabilities.
   * **Comprehensive Scenario Simulator (`MockL0Device`)**: Reproducibly simulates 10 critical operational conditions for automated CI/CD:
     * `BONA_FIDE_LIVE`, `STATIC_PHOTO_ATTACK`, `SCREEN_REPLAY_ATTACK`, `NO_FACE`, `MULTIPLE_FACES`, `POOR_LIGHTING_DARK`, `POOR_LIGHTING_BRIGHT`, `POOR_LIGHTING_UNEVEN`, `BLURRY_FRAME`, `DEVICE_DISCONNECT`, `INVALID_FRAME`.
     * Supports programmable scripted actions (`BLINK`, `SMILE`, `TURN_LEFT`, `TURN_RIGHT`).

7. **Model Versioning & Hardware Acceleration**:
   * `ModelMetadata`: Every PAD decision is traceable to backend name, model version, SHA-256 cryptographic hash, input dimensions, inference provider, and threshold.
   * Automatic execution provider discovery via `onnxruntime.get_available_providers()` prioritizing CUDA, DirectML, OpenVINO, and CPU.

8. **Secure Offline Model Updates (`SecureModelUpdateManager`)**:
   * Model update package verification: SHA-256 integrity, HMAC-SHA256 signature verification, strict semantic version progression (anti-downgrade), atomic POSIX/Windows filesystem replacement, and automatic rollback on failure.
   * **Key Management Disclosure**: The built-in key (`DEFAULT_DEV_TEST_KEY = b"DEV_INSECURE_TEST_KEY_FOR_LOCAL_EVALUATION_ONLY"`) is strictly a local developer test fixture. Production deployments must utilize asymmetric PKI (e.g. RSA-4096 / ECDSA P-384) with keys injected via the `MOSIP_MODEL_SIGNING_KEY` environment variable or hardware KMS/HSM modules.

9. **Multi-Workflow Policy Engine**:
   * **Resident Registration**: Low-friction passive evaluation ($0.80$ threshold) with automatic active challenge escalation on uncertainty.
   * **Operator Authentication**: High-security threshold ($0.88$) with 2 mandatory challenges and tight timeouts.
   * **Supervisor Authentication**: Maximum security ($0.92$) requiring 2 sequential multi-challenges for biometric override.

10. **MOSIP Device Service (MDS) REST & MJPEG Service**:
    * Compliant with MOSIP Device Service architectural patterns on `http://127.0.0.1:4501/`.
    * Standard endpoints: `/info` (device discovery), `/stream` (live MJPEG overlay), `/capture` (returns ISO/IEC 19794-5-aligned image representation and cryptographic token hash), `/configure` (runtime threshold updates), and `/switch-device`.
    * Configurable CORS protection defaulting to loopback interfaces with full Pydantic validation.

11. **Security & Privacy Protections**:
    * **Safe Error Taxonomy**: Clear separation between internal diagnostics (`SCREEN_REPLAY_DETECTED`, `MOIRE_HARMONICS_DETECTED`) and safe user-facing instructions (`"Face verification could not be completed. Please position your face and try again."`) to prevent reverse-engineering of PAD thresholds.
    * **No Persistent Raw Biometric Storage**: Processing occurs solely in ephemeral RAM. While the `/capture` endpoint temporarily returns an in-memory Base64-encoded image payload to the authenticated client, raw facial images are strictly never persisted to disk, local databases, or audit logs.
    * **100% Offline Execution**: Zero external telemetry, cloud APIs, or outbound connections.

---

## 📊 Feature Coverage Matrix (Official Problem 04 Requirements)

| Requirement | Category | Status | Implementation File | Demo / Test Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Physical L0 Webcam Capture** | Mandatory | ✅ **REAL** | [`src/devices/webcam_device.py`](src/devices/webcam_device.py) | `python run_desktop_app.py` |
| **L1 Device Integration** | Mandatory | 🟡 **SIMULATED** | [`src/devices/base.py`](src/devices/base.py) (`VendorL1Adapter`) | `pytest tests/test_mock_device.py -k test_vendor_l1` |
| **ISO 19794-5 Quality Assessor** | Mandatory | ✅ **REAL** | [`src/core/face_detector.py`](src/core/face_detector.py) | `pytest tests/test_face_detector.py` |
| **Passive Liveness Engine** | Mandatory | ✅ **REAL** | [`src/core/passive_pad.py`](src/core/passive_pad.py) | `pytest tests/test_passive_pad.py` |
| **Presentation Attack Detection** | Mandatory | ✅ **REAL** | [`src/core/passive_pad.py`](src/core/passive_pad.py) | `python run_desktop_app.py --demo 3` |
| **Active Liveness Challenges** | Mandatory | ✅ **REAL** | [`src/core/active_liveness.py`](src/core/active_liveness.py) | `python run_desktop_app.py --demo 2` |
| **Resident Registration Workflow** | Mandatory | ✅ **REAL** | [`src/core/enrollment.py`](src/core/enrollment.py) | `python run_desktop_app.py --resident-id RES-00123` |
| **Operator Authentication** | Mandatory | ✅ **REAL** | [`src/core/pipeline.py`](src/core/pipeline.py) | `python run_desktop_app.py --workflow OPERATOR_AUTHENTICATION` |
| **Supervisor Authentication** | Mandatory | ✅ **REAL** | [`src/core/pipeline.py`](src/core/pipeline.py) | `python run_desktop_app.py --workflow SUPERVISOR_AUTHENTICATION` |
| **Configuration & Policies** | Mandatory | ✅ **REAL** | [`src/core/config.py`](src/core/config.py) | `pytest tests/test_workflows.py` |
| **Offline Operation** | Mandatory | ✅ **REAL** | Core pipeline (zero external network calls) | `python -m pytest -v` (100% offline) |
| **Error Handling & Taxonomy** | Mandatory | ✅ **REAL** | [`src/core/errors.py`](src/core/errors.py) | `python run_desktop_app.py --demo 8` |
| **Desktop UI / UX** | Mandatory | ✅ **REAL** | [`src/ui/desktop_client.py`](src/ui/desktop_client.py) | `python run_desktop_app.py --demo 1` |
| **Multiple Facial Actions (6 Actions)** | Good-to-Have | ✅ **REAL** | [`src/core/active_liveness.py`](src/core/active_liveness.py) | `pytest tests/test_active_liveness.py` |
| **Configurable Challenge Pools** | Good-to-Have | ✅ **REAL** | [`src/core/challenge_manager.py`](src/core/challenge_manager.py) | `pytest tests/test_active_liveness.py -k test_challenge_manager` |
| **Workflow Policy Switching** | Good-to-Have | ✅ **REAL** | [`src/core/config.py`](src/core/config.py) | Press `1`, `2`, `3` in Desktop Client |
| **Configurable User Guidance** | Good-to-Have | ✅ **REAL** | [`src/core/errors.py`](src/core/errors.py) | Decoupled safe end-user messages in Action Card |
| **Diagnostic Mode HUD** | Good-to-Have | ✅ **REAL** | [`src/ui/desktop_client.py`](src/ui/desktop_client.py) | `python run_desktop_app.py --mock --diagnostic` |
| **Multi-Vendor Capability Discovery** | Good-to-Have | ✅ **REAL** | [`src/devices/base.py`](src/devices/base.py) (`DeviceCapabilities`) | `curl -s http://127.0.0.1:4501/info` |
| **Anonymized Operational Metrics** | Good-to-Have | ✅ **REAL** | [`src/core/audit_logger.py`](src/core/audit_logger.py) | Inspect stdout structured JSON audit events |
| **Liveness Performance Metrics** | Good-to-Have | ✅ **REAL** | [`test_photo_spoof_simulation.py`](test_photo_spoof_simulation.py) | `python test_photo_spoof_simulation.py` |
| **Mock L0/L1 Simulator (11 Scenarios)** | Bonus | ✅ **REAL** | [`src/devices/mock_l0_device.py`](src/devices/mock_l0_device.py) | `pytest tests/test_mock_device.py` |
| **Automated PAD Attack Benchmarks** | Bonus | ✅ **REAL** | [`test_photo_spoof_simulation.py`](test_photo_spoof_simulation.py) | `python test_photo_spoof_simulation.py` |
| **Interoperability Framework (MDS API)**| Bonus | ✅ **REAL** | [`src/mds/mds_server.py`](src/mds/mds_server.py) | `python run_mds_service.py` & `pytest tests/test_mds.py` |
| **Java 21 Client Adapter** | Bonus | ✅ **REAL** | [`src/java_integration/MosipLivenessDeviceService.java`](src/java_integration/MosipLivenessDeviceService.java) | `javac src/java_integration/MosipLivenessDeviceService.java` |
| **Model Version & Provenance** | Bonus | ✅ **REAL** | [`src/core/model_updater.py`](src/core/model_updater.py) (`ModelMetadata`) | Provenance hash attached to all audit/API outputs |
| **Secure Offline Model Updates** | Bonus | ✅ **REAL** | [`src/core/model_updater.py`](src/core/model_updater.py) | `pytest tests/test_model_updater.py` |
| **Hardware Acceleration Discovery** | Bonus | ✅ **REAL** | [`src/core/passive_pad.py`](src/core/passive_pad.py) | DirectML, CUDA, OpenVINO provider priority lookup |
| **Deep Learning ONNX Weights** | Bonus | 🔵 **ARCH-READY**| [`src/core/passive_pad.py`](src/core/passive_pad.py) (`ONNXModelPADBackend`) | Drops into `assets/models/` without code change |
| **Low-Resource Android Strategy** | Bonus | 🔵 **ARCH-READY**| Documented adaptive subsampling (10 Hz DFT) & NNAPI | [`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md#L183-L195) |
| **Formal ISO Laboratory Certification**| Standard | ❌ **NOT CLAIMED**| Alignment with ISO/IEC 30107 & 19794-5 design principles | Formal testing requires accredited third-party lab |

---

## 📁 Repository Structure

```
livliness/
├── docs/
│   ├── TECHNICAL_DESIGN.md        # Comprehensive architecture, security, & ISO alignment
│   └── SEQUENCE_DIAGRAMS.md       # Mermaid sequence diagrams for all flows
├── src/
│   ├── core/
│   │   ├── config.py              # Centralized policies, thresholds, and PADMode enums
│   │   ├── errors.py              # BiometricErrorCode taxonomy & safe user message mapping
│   │   ├── audit_logger.py        # Privacy-preserving structured JSON audit logger
│   │   ├── enrollment.py          # Lightweight ResidentEnrollmentManager & privacy-preserving records
│   │   ├── temporal_buffer.py     # Sliding temporal frame buffer & micro-motion analysis
│   │   ├── face_detector.py       # ISO 19794-5 quality, blur, lighting, centering checks
│   │   ├── passive_pad.py         # Modular ONNX & multi-cue physical heuristic PAD engine with ModelMetadata
│   │   ├── active_liveness.py     # Temporal EAR, MAR, and SolvePnP 3D pose state machines
│   │   ├── challenge_manager.py   # Cryptographic challenge selection & timeout tracker
│   │   ├── model_updater.py       # Secure offline model update manager (SHA-256, HMAC, atomic swap)
│   │   └── pipeline.py            # Master hybrid state machine orchestrator (14 states)
│   ├── devices/
│   │   ├── base.py                # BaseBiometricDevice, L0Device, L1Device, VendorL1Adapter, DeviceCapabilities
│   │   ├── webcam_device.py       # Physical L0 Webcam adapter
│   │   └── mock_l0_device.py      # 10-scenario deterministic mock biometric device
│   ├── mds/
│   │   └── mds_server.py          # MOSIP Device Service REST & MJPEG server
│   ├── ui/
│   │   └── desktop_client.py      # Desktop Client UI with cinematic HUD & Evaluator Diagnostic Mode
│   └── java_integration/
│       └── MosipLivenessDeviceService.java # Java 21 MOSIP Client Adapter
├── tests/
│   ├── test_face_detector.py      # 8 ISO 19794-5 quality assessment unit tests
│   ├── test_passive_pad.py        # 6 Passive PAD cue & ONNX fallback tests
│   ├── test_active_liveness.py    # 7 Temporal EAR, Smile, Pose & timeout tests
│   ├── test_mock_device.py        # 7 Lifecycle, scenario generation, capabilities & L1 adapter tests
│   ├── test_pipeline.py           # 9 Master state machine, attack rejection, and retry exhaustion tests
│   ├── test_temporal.py          # 4 Sliding window, micro-motion, and stability tests
│   ├── test_model_updater.py      # 4 Integrity, signature, anti-downgrade, and rollback tests
│   ├── test_workflows.py          # 4 Resident, Operator, Supervisor policy tests
│   ├── test_mds.py                # 10 MDS REST endpoint, stream & capture regression tests
│   └── test_enrollment.py         # 5 Lightweight resident enrollment & privacy tests
├── run_desktop_app.py             # Desktop Client UI launcher with --demo, --diagnostic, and --resident-id flags
├── run_mds_service.py             # MOSIP Device Service (MDS) launcher
├── test_photo_spoof_simulation.py # Multi-vector presentation attack evaluation benchmark
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
* Python 3.11+ (Windows / Linux / macOS)
* Webcam (optional; full testing and demonstration can run via the Mock Simulator)

### 2. Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Automated Test Suite (64 Tests)
Execute the complete unit and integration test suite:
```bash
python -m pytest -v
```
*All 64 tests pass 100%, covering face quality assessment, passive heuristics, temporal active challenges, device abstractions, lightweight resident enrollment, privacy guarantees, offline model updates, workflow policies, and MDS REST endpoints.*

---

## 🎬 Live Evaluator Demo Modes

The desktop client provides dedicated flags to demonstrate all 10 core evaluator scenarios instantly:

```powershell
# Lightweight Resident Registration (With custom or auto-generated Resident ID)
.\venv\Scripts\python run_desktop_app.py --resident-id RES-00123

# Demo 1: Bona Fide Live Subject (High confidence passive pass)
.\venv\Scripts\python run_desktop_app.py --demo 1

# Demo 2: Uncertain Passive -> Dynamic Active Challenge Escalation
.\venv\Scripts\python run_desktop_app.py --demo 2

# Demo 3: Printed Photo Presentation Attack (Heuristic PAD Rejection)
.\venv\Scripts\python run_desktop_app.py --demo 3

# Demo 4: Smartphone Screen Replay Attack (Moiré grid + specular glare rejection)
.\venv\Scripts\python run_desktop_app.py --demo 4

# Demo 5: Static Photo against Active Challenge (Times out & fails)
.\venv\Scripts\python run_desktop_app.py --demo 5

# Demo 6: Multiple Faces in Frame (ISO 19794-5 single-subject enforcement)
.\venv\Scripts\python run_desktop_app.py --demo 6

# Demo 7: Poor Lighting Environment (Underexposed dark rejection & user guidance)
.\venv\Scripts\python run_desktop_app.py --demo 7

# Demo 8: Device Disconnect (Mid-stream hardware failure handling)
.\venv\Scripts\python run_desktop_app.py --demo 8

# Demo 9: Blurry Frame & Defocus (Laplacian sharpness quality rejection)
.\venv\Scripts\python run_desktop_app.py --demo 9

# Demo 10: No Face Present in Frame (Positioning guidance prompt)
.\venv\Scripts\python run_desktop_app.py --demo 10

# Launch directly in Evaluator Diagnostic Mode (Displays raw FPS, EAR, MAR, Yaw, PAD score HUD):
.\venv\Scripts\python run_desktop_app.py --mock --diagnostic
```

*Interactive Desktop Client Hotkeys*:
* `n`: Generate a new **Resident ID** (`RES-XXXXX`) and start a fresh enrollment session.
* `r`: Reset current session and re-evaluate.
* `d`: Toggle **Evaluator Diagnostic Mode** on/off (shows FPS, EAR, MAR, Yaw, and score breakdown).
* `1`, `2`, `3`: Switch workflow policies on the fly (`1`: Resident, `2`: Operator, `3`: Supervisor).
* `q` or `Esc`: Gracefully quit.

---

## 🧭 Step-by-Step Evaluator Walkthrough (Recommended Flow)

Follow this 18-step sequential checklist to evaluate the complete subsystem end-to-end:

1. **Start MDS Service**: Run `.\venv\Scripts\python run_mds_service.py` (daemon binds to port 4501).
2. **Inspect Web Console**: Open browser at `http://127.0.0.1:4501/`. Verify live video stream renders with centering oval.
3. **Device Capability Discovery**: Query `GET http://127.0.0.1:4501/info` and inspect `DeviceCapabilities` JSON (security level, vendor, resolutions).
4. **Resident Biometric Enrollment (Live Mock)**: On web console or via CLI (`run_desktop_app.py --demo 1`), select Resident Registration (`RES-00123`).
5. **Passive PAD Evaluation**: Observe passive multi-cue analysis evaluating quality, frequency harmonics, and chrominance in real-time.
6. **Enrollment Completion**: Capture completes, displays `RES-00123 [COMPLETED]` with SHA-256 token hash (zero raw facial image persistence).
7. **Static Photo Attack Simulation**: Switch device to Photo Spoof (`run_desktop_app.py --demo 3` or click web button).
8. **Verify PAD Rejection**: Observe immediate `ATTACK_REJECTED` verdict without escalating to active challenges.
9. **Screen Replay Attack Simulation**: Switch to Screen Replay (`run_desktop_app.py --demo 4`).
10. **Verify Screen Glare & Moiré Rejection**: Observe high-frequency 2D DFT harmonics triggering `ATTACK_REJECTED`.
11. **Operator Authentication Workflow**: Press `2` (or select Operator Auth). Note elevated passive threshold (0.88) and mandatory active challenge.
12. **Supervisor Authentication Workflow**: Press `3` (or select Supervisor Auth). Note maximum security threshold (0.92) requiring multi-challenge verification.
13. **Active Challenge Execution**: Press `n` or run `--demo 2` (dynamic escalation to challenge) or `--demo 5` (static photo failing challenge) to observe EAR blink sequence or baseline-neutral smile hold.
14. **Toggle Diagnostic Mode**: Press `d` to inspect live FPS, EAR, MAR, 3D Pose Yaw/Pitch, and active PAD engine (`Heuristic PAD — Active` or `ONNX`).
15. **Vendor L1 Adapter Demonstration**: Click "Vendor L1 — Simulated Adapter" or query `/info` to see `securityLevel: L1_SIMULATED` with HMAC-SHA256 biometric signing.
16. **Offline Model Updater**: Run model updater verification test (`pytest tests/test_model_updater.py`) to observe SHA-256 check, HMAC verification, anti-downgrade check, and rollback.
17. **Run Attack Benchmark**: Run `python test_photo_spoof_simulation.py` to inspect APCER/BPCER developer benchmark metrics.
18. **Verify Test Suite**: Run `python -m pytest -v` to confirm all 64 unit and integration tests pass 100%.

---

## 🌐 MOSIP Device Service (MDS) Execution

Launch the MDS service locally on port 4501:
```powershell
.\venv\Scripts\python run_mds_service.py
```

Access the integrated endpoints:
* **Interactive Console**: [http://127.0.0.1:4501/](http://127.0.0.1:4501/)
* **Device Discovery**: `GET http://127.0.0.1:4501/info`
* **Real-time Video Stream**: `GET http://127.0.0.1:4501/stream`
* **Biometric Capture Trigger**: `POST http://127.0.0.1:4501/capture`
* **Dynamic Configuration**: `POST http://127.0.0.1:4501/configure`
* **Device Simulator Switching**: `POST http://127.0.0.1:4501/switch-device`

---

## 🔬 Multi-Vector Attack Evaluation Benchmark

Run the automated Presentation Attack Detection benchmark:
```powershell
.\venv\Scripts\python test_photo_spoof_simulation.py
```

This benchmark feeds print photos, smartphone screen replays with moiré/glare artifacts, 2D displays, and bona fide samples through the temporal pipeline and reports:
* **Sample Counts**: Number of presentation attack samples and bona fide live samples tested.
* **Attack Presentation Classification Error Rate (APCER)**: Proportion of presentation attacks erroneously accepted.
* **Bona Fide Presentation Classification Error Rate (BPCER)**: Proportion of bona fide presentations erroneously rejected.
* **Pipeline Latency & Frame Rate (FPS)**.

> *Disclaimer*: These metrics reflect local experimental testing against developer test fixtures and do not constitute formal laboratory certification under ISO/IEC 19792 or 30107.

---

## ☕ Java 21 Client Adapter

With the MDS server running on port 4501, execute the Java 21 adapter:
```powershell
javac -d bin src/java_integration/MosipLivenessDeviceService.java
java -cp bin io.mosip.registration.liveness.MosipLivenessDeviceService
```
The adapter connects via HTTP/JSON to the MDS server, initiates biometric capture for the specified workflow, verifies the response payload, and decodes the ISO 19794-5 image token.
