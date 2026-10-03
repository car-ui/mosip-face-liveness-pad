# MOSIP Face Liveness Detection and Presentation Attack Detection (Decode 2026 - Problem 04)

[![Tests: 54 Passed](https://img.shields.io/badge/Tests-54%20Passed-brightgreen.svg)]()
[![Platform: Offline-First](https://img.shields.io/badge/Architecture-100%25%20Offline-blue.svg)]()
[![Standard: ISO/IEC 30107 & 19794-5 Aligned](https://img.shields.io/badge/Standards-ISO%2FIEC%2030107%20%7C%2019794--5-orange.svg)]()
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![Java: 21 Ready](https://img.shields.io/badge/Java-21%20Ready-red.svg)]()

A robust, enterprise-grade, hardware-agnostic solution for **Face Liveness Detection** and **Presentation Attack Detection (PAD)** designed for the **MOSIP (Modular Open Source Identity Platform)** Desktop and Android Registration Clients.

> **Design Philosophy & Academic Integrity**: Built for production readiness and academic rigor. The architecture modularly isolates deep-learning ONNX model inference from deterministic multi-cue physical heuristics. The system operates 100% offline, logs zero raw biometrics, and explicitly reports whether decisions are driven by `MODEL` or `HEURISTIC` engines. All experimental numbers are clearly presented as local developer test benchmarks, with zero unsubstantiated laboratory certification claims.

---

## 🚀 Key Architectural Highlights

1. **Modular Passive PAD Engine (ISO/IEC 30107 Aligned)**:
   * **Pluggable ONNX Inference Interface**: Allows dropping in pre-trained ONNX liveness models (`.onnx`) with zero code modifications.
   * **Deterministic Multi-Cue Heuristic Fallback**: Analyzes 2D Discrete Fourier Transform (DFT) high-frequency moiré harmonics, YCrCb/HSV chrominance distribution, specular glass/screen reflection glare, and Sobel micro-texture gradient depth.
   * **Calibrated Confidence**: Computes dispersion across cues and exposes a 4-way verdict: `BONA_FIDE_LIVE`, `UNCERTAIN`, `PRESENTATION_ATTACK`, or `PROCESSING_ERROR`.
   * **Operational Mode Transparency**: Never fakes deep-learning inference; explicitly signals `operational_mode` (`MODEL` or `HEURISTIC`) in results and audit logs.

2. **Clean Hybrid Decision Logic**:
   * `BONA_FIDE_LIVE` $\rightarrow$ Proceed to `CAPTURE_SUCCESS` directly if temporal stability holds.
   * `UNCERTAIN` $\rightarrow$ Escalate to interactive `ACTIVE_CHALLENGE` to resolve ambiguity.
   * `PRESENTATION_ATTACK` $\rightarrow$ Immediate rejection (`ATTACK_REJECTED`); definite attacks are blocked without escalating to active challenges.
   * `PROCESSING_ERROR` $\rightarrow$ Non-punitive user guidance and retry cooldown.

3. **Temporal Consistency Window (`TemporalLivenessBuffer`)**:
   * Evaluates rolling weighted confidence, min/max score bounds, variance, and micro-motion trajectory across a configurable sliding frame window (default: 15–25 frames).
   * Prevents single aberrant frames from triggering false accepts or false rejections.
   * Detects completely frozen/static presentation attacks (zero micro-motion variance).

4. **Dynamic Unpredictable Active Challenges**:
   * **Cryptographically Unpredictable**: Dynamic selection using `secrets.SystemRandom()` with non-repeating memory pool.
   * **Temporal State Machines**:
     * **Blink**: Strict three-phase `OPEN -> CLOSED -> OPEN` Eye Aspect Ratio (EAR) sequence with duration validation.
     * **Smile**: Baseline-neutral differential calculation ($\Delta \ge 0.15$) held over $N \ge 3$ consecutive frames.
     * **Head Turn**: Temporal yaw progression (`CENTER -> TURN -> CENTER`) using Perspective-n-Point (SolvePnP) 3D head pose estimation.
   * **Anti-Replay Protection**: Rejects static photos and non-responsive replays.

5. **L0/L1 Multi-Vendor Device Abstraction**:
   * Clear inheritance hierarchy: `BaseBiometricDevice` $\rightarrow$ `L0Device` (`WebcamCaptureDevice`, `MockL0Device`) & `L1Device` (`VendorL1Adapter`).
   * **Capability Discovery (`DeviceCapabilities`)**: Structured query of supported capture modes, resolutions, security level, and hardware capabilities.
   * **Comprehensive Scenario Simulator (`MockL0Device`)**: Reproducibly simulates 10 critical operational conditions for automated CI/CD:
     * `BONA_FIDE_LIVE`, `STATIC_PHOTO_ATTACK`, `SCREEN_REPLAY_ATTACK`, `NO_FACE`, `MULTIPLE_FACES`, `POOR_LIGHTING_DARK`, `POOR_LIGHTING_BRIGHT`, `POOR_LIGHTING_UNEVEN`, `BLURRY_FRAME`, `DEVICE_DISCONNECT`, `INVALID_FRAME`.
     * Supports programmable scripted actions (`BLINK`, `SMILE`, `TURN_LEFT`, `TURN_RIGHT`).

6. **Model Versioning & Hardware Acceleration**:
   * `ModelMetadata`: Every PAD decision is traceable to backend name, model version, SHA-256 cryptographic hash, input dimensions, inference provider, and threshold.
   * Automatic execution provider discovery via `onnxruntime.get_available_providers()` prioritizing CUDA, DirectML, OpenVINO, and CPU.

7. **Secure Offline Model Updates (`SecureModelUpdateManager`)**:
   * Model update package verification: SHA-256 integrity, HMAC-SHA256 signature verification, strict semantic version progression (anti-downgrade), atomic POSIX/Windows filesystem replacement, and automatic rollback on failure.

8. **Multi-Workflow Policy Engine**:
   * **Resident Registration**: Low-friction passive evaluation ($0.80$ threshold) with automatic active challenge escalation on uncertainty.
   * **Operator Authentication**: High-security threshold ($0.88$) with 1 mandatory challenge and tight timeouts.
   * **Supervisor Authentication**: Maximum security ($0.92$) requiring 2 sequential multi-challenges for biometric override.

9. **MOSIP Device Service (MDS) REST & MJPEG Service**:
   * Compliant with MOSIP Device Service architectural patterns on `http://127.0.0.1:4501/`.
   * Standard endpoints: `/info` (device discovery), `/stream` (live MJPEG overlay), `/capture` (biometric token generation with ISO 19794-5 packaging), `/configure` (runtime threshold updates), and `/switch-device`.
   * Full Pydantic request/response schema validation with standard HTTP error codes (`400`, `408`, `503`).

10. **Security & Privacy Protections**:
    * **Safe Error Taxonomy**: Clear separation between internal diagnostics (`SCREEN_REPLAY_DETECTED`, `MOIRE_HARMONICS_DETECTED`) and safe user-facing instructions (`"Face verification could not be completed. Please position your face and try again."`) to prevent reverse-engineering of PAD thresholds.
    * **Zero Raw Biometric Logging**: Structured JSON audit logger (`BiometricAuditLogger`) logs UUID session tokens, timestamps, and detection metrics, while strictly omitting raw facial imagery.
    * **100% Offline Execution**: Zero external telemetry, cloud APIs, or outbound connections.

---

## 📊 Implementation Status Matrix

| Component / Deliverable | Status | Nature of Implementation |
| :--- | :--- | :--- |
| **Physical L0 Webcam Capture** | **REAL** | OpenCV / UVC hardware camera stream capture with DirectShow acceleration |
| **ISO 19794-5 Quality Assessor** | **REAL** | Laplacian variance blur filter, mean luminance check, centering oval, single-face validation |
| **Multi-Cue Heuristic PAD** | **REAL** | 2D Discrete Fourier Transform moiré detection, YCrCb chromatic variance, specular glare, Sobel texture |
| **Active Challenge Geometry** | **REAL** | MediaPipe 478 landmarks, temporal EAR three-phase blink, neutral baseline smile hold, SolvePnP 3D pose |
| **Temporal Consistency Buffer** | **REAL** | Rolling sliding frame buffer, weighted confidence, stability metrics, micro-motion jitter |
| **Privacy Audit Logging** | **REAL** | Zero raw image persistence, structured JSON events with UUIDs and ISO 8601 timestamps |
| **Safe Error Taxonomy** | **REAL** | Internal diagnostic codes mapped to user-facing safe guidance |
| **MOSIP Device Service (MDS)** | **REAL** | FastAPI REST & MJPEG daemon on port 4501 with Pydantic validation & standard HTTP error codes |
| **Secure Offline Model Updater** | **REAL** | SHA-256 integrity, HMAC signature verification, semantic anti-downgrade, atomic swap, rollback |
| **Model Version & Provider Tracking** | **REAL** | `ModelMetadata` provenance, SHA-256 hash tracking, `onnxruntime` provider discovery |
| **Desktop Client UI** | **REAL** | OpenCV HUD, Apple-style FaceID oval, cinematic laser scanner, Evaluator Diagnostic Mode |
| **Java 21 Client Adapter** | **REAL** | HTTP/JSON MOSIP desktop client adapter connecting to MDS on port 4501 |
| **Deterministic Mock L0 Device** | **SIMULATED** | 10 reproducible operational scenarios + programmable scripted actions for CI/CD |
| **Vendor L1 Device Adapter** | **ARCHITECTURE-READY** | Concrete `VendorL1Adapter` demonstrating cryptographic biometric token signing & tamper alarms for vendor SDKs |
| **Deep Learning ONNX Weights** | **ARCHITECTURE-READY** | `ONNXModelPADBackend` implemented; loads standard `.onnx` models when dropped into path |
| **Low-Resource Android Optimization** | **ARCHITECTURE-READY** | Documented adaptive frame subsampling & NNAPI quantization strategy; no native Android build in repo |
| **Formal ISO Certification** | **NOT IMPLEMENTED** | System is engineered in alignment with ISO/IEC 30107 & 19794-5; formal certification requires accredited lab |

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
│   ├── test_passive_pad.py        # 5 Passive PAD cue & ONNX fallback tests
│   ├── test_active_liveness.py    # 7 Temporal EAR, Smile, Pose & timeout tests
│   ├── test_mock_device.py        # 7 Lifecycle, scenario generation, capabilities & L1 adapter tests
│   ├── test_pipeline.py           # 9 Master state machine, attack rejection, and retry exhaustion tests
│   ├── test_temporal.py          # 4 Sliding window, micro-motion, and stability tests
│   ├── test_model_updater.py      # 4 Integrity, signature, anti-downgrade, and rollback tests
│   ├── test_workflows.py          # 4 Resident, Operator, Supervisor policy tests
│   └── test_mds.py                # 6 MDS REST endpoint & capture contract tests
├── run_desktop_app.py             # Desktop Client UI launcher with --demo and --diagnostic flags
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
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Automated Test Suite (54 Tests)
Execute the complete unit and integration test suite:
```powershell
.\venv\Scripts\python -m pytest -v
```
*All 54 tests pass 100%, covering face quality assessment, passive heuristics, temporal active challenges, device abstractions, offline model updates, workflow policies, and MDS REST endpoints.*

---

## 🎬 Live Evaluator Demo Modes

The desktop client provides dedicated flags to demonstrate all 8 core evaluator scenarios instantly:

```powershell
# Demo 1: Bona Fide Live Subject (Natural facial capture)
.\venv\Scripts\python run_desktop_app.py --demo 1

# Demo 2: Photo Print Presentation Attack (Static paper presentation)
.\venv\Scripts\python run_desktop_app.py --demo 2

# Demo 3: Screen Replay Presentation Attack (Smartphone display with moiré + glare)
.\venv\Scripts\python run_desktop_app.py --demo 3

# Demo 4: Poor Lighting / Underexposed Subject (Low illumination rejection)
.\venv\Scripts\python run_desktop_app.py --demo 4

# Demo 5: Motion Blur & Poor Focus (Laplacian sharpness rejection)
.\venv\Scripts\python run_desktop_app.py --demo 5

# Demo 6: Multiple Faces in Frame (ISO 19794-5 single-subject enforcement)
.\venv\Scripts\python run_desktop_app.py --demo 6

# Demo 7: Active Liveness Challenge: Blink Verification (Temporal EAR cycle)
.\venv\Scripts\python run_desktop_app.py --demo 7

# Demo 8: Active Liveness Challenge: Smile Verification (Baseline-neutral delta hold)
.\venv\Scripts\python run_desktop_app.py --demo 8

# Launch in Evaluator Diagnostic Mode (Displays raw FPS, EAR, MAR, Yaw, PAD score HUD):
.\venv\Scripts\python run_desktop_app.py --mock --diagnostic
```

*Interactive Desktop Client Hotkeys*:
* `r`: Reset session and re-evaluate.
* `d`: Toggle **Evaluator Diagnostic Mode** on/off (shows FPS, EAR, MAR, Yaw, and score breakdown).
* `1`, `2`, `3`: Switch workflow policies on the fly (`1`: Resident, `2`: Operator, `3`: Supervisor).
* `q` or `Esc`: Gracefully quit.

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
