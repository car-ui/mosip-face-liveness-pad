# MOSIP Face Liveness Detection and Presentation Attack Detection (Decode 04)

An enterprise-ready, hardware-agnostic solution for **Face Liveness Detection** and **Presentation Attack Detection (PAD)** designed for the **MOSIP (Modular Open Source Identity Platform)** Desktop and Android Registration Clients.

Conforms to **ISO/IEC 30107-1/3**, **ISO/IEC 19794-5**, and the official **MOSIP Device Service (MDS)** architecture.

---

## 🚀 Key Features

* **Hybrid Passive-to-Active Decision Engine**:
  * Evaluates incoming frame streams using passive PAD (frequency analysis, moiré filtering, chromatic variance, specular glare detection).
  * Automatically transitions to dynamic active challenge-response if passive confidence is borderline.
* **Dynamic Active Challenges**:
  * Unpredictable challenge generation: **Blink** (Eye Aspect Ratio), **Smile** (Mouth Aspect Ratio), **Head Turn Left/Right** (SolvePnP 3D pose estimation).
  * Enforces real-time timeouts, countdown animations, and retry policies.
* **L0/L1 Device Integration & Mock Simulator (Bonus Deliverable)**:
  * Implements the **Device Adapter Pattern** (`FaceCaptureDevice`) ensuring complete independence from biometric hardware vendors.
  * Includes a built-in **Mock L0/L1 Device Simulator** for automated testing and CI/CD without physical hardware.
* **MOSIP Device Service (MDS) API Compliance**:
  * Exposes standard endpoints: `/info` (discovery), `/stream` (live MJPEG), and `/capture` (ISO compliant biometric packaging).
* **Multi-Workflow Support**:
  * Tailored policies and security thresholds for **Resident Registration**, **Operator Authentication**, and **Supervisor Authentication**.
* **100% Offline Capability**:
  * All inference executes locally on-device with zero cloud or network dependencies.
* **Java 21 Client Adapter**:
  * Includes a ready-to-run Java adapter for integration into MOSIP's existing Java Desktop Registration Client.

---

## 📁 Repository Structure

```
livliness/
├── docs/
│   ├── TECHNICAL_DESIGN.md        # Architecture, ISO compliance, and security
│   └── SEQUENCE_DIAGRAMS.md       # Mermaid sequence diagrams for all flows
├── src/
│   ├── core/
│   │   ├── config.py              # Configurable thresholds, policies, workflows
│   │   ├── face_detector.py       # ISO 19794-5 quality, blur, illumination checks
│   │   ├── passive_pad.py         # ISO 30107 Presentation Attack Detection
│   │   ├── active_liveness.py     # 3D facial landmark geometry (EAR, MAR, Pose)
│   │   ├── challenge_manager.py   # Dynamic challenge pool & timeout management
│   │   └── pipeline.py            # Master hybrid workflow orchestrator
│   ├── devices/
│   │   ├── base.py                # Device Adapter Pattern base interface
│   │   ├── webcam_device.py       # Live L0 Physical Webcam implementation
│   │   └── mock_l0_device.py      # Mock L0/L1 Simulator (bonus task)
│   ├── mds/
│   │   └── mds_server.py          # MOSIP Device Service REST & MJPEG server
│   ├── ui/
│   │   └── desktop_client.py      # Standalone Desktop Registration Client UI
│   └── java_integration/
│       └── MosipLivenessDeviceService.java # Java 21 MOSIP Client Adapter
├── tests/
│   ├── test_mock_device.py        # Mock L0 lifecycle & frame streaming tests
│   ├── test_passive_pad.py        # Presentation attack detection tests
│   ├── test_active_liveness.py    # Landmark geometry & state tests
│   ├── test_face_detector.py      # Biometric quality & blur tests
│   └── test_pipeline.py           # Hybrid state machine integration tests
├── run_desktop_app.py             # Desktop Client UI launcher
├── run_mds_service.py             # MOSIP Device Service (MDS) launcher
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
Ensure you have Python 3.11+ installed (installed on this system).

### 2. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Run the Desktop Registration Client
Launch the interactive desktop client with live camera preview and guidance:
```powershell
.\venv\Scripts\python run_desktop_app.py
```
* Hotkeys in app window:
  * Press `r` to reset and run a new test.
  * Press `1`, `2`, or `3` to switch workflows (Resident, Operator, Supervisor).
  * Press `q` or `Esc` to quit.

To start in Mock Device simulator mode:
```powershell
.\venv\Scripts\python run_desktop_app.py --mock
```

---

### 4. Run the MOSIP Device Service (MDS) & Web Console
Start the MDS server on port 4501:
```powershell
.\venv\Scripts\python run_mds_service.py
```
Now access:
* **Interactive Console**: [http://127.0.0.1:4501/](http://127.0.0.1:4501/)
* **Device Discovery**: [http://127.0.0.1:4501/info](http://127.0.0.1:4501/info)
* **Live Stream**: [http://127.0.0.1:4501/stream](http://127.0.0.1:4501/stream)
* **Biometric Capture**: `POST http://127.0.0.1:4501/capture`

---

### 5. Run the Automated Test Suite & Spoof Attack Simulation
Execute the unit and integration test suite:
```powershell
.\venv\Scripts\python -m pytest -v tests
```
*All 10 tests will execute and pass, verifying mock streaming, quality checks, passive PAD attacks, landmark mathematics, and pipeline state progression.*

Execute the real-world photo spoof presentation attack simulation:
```powershell
.\venv\Scripts\python test_photo_spoof_simulation.py
```
*Feeds static photos frame-by-frame and verifies that print/screen spoofs are 100% blocked.*

---

### 6. Run the Java Registration Client Adapter
With the MDS service running on port 4501, run the Java adapter:
```powershell
java -cp bin io.mosip.registration.liveness.MosipLivenessDeviceService
```

---

## 🛡️ Testing Presentation Attack Detection (PAD)

To verify the system's resilience against attacks:
1. **Photo Print Attack**: Hold up a printed photograph of a face $\rightarrow$ the system detects paper frequency roll-off and flat chrominance, rejecting the attack.
2. **Screen Replay Attack**: Display a photo or video of a face on a smartphone in front of the camera $\rightarrow$ the specular reflection and moiré harmonics trigger an immediate `ATTACK_DETECTED` status.
3. **Live Human Test**: Look into the camera $\rightarrow$ the system observes natural skin reflectance, triggers an active challenge if needed (e.g., "Please blink"), and successfully accepts the capture.
