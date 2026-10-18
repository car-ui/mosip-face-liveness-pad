# Capture sequences

These diagrams describe the implemented prototype. The native client's identity matcher and final registration acceptance remain outside this repository's verified integration.

```mermaid
sequenceDiagram
    actor Person
    participant UI as Local console
    participant API as Research service
    participant Device as Webcam or simulator
    participant Engine as Liveness pipeline
    UI->>API: POST /capture with token and workflow
    API->>API: Acquire exclusive capture lock
    loop Frames until terminal decision or timeout
        API->>Device: read_frame
        Device-->>API: BGR frame
        API->>Engine: Face quality and passive PAD
        Engine->>Engine: Temporal checks and workflow policy
        alt Active action required
            Engine-->>API: Random action prompt
            UI->>API: GET /status
            API-->>UI: Prompt, guidance, progress
            Person->>Device: Respond to action
            API->>Engine: Next frame, quality, PAD, action detection
        end
        UI->>API: GET /stream
        API-->>UI: Latest preview, no pipeline mutation
    end
    alt Verified
        API-->>UI: Application JPEG, SHA-256, liveness verdict, simulation flag
    else Attack, engine error, retry limit, disconnect, or timeout
        API-->>UI: Safe failure and empty biometrics
    end
    API->>API: Clear image references, update anonymous counters, release lock
```

```mermaid
sequenceDiagram
    participant Client as Future native client adapter
    participant Gate as Portable capture gate
    participant Inference as Trusted native PAD and action engine
    participant Matcher as Identity matcher
    Client->>Gate: Create session with challenge policy and deadline
    loop Each trusted frame
        Client->>Inference: Frame and current challenge
        Inference-->>Client: Quality, PAD, action result
        Client->>Gate: Assessment bound to session and frame sequence
        Gate-->>Client: Continue, reject, or accept candidate digest
    end
    Client->>Gate: Consume exact accepted JPEG once
    Gate-->>Client: Permit or reject
    Note over Client,Matcher: This integration path is proposed, not run in official clients
    Client->>Matcher: Perform identity matching if liveness gate permits
```
