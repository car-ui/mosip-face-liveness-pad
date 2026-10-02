# MOSIP Liveness & PAD Subsystem - Sequence Diagrams

This document contains end-to-end Mermaid sequence diagrams for all biometric workflows defined in MOSIP Decode Problem Statement 04.

---

## 1. Resident Registration Flow (Hybrid Passive-to-Active)

```mermaid
sequenceDiagram
    autonumber
    actor Resident as Resident / Citizen
    participant Client as Registration Client UI
    participant MDS as MOSIP Device Service (MDS)
    participant Device as L0/L1 Biometric Device
    participant Engine as Liveness & PAD Pipeline

    Resident->>Client: Approaches Registration Counter
    Client->>MDS: POST /capture (Workflow: RESIDENT_REGISTRATION)
    MDS->>Device: Connect and start frame stream
    Device-->>MDS: Frame stream (30 FPS)
    MDS-->>Client: Live video stream overlay (/stream)

    loop Every Incoming Frame
        MDS->>Engine: Process frame (Quality + Passive PAD)
        Engine-->>MDS: QualityMetrics + PADResult
    end

    alt Passive Liveness Score >= 0.80 (High Confidence)
        Engine-->>MDS: Decision: PASSED (Live Face Confirmed)
        MDS->>Device: Capture ISO 19794-5 compliant frame
        MDS-->>Client: Return 200 OK + Base64 Biometric Token
        Client->>Resident: Display "Good, face captured successfully"
    else Passive Liveness Score < 0.80 (Uncertain / Ambiguous)
        MDS->>Engine: Trigger Active Challenge State
        Engine->>Engine: Randomly select challenge (e.g. BLINK)
        Engine-->>MDS: ChallengeState: "Please blink naturally"
        MDS-->>Client: Prompt "Please blink" + countdown
        Resident->>Device: Performs dynamic blink action
        Engine->>Engine: Track EAR: Open -> Closed -> Open
        Engine-->>MDS: Action verified successfully!
        MDS-->>Client: Return 200 OK + Base64 Biometric Token
        Client->>Resident: Display "Biometric Accepted"
    else Presentation Attack Detected (Printed Photo / Screen Replay)
        Engine-->>MDS: Attack Detected (PAI: SCREEN_REPLAY)
        MDS-->>Client: Return 400 Rejected ("Verification could not be completed")
        Client->>Resident: Display safe generic error & prompt retry
    end
```

---

## 2. Operator Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Registration Operator
    participant Client as Registration Client UI
    participant MDS as MOSIP Device Service (MDS)
    participant Engine as Liveness & PAD Pipeline
    participant AuthServer as MOSIP Auth Server (Offline/Online)

    Operator->>Client: Login / Initiate Biometric Auth
    Client->>MDS: POST /capture (Workflow: OPERATOR_AUTHENTICATION, Threshold: 0.88)
    MDS->>Engine: Apply Operator Policy (Strict Threshold = 0.88)
    MDS-->>Client: Live Stream with centering guide

    MDS->>Engine: Evaluate Frame Stream
    alt Strict Passive Passed
        Engine-->>MDS: Liveness Confirmed
    else Active Challenge Required
        Engine-->>Client: Prompt "Please smile"
        Operator->>MDS: Performs smile action
        Engine-->>MDS: Action verified (MAR ratio > 0.76)
    end

    MDS-->>Client: Signed Biometric Token
    Client->>AuthServer: 1:1 Match against registered operator biometric
    AuthServer-->>Client: Operator Authenticated Successfully
    Client->>Operator: Unlock Registration Desk
```

---

## 3. Supervisor Override & Multi-Challenge Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor Supervisor as Center Supervisor
    participant Client as Registration Client UI
    participant MDS as MOSIP Device Service (MDS)
    participant Engine as Liveness & PAD Pipeline

    Note over Supervisor, Engine: Supervisor workflow mandates 2 sequential dynamic challenges
    Supervisor->>Client: Authenticate for Exception Override
    Client->>MDS: POST /capture (Workflow: SUPERVISOR_AUTHENTICATION, MinChallenges: 2)
    MDS->>Engine: Initialize ChallengeManager (Count = 2)

    Engine-->>Client: Challenge 1/2: "Please turn your head to the left"
    Supervisor->>MDS: Turns head left (Yaw > +16°)
    Engine->>Engine: Action 1 completed

    Engine-->>Client: Challenge 2/2: "Please blink"
    Supervisor->>MDS: Blinks eyes (EAR drop/rise)
    Engine->>Engine: Action 2 completed

    Engine-->>MDS: Supervisor Liveness Confirmed (All challenges met)
    MDS-->>Client: Supervisor Biometric Artifact + Audit Trail
    Client->>Supervisor: Override Approved
```

---

## 4. Device Error Handling & Disconnection Recovery Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client as Registration Client UI
    participant MDS as MOSIP Device Service (MDS)
    participant Hardware as Physical USB Camera

    Client->>MDS: GET /info (Device Discovery)
    MDS->>Hardware: Query USB descriptor
    alt Hardware Missing / Disconnected
        Hardware-->>MDS: Device Not Responding
        MDS->>MDS: Auto-failover to Mock L0 Simulator
        MDS-->>Client: Report Status: MOCK_L0_SIMULATOR (Fallback active)
        Client->>Client: Notify operator: "Operating in simulated device mode"
    else Hardware Available
        Hardware-->>MDS: Ready (L0 Webcam)
        MDS-->>Client: Report Status: CONNECTED
    end

    loop Video Streaming
        Hardware--xMDS: Sudden USB Disconnect Event
        MDS->>Client: Error 503: "Camera unavailable. Check device connection."
        Client->>Client: Pause UI capture, show reconnect prompt
    end
```
