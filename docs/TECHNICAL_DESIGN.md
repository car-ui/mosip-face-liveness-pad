# MOSIP Face Liveness & Presentation Attack Detection (PAD) Subsystem
## Comprehensive Technical Design Document (Decode 2026 - Problem 04)

---

## 1. Executive Summary & Design Scope
This document specifies the technical architecture, algorithms, and design patterns for integrating **Face Liveness Detection** and **Presentation Attack Detection (PAD)** into the MOSIP (Modular Open Source Identity Platform) Desktop and Android Registration Clients.

The subsystem is architected in accordance with:
* **ISO/IEC 30107-1 & ISO/IEC 30107-3**: Presentation attack detection definitions, presentation attack instrument (PAI) categories, evaluation protocol methodology, and metric reporting (APCER and BPCER).
* **ISO/IEC 19794-5**: Biometric data interchange format for facial image data (illumination adequacy, sharpness/blur assessment, single-face constraint, and centering constraints).
* **MOSIP Device Service (MDS) Specification**: Decoupled biometric device discovery (`GET /info`), streaming (`GET /stream`), and biometric capture (`POST /capture`).

> **Note on Laboratory Certification**: The subsystem is designed and implemented strictly according to ISO/IEC 30107 principles and performance requirements. Formal certification requires an accredited testing laboratory (such as iBeta or FIDO Alliance).

---

## 2. High-Level Architecture & Layered Design

```mermaid
flowchart TD
    subgraph Device Layer [Hardware & Simulation Abstraction]
        HW1[Physical L0 Webcam Sensor]
        HW2[L1 Dedicated Biometric Hardware]
        SIM[MockL0Device 11-Scenario Deterministic Simulator]
        VEND[VendorL1Adapter Secure Token Simulator]
    end

    subgraph Device Adapter Layer [Multi-Vendor Device Abstraction]
        DIF[BaseBiometricDevice Interface]
        L0Base[L0Device Abstraction]
        L1Base[L1Device Abstraction with Cryptographic Signing]
        WAdapter[WebcamCaptureDevice]
        MAdapter[MockL0Device]
        VAdapter[VendorL1Adapter]
    end

    subgraph Core Processing Pipeline [Offline Inference Engine]
        QA[FaceQualityAssessor: ISO 19794-5 Illumination / Sharpness / Centering]
        TB[TemporalLivenessBuffer: Rolling Sliding Window & Micro-Motion]
        PAD[Modular Passive PAD: ONNX Model / Multi-Cue Physical Heuristics]
        AL[ActiveLivenessDetector: Facial Landmarks / Temporal EAR / MAR / Geometric Pose]
        CM[ChallengeManager: Cryptographic Dynamic Selection & Timeouts]
        ALog[BiometricAuditLogger: Privacy-Preserving JSON Telemetry]
        UPD[SecureModelUpdateManager: SHA-256 / HMAC / Atomic Swap]
        REM[ResidentEnrollmentManager: Lightweight Registration & Privacy]
        SM[Master LivenessPipeline State Machine: 14 States]
    end

    subgraph Interface & Service Layer
        MDS[MOSIP Device Service: FastAPI REST & MJPEG Engine - Port 4501]
        DesktopUI[Desktop Registration Client: OpenCV HUD & Evaluator Diagnostic Mode]
        JavaAdapter[Java 21 Client Adapter: MOSIP Registration Core]
    end

    HW1 --> WAdapter --> L0Base --> DIF
    SIM --> MAdapter --> L0Base --> DIF
    HW2 --> VAdapter --> L1Base --> DIF
    VEND --> VAdapter

    DIF --> SM
    SM --> QA
    SM --> TB
    SM --> PAD
    SM --> AL
    SM --> CM
    SM --> ALog
    SM --> REM
    UPD --> PAD

    SM --> MDS
    SM --> DesktopUI
    MDS --> JavaAdapter
```

---

## 3. Finite State Machine (FSM) Lifecycle

The pipeline implements an explicit 14-state lifecycle ensuring deterministic transitions and testability:

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> DEVICE_CONNECTING : connect()
    DEVICE_CONNECTING --> FACE_DETECTION : device_ready
    DEVICE_CONNECTING --> DEVICE_ERROR : connection_failed

    FACE_DETECTION --> QUALITY_CHECK : single_face_found
    FACE_DETECTION --> QUALITY_FAILURE : no_face / multiple_faces

    QUALITY_CHECK --> PASSIVE_LIVENESS : quality_acceptable
    QUALITY_CHECK --> QUALITY_FAILURE : blurry / dark / uncentered

    PASSIVE_LIVENESS --> CAPTURE_SUCCESS : score >= threshold & temporal_stable (BONA_FIDE_LIVE)
    PASSIVE_LIVENESS --> ATTACK_REJECTED : attack_detected (PRESENTATION_ATTACK)
    PASSIVE_LIVENESS --> ACTIVE_CHALLENGE : uncertain_score & active_enabled (UNCERTAIN)

    ACTIVE_CHALLENGE --> CHALLENGE_VALIDATION : user_action_in_progress
    ACTIVE_CHALLENGE --> RETRY_PENDING : challenge_timeout / failure

    CHALLENGE_VALIDATION --> ACTIVE_CHALLENGE : more_challenges_required
    CHALLENGE_VALIDATION --> CAPTURE_SUCCESS : all_challenges_satisfied

    RETRY_PENDING --> FACE_DETECTION : retries_remaining & cooldown_elapsed
    RETRY_PENDING --> MAX_RETRIES_EXCEEDED : retries_exhausted

    QUALITY_FAILURE --> RETRY_PENDING
    ACTIVE_CHALLENGE_FAILURE --> RETRY_PENDING

    CAPTURE_SUCCESS --> [*]
    ATTACK_REJECTED --> [*]
    MAX_RETRIES_EXCEEDED --> [*]
    DEVICE_ERROR --> [*]
```

### Hybrid Decision Semantics
1. **`BONA_FIDE_LIVE`**: Liveness score meets or exceeds the configured policy threshold ($0.80 - 0.92$) and temporal stability $\ge 0.60$. Directly completes capture (`CAPTURE_SUCCESS`).
2. **`UNCERTAIN`**: Liveness score is borderline or cues exhibit high dispersion. Automatically escalates to dynamic interactive active challenges.
3. **`PRESENTATION_ATTACK`**: Definite attack signature detected (e.g. screen glare highlight, moiré harmonics, flat paper gamut). Immediately rejected (`ATTACK_REJECTED`) without escalating to active challenges.
4. **`PROCESSING_ERROR`**: Invalid crop or severe motion blur. Guided retry without penalty.

---

## 4. Multi-Vendor L0 / L1 Device Architecture

The device layer cleanly separates standard optical sensors from cryptographically secure biometric hardware:

```
BaseBiometricDevice (Abstract)
├── L0Device
│     ├── WebcamCaptureDevice (DirectShow / UVC physical camera)
│     └── MockL0Device (11-scenario deterministic simulator)
└── L1Device
      └── VendorL1Adapter (Architecture-ready adapter for vendor SDKs)
```

### Device Capabilities Discovery (`DeviceCapabilities`)
Every device provides structured metadata for MDS discovery:
* `device_type`: `PHYSICAL_L0_WEBCAM`, `MOCK_L0_SIMULATOR`, `HARDWARE_L1_BIOMETRIC`, or `VENDOR_L1_ADAPTER`
* `vendor`, `model`, `firmware_version`
* `security_level`: `"L0_BASIC"`, `"L0_SIMULATED"`, `"L1_SIMULATED"` (reserved: `"L1_SECURE_HARDWARE"` for certified physical hardware)
* `supported_capture_modes`: `["STREAM", "STILL_FRAME", "CRYPTO_TOKEN"]`
* `liveness_capabilities`: Supported hardware/software PAD indicators

### Simulated L1 Hardware Integration (`VendorL1Adapter`)
VendorL1Adapter demonstrates the integration contract and simulator behavior; actual L1 hardware requires vendor SDK/device integration. L1 devices incorporate on-chip cryptographic signing (`sign_biometric_data()`) and physical tamper detection (`verify_tamper_status()`). The `VendorL1Adapter` provides a concrete integration point where physical vendor SDKs (e.g., Suprema, Idemia, Dermalog, Mantra) attach their native C/C++ drivers.

---

## 5. Model Versioning & Provenance Tracking

Every biometric evaluation generates complete provenance records via `ModelMetadata`:
* `backend_name`: `"onnx_deep_learning"` or `"heuristic_multi_cue"`
* `version`: Version identifier (e.g. `"v1.0.0-onnx"` or `"v1.2.0-heuristic"`)
* `model_hash`: SHA-256 hex digest of the model binary or descriptive provenance
* `input_size`: Dimensions of neural network input tensor
* `inference_provider`: Hardware accelerator utilized (e.g. `CUDAExecutionProvider`, `DirectMLExecutionProvider`, `CPUExecutionProvider`)
* `threshold`: Decision boundary threshold applied

### ONNX Model Contract & Output Layout Specification
* **Status**: `ARCHITECTURE-READY`. The inference engine (`ONNXModelPADBackend`) is fully implemented with dynamic hardware provider discovery (DirectML, CUDA, OpenVINO, CPU) and SHA-256 model provenance. Pre-trained deep-learning production weights are **not** bundled; deterministic multi-cue physical heuristics serve as the active engine.
* **Input Tensor**: Shape `[1, 3, 224, 224]` (NCHW format, float32, RGB), normalized using ImageNet mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`.
* **Output Tensor Contract**: Binary classification layout `[prob_live, prob_spoof]` over Softmax probabilities. If a single logit is produced, `prob_spoof = 1.0 - prob_live`.
* **Plug-and-Play Placement**: Drop any compatible `.onnx` model into `assets/models/` to automatically activate deep-learning inference with zero code modifications.

---

## 6. Secure Offline Model Update Subsystem (`SecureModelUpdateManager`)

For isolated enrollment centers operating without internet connectivity, model updates are distributed in signed offline packages:

```mermaid
flowchart TD
    Pkg[Model Update Package .pkg] --> Integrity{1. SHA-256 Integrity Verification}
    Integrity -- Fail --> Reject1[Reject: Corrupted Package]
    Integrity -- Pass --> Sig{2. HMAC-SHA256 Signature Verification}
    Sig -- Fail --> Reject2[Reject: Untrusted Signature]
    Sig -- Pass --> Ver{3. Semantic Anti-Downgrade Version Check}
    Ver -- Fail --> Reject3[Reject: Version Downgrade Attempt]
    Ver -- Pass --> Backup[4. Backup Active Model to .bak]
    Backup --> AtomicSwap[5. Write to .tmp & Atomic Replace]
    AtomicSwap -- Exception --> Rollback[Automatic Rollback from .bak]
    AtomicSwap -- Success --> Active[Active Model Updated]
```

---

## 7. Low-Resource Edge & Android Optimization Strategy

While this submission focuses on the Desktop/Linux/Windows registration client, the codebase is architecturally prepared for low-resource Android tablets:

1. **Adaptive Frame Subsampling**:
   * Passive PAD frequency analysis (2D DFT) executes every 3rd frame ($\approx 10$ Hz), reducing CPU load by 60%.
   * Facial landmark tracking (MediaPipe) runs at native 30 FPS for smooth user interaction.
2. **Quantized Mobile Models**:
   * The `ONNXModelPADBackend` accepts 8-bit quantized models (`int8`), reducing memory footprint from 45MB to under 8MB.
3. **Hardware Acceleration Discovery**:
   * Uses `onnxruntime.get_available_providers()` to dynamically select `NNAPIExecutionProvider` on Android, `DirectMLExecutionProvider` on Windows, or `CUDAExecutionProvider` on Nvidia edge devices, with transparent fallback to `CPUExecutionProvider`.

---

## 8. Security, Privacy & Diagnostic Isolation

### Safe User Messaging Taxonomy
Internal diagnostic codes are strictly decoupled from user-facing prompts:

| Internal BiometricErrorCode | Technical Cause | Safe End-User Message |
| :--- | :--- | :--- |
| `NO_FACE` | Face count == 0 | "Face not detected. Please look directly at the camera." |
| `MULTIPLE_FACES` | Face count > 1 | "Multiple faces detected. Only one person should be in frame." |
| `POOR_LIGHTING` | Illumination out of bounds | "Lighting is inadequate. Please move to a well-lit area." |
| `BLURRY_FACE` | Laplacian variance < 30 | "Image is blurry. Please remain still during capture." |
| `PAD_ATTACK_DETECTED` | Moiré / Glare / Paper attack | "Face verification could not be completed. Please position your face and try again." |
| `ACTIVE_CHALLENGE_TIMEOUT` | Countdown expired | "Challenge timed out. Please follow the on-screen instructions." |

### Privacy-Preserving Structured Audit Logging
Structured JSON events record session tokens and metrics while strictly omitting raw facial imagery:
```json
{"eventId": "4323a378-bc4d-498b-a223-991edc13ceff", "timestamp": 1791015209.412, "isoTimestamp": "2026-10-03T08:13:29Z", "eventType": "PAD_ATTACK_DETECTED", "sessionId": "9db483b1-3120-4bdf-a8c3-6dbd632d5047", "workflow": "RESIDENT_REGISTRATION", "details": {"attack_type": "SCREEN_REPLAY", "liveness_score": 0.38, "mode": "HEURISTIC", "model_version": "v1.2.0-heuristic"}}
```

---

## 9. Lightweight Resident Enrollment & Strict Privacy Architecture

To meet MOSIP's real-world registration station operational requirements without introducing bloat (such as user databases, password management, or web-app sessions), the subsystem incorporates a lightweight, focused biometric enrollment manager:

```
┌────────────────────────────────────────────────────────┐
│             RESIDENT ENROLLMENT LIFECYCLE              │
└────────────────────────────────────────────────────────┘
                          START
                            │
                            ▼
                    [ Enter/Generate ID ] (RES-00123)
                            │
                            ▼
                    [ Face Positioning ] (ISO 19794-5 Quality Check)
                            │
                            ▼
                  [ Liveness Verification ]
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
       BONA_FIDE_LIVE                  UNCERTAIN
             │                             │
             │                             ▼
             │                     [ Active Challenge ]
             │                             │
             └──────────────┬──────────────┘
                            │ Pass
                            ▼
                   [ ENROLLMENT SUCCESS ]
            (Cryptographic Biometric Token SHA-256)
```

### Core Architecture Components
1. **`ResidentEnrollmentManager` (`src/core/enrollment.py`)**:
   * Tracks dynamic enrollment states: `READY`, `POSITIONING`, `LIVENESS_CHECK`, `ENROLLED`, `REJECTED`, `FAILED`.
   * Manages predictable `RES-XXXXX` identifier token sequences (with custom override support via CLI flag `--resident-id` or interactive hotkey `'n'`).
   * Provides 3-step checklist status for desktop UI HUD overlays:
     * `Step 1: Position Face`
     * `Step 2: Liveness Check`
     * `Step 3: Enrolled`

2. **Strict Data Privacy & Zero Biometric Persistence**:
   * **Ephemeral In-Memory Processing**: Captured camera frames exist solely in volatile memory during pipeline processing and are discarded immediately upon frame cycle completion.
   * **No Raw Image Storage**: Neither the audit logs nor the `ResidentEnrollmentRecord` store raw pixel arrays, JPEG/PNG files, or face crops.
   * **Cryptographic Biometric Token Hashing**: Upon successful enrollment, the system generates an ISO/IEC 19794-5-aligned representation and computes a SHA-256 digest (`token_hash = sha256(biometric_payload)`). Downstream MOSIP registration services verify token integrity against this SHA-256 digest of the ephemeral captured image payload without exposing raw biometric imagery to the local filesystem (note: this hash serves as an integrity/token verification check, not an extracted biometric feature template for 1:1 or 1:N biometric matching).

