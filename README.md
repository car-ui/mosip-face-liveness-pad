# MOSIP Face Liveness Detection and Presentation Attack Detection (Decode 2026 - Problem 04)

[![Tests: 41 Passed](https://img.shields.io/badge/Tests-41%20Passed-brightgreen.svg)]()
[![Platform: Offline-First](https://img.shields.io/badge/Architecture-100%25%20Offline-blue.svg)]()
[![Standard: ISO/IEC 30107 & 19794-5 Aligned](https://img.shields.io/badge/Standards-ISO%2FIEC%2030107%20%7C%2019794--5-orange.svg)]()
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![Java: 21 Ready](https://img.shields.io/badge/Java-21%20Ready-red.svg)]()

A robust, enterprise-grade, hardware-agnostic solution for **Face Liveness Detection** and **Presentation Attack Detection (PAD)** designed for the **MOSIP (Modular Open Source Identity Platform)** Desktop and Android Registration Clients.

> **Design Philosophy & Integrity**: Built for production readiness and academic rigor. The architecture modularly isolates deep-learning ONNX model inference from deterministic multi-cue physical heuristics. The system operates 100% offline, logs zero raw biometrics, and explicitly reports whether decisions are driven by `MODEL` or `HEURISTIC` engines.

---

## 🚀 Key Architectural Highlights

1. **Modular Passive PAD Engine (ISO/IEC 30107 Aligned)**:
   * **Pluggable ONNX Inference Interface**: Allows dropping in pre-trained ONNX liveness models (`.onnx`) with zero code modifications.
   * **Deterministic Multi-Cue Heuristic Fallback**: Analyzes 2D Discrete Fourier Transform (DFT) high-frequency moiré harmonics, YCrCb/HSV chrominance distribution, specular glass/screen reflection glare, and Sobel micro-texture gradient depth.
   * **Calibrated Confidence**: Computes dispersion across cues and exposes a 4-way verdict: `BONA_FIDE_LIVE`, `UNCERTAIN`, `PRESENTATION_ATTACK`, or `PROCESSING_ERROR`.
   * **Operational Mode Transparency**: Never fakes deep-learning inference; explicitly signals `operational_mode` (`MODEL` or `HEURISTIC`) in results and audit logs.

2. **Temporal Consistency Window (`TemporalLivenessBuffer`)**:
   * Evaluates rolling weighted confidence, min/max score bounds, variance, and micro-motion trajectory across a configurable sliding frame window (default: 15–25 frames).
   * Prevents single aberrant frames from triggering false accepts or false rejections.
   * Detects completely frozen/static presentation attacks (zero micro-motion variance).

3. **Dynamic Unpredictable Active Challenges**:
   * **Cryptographically Unpredictable**: Dynamic selection using `secrets.SystemRandom()` with non-repeating memory pool.
   * **Temporal State Machines**:
     * **Blink**: Strict three-phase `OPEN -> CLOSED -> OPEN` Eye Aspect Ratio (EAR) sequence with duration validation.
     * **Smile**: Baseline-neutral differential calculation ($\Delta \ge 0.15$) held over $N \ge 3$ consecutive frames.
     * **Head Turn**: Temporal yaw progression (`CENTER -> TURN -> CENTER`) using Perspective-n-Point (SolvePnP) 3D head pose estimation.
   * **Anti-Replay Protection**: Rejects static photos and non-responsive replays.

4. **L0/L1 Device Abstraction & Deterministic Mock Simulator**:
   * Implements the **Device Adapter Pattern** (`FaceCaptureDevice`), completely isolating CV pipelines from physical hardware APIs.
   * **Comprehensive Scenario Simulator (`MockL0Device`)**: Reproducibly simulates 10 critical operational conditions for automated CI/CD:
     * `BONA_FIDE_LIVE`, `STATIC_PHOTO_ATTACK`, `SCREEN_REPLAY_ATTACK`, `NO_FACE`, `MULTIPLE_FACES`, `POOR_LIGHTING_DARK`, `POOR_LIGHTING_BRIGHT`, `POOR_LIGHTING_UNEVEN`, `BLURRY_FRAME`, `DEVICE_DISCONNECT`, `INVALID_FRAME`.
     * Supports programmable scripted actions (`BLINK`, `SMILE`, `TURN_LEFT`, `TURN_RIGHT`).

5. **Multi-Workflow Policy Engine**:
   * **Resident Registration**: Low-friction passive evaluation ($0.80$ threshold) with automatic active challenge escalation on uncertainty.
   * **Operator Authentication**: High-security threshold ($0.88$) with 1 mandatory challenge and tight timeouts.
   * **Supervisor Authentication**: Maximum security ($0.92$) requiring 2 sequential multi-challenges for biometric override.

6. **MOSIP Device Service (MDS) REST & MJPEG Service**:
   * Compliant with MOSIP Device Service architectural patterns on `http://127.0.0.1:4501/`.
   * Standard endpoints: `/info` (device discovery), `/stream` (live MJPEG overlay), `/capture` (biometric token generation with ISO 19794-5 packaging), `/configure` (runtime threshold updates), and `/switch-device`.
   * Full Pydantic request/response schema validation with standard HTTP error codes (`400`, `408`, `503`).

7. **Security & Privacy Protections**:
   * **Safe Error Taxonomy**: Clear separation between internal diagnostics (`SCREEN_REPLAY_DETECTED`, `MOIRE_HARMONICS_DETECTED`) and safe user-facing instructions (`"Verification could not be completed. Please position your face and try again."`) to prevent reverse-engineering of PAD thresholds.
   * **Zero Raw Biometric Logging**: Structured JSON audit logger (`BiometricAuditLogger`) logs UUID session tokens, timestamps, and detection metrics, while strictly omitting raw facial imagery.
   * **100% Offline Execution**: Zero external telemetry, cloud APIs, or outbound connections.

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
│   │   ├── passive_pad.py         # Modular ONNX & multi-cue physical heuristic PAD engine
│   │   ├── active_liveness.py     # Temporal EAR, MAR, and SolvePnP 3D pose state machines
│   │   ├── challenge_manager.py   # Cryptographic challenge selection & timeout tracker
│   │   └── pipeline.py            # Master hybrid state machine orchestrator
│   ├── devices/
│   │   ├── base.py                # Device Adapter interface & MockScenario enums
│   │   ├── webcam_device.py       # Physical L0 Webcam adapter
│   │   └── mock_l0_device.py      # 10-scenario deterministic mock biometric device
│   ├── mds/
│   │   └── mds_server.py          # MOSIP Device Service REST & MJPEG server
│   ├── ui/
│   │   └── desktop_client.py      # Standalone Desktop Client UI with cinematic HUD
│   └── java_integration/
│       └── MosipLivenessDeviceService.java # Java 21 MOSIP Client Adapter
├── tests/
│   ├── test_face_detector.py      # 8 ISO 19794-5 quality assessment unit tests
│   ├── test_passive_pad.py        # 5 Passive PAD cue & ONNX fallback tests
│   ├── test_active_liveness.py    # 7 Temporal EAR, Smile, Pose & timeout tests
│   ├── test_mock_device.py        # 5 Lifecycle & scenario generation tests
│   ├── test_pipeline.py           # 6 Master state machine & transition tests
│   ├── test_workflows.py          # 4 Resident, Operator, Supervisor policy tests
│   └── test_mds.py                # 6 MDS REST endpoint & capture contract tests
├── run_desktop_app.py             # Desktop Client UI launcher with --demo flags
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

### 3. Run the Automated Test Suite (41 Tests)
Execute the complete unit and integration test suite:
```powershell
.\venv\Scripts\python -m pytest -v
```
*All 41 tests pass 100%, covering face quality assessment, passive heuristics, temporal active challenges, device abstractions, workflow policies, and MDS REST endpoints.*

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
```

*Interactive Desktop Client Hotkeys*:
* `r`: Reset session and re-evaluate.
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

This benchmark feeds print photos, smartphone screen replays with moiré/glare artifacts, 2D displays, and bona fide samples through the temporal pipeline and computes:
* **Attack Presentation Classification Error Rate (APCER)**: Proportion of presentation attacks erroneously accepted.
* **Bona Fide Presentation Classification Error Rate (BPCER)**: Proportion of bona fide presentations erroneously rejected.
* **Pipeline Latency & Frame Rate (FPS)**.

> *Note*: Experimental evaluation metrics reflect local testing fixtures and do not constitute formal laboratory certification under ISO/IEC 19792 or 30107.

---

## ☕ Java 21 Client Adapter

With the MDS server running on port 4501, execute the Java 21 adapter:
```powershell
javac -d bin src/java_integration/MosipLivenessDeviceService.java
java -cp bin io.mosip.registration.liveness.MosipLivenessDeviceService
```
The adapter connects via HTTP/JSON to the MDS server, initiates biometric capture for the specified workflow, verifies the response payload, and decodes the ISO 19794-5 image token.

---

## 🛡️ Security, Privacy & Compliance Statements

* **Zero Biometric Leakage**: In accordance with biometric privacy principles, raw images are processed strictly in volatile memory. No facial imagery is saved to disk or emitted to logs.
* **Safe Diagnostics**: Detailed presentation attack diagnostics (e.g., moiré peak frequencies, chromatic standard deviation) are strictly logged internally for security audits and are never displayed in end-user guidance text.
* **No False Certification Claims**: While the codebase is strictly engineered in accordance with ISO/IEC 30107 and ISO/IEC 19794-5 requirements, formal certification requires an accredited third-party evaluation laboratory (e.g., iBeta, FIDO).
