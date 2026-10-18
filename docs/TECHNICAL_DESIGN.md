# Technical design

This document describes the implemented research service and the boundaries required for integration into MOSIP Registration Clients. The custom HTTP service runs on a desktop host. Python, OpenCV, and MediaPipe are not an Android deployment architecture.

## Components and data flow

```mermaid
flowchart LR
    Camera[Webcam or explicit simulator] --> Device[Common frame adapter]
    Device --> Quality[Face count and image quality]
    Quality --> PAD[Passive ONNX or research heuristics]
    PAD --> Window[Temporal score and motion checks]
    Window --> Policy[Workflow policy]
    Policy --> Action[Random active action when required]
    Action --> PAD
    Policy --> Gate[Capture acceptance gate]
    Gate --> JPEG[Ephemeral application JPEG]
    Policy --> Audit[Redacted audit events]
    Policy --> Counters[Anonymous process counters]
    Preview[Preview and status UI] -. observes .-> Device
```

`VideoFrame` carries a BGR `uint8` array, dimensions, frame number, timestamp, and optional device metadata. The pipeline rejects invalid pixel layouts. It does not trust simulator metadata as evidence of a completed action. Device adapters implement connection, frame delivery, stream control, and capability discovery. The L1 adapter is simulated and does not supply secure hardware attestation.

## Decision flow

The pipeline detects faces and checks lighting, sharpness, size, and centering. A tracked face box cannot bypass the search for additional faces. Quality measurements are engineering heuristics; they do not produce an ISO face interchange record.

Passive evaluation returns `BONA_FIDE_LIVE`, `UNCERTAIN`, `PRESENTATION_ATTACK`, or `PROCESSING_ERROR`. Scores are model or heuristic outputs, not calibrated probabilities of human presence. The resident path accumulates 25 passive frames and evaluates a rolling window of 15. A high score also requires temporal stability and observed motion. Static or uncertain input escalates to active verification when enabled. Motion alone does not distinguish a live face from a moving photograph.

Operator and supervisor policies require active challenges by default. A random action is selected from the configured pool. The existing action detector tracks blink, smile, left/right turn, and up/down movement. An active frame still undergoes quality and PAD checks. A failed PAD result terminates acceptance. Face loss invalidates partial action history and consumes a retry. Terminal rejection cannot change to success without a reset.

All workflow decisions in this repository stop at liveness verification. An integrating client must additionally perform identity matching, registration packet construction, authorization, and any required SBI signature verification.

## Concurrency and privacy

One capture owns the pipeline. A nonblocking capture lock rejects concurrent capture, device replacement, and policy mutation with HTTP 409. A device lock serializes preview reads and capture reads. During capture, preview clients receive the latest processed frame. Preview clients never call `process_frame`.

Frames and the accepted image exist in memory. The service clears its captured-image and preview references after completion or timeout. Python cannot guarantee cryptographic erasure of every memory copy, and clients receiving the JPEG control their own retention. HTTP responses disable caching. The audit logger recursively removes buffers and common sensitive keys. Session counters retain totals only and reset on restart.

The audit chain links canonical event JSON with SHA-256. A separate trusted checkpoint is needed to detect deletion or wholesale replacement. It is not a substitute for a protected logging backend.

## Offline operation and configuration

The installed runtime and local models require no network calls for inference, action generation, or policy decisions. Installation and fetching an updated model require network access. Resident, operator, and supervisor policies have independent thresholds, required action counts, timeouts, retries, and active-challenge requirements. The API applies validated updates atomically, updates the actual detector threshold, and resets the session. Policies are in memory; secure synchronized configuration distribution is not implemented.

Global `liveness_enabled: false` stops verified capture. It cannot produce a JPEG labelled `livenessVerified=true`. A production enable/disable workflow must integrate an explicit, audited client policy for any permitted unchecked capture.

## Secure model updates

The updater signs a canonical manifest containing model name, semantic version, payload checksum, and metadata. Receivers verify the payload and signed manifest, reject path traversal, and compare the new version with a persisted high-water mark. Ed25519 receivers need only a public key. HMAC mode requires a shared secret and is a separate trust model.

The updater writes a temporary payload and swaps it atomically. Its conservative version high-water mark is written before publishing the new model. A crash can require operator recovery, but must not silently permit replay of an older version. A manual rollback preserves the high-water mark. The model file and version record are not a transactional database; multi-process deployment and power-loss testing remain integration work. Installation does not automatically hot-swap a running inference session.

## Native client integration

`NativeCaptureGate` is a portable Java 8 component, compiled and exercised independently. It binds accepted bytes to a session and permits consumption once. It must receive assessments from a trusted native inference adapter. It does not make a client-supplied `PASSED` field trustworthy.

The existing Java HTTP adapter now validates loopback URLs, restricts workflow names, requires a configured bearer token, limits response size, applies timeouts, and avoids printing biometric payloads. It is transport example code. No official Desktop or Android Registration Client build has been modified or run by these changes. See the [integration contract](NATIVE_INTEGRATION.md).

## Standards and evaluation

ISO/IEC 30107 is relevant to attack models and evaluation; this project does not claim certification. ISO/IEC 19794-5 defines a face image interchange format. A Base64 JPEG plus image-quality checks is not proof of that format's conformance. Real evaluation requires consented bona fide subjects, representative presentation attack instruments, device and lighting variation, fixed thresholds, separate development/test participants, and reported nonresponses. See the [evaluation protocol](EVALUATION_PROTOCOL.md).
