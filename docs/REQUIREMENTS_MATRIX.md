# Problem 04 requirement evidence

Reviewed against the supplied `ps4.pdf`, including mandatory tasks on pages 6-9, bonus and good-to-have tasks on page 10, and deliverables on pages 11-12. The root evaluation PDF assigns 40/40/10/10 to functionality, quality, UX, and presentation. Status describes available evidence, not a jury score.

`Implemented` means code with automated verification at the stated scope. `Partial` means a prototype, simulator, or adapter exists but a required integration or real-world validation is missing. `Unverified` means this repository does not establish the requirement.

## Mandatory tasks

| Requirement | Status and evidence | Remaining acceptance evidence |
|---|---|---|
| 1. L0/L1 device integration | Partial. Webcam adapter, common BGR frame interface, simulator scenarios, explicit capability discovery, disconnect handling. `tests/test_mock_device.py`, `tests/test_mds.py`. | Physical vendor L1 SDK, signed frame/attestation verification, device format coverage, at least two real vendors. Simulated L1 does not establish hardware integration. |
| 2. Passive liveness | Partial. Local ONNX inference and research heuristics, declared preprocessing, threshold comparisons, temporal decision buffer, model-error rejection. `tests/test_passive_pad.py`, `tests/test_security_regressions.py`. | Independent bona fide/attack evaluation, threshold calibration, representative subjects/devices/lighting, offline camera E2E. |
| 3. Presentation attack detection | Partial. PAD gates passive and active acceptance; rejection returns no biometric payload. Strict ONNX mode cannot silently fall back after runtime errors. | Real printed-photo, screen-replay, 3D-mask, and injection tests as applicable; ISO/IEC 30107 evaluation protocol execution. Heuristic fixture rejection is not attack accuracy. |
| 4. Active liveness | Implemented at prototype scope. Random action selection, automatic prompts, temporal blink/smile/pose detection, per-frame PAD re-evaluation, action invalidation on face loss, multi-challenge progression. `tests/test_active_liveness.py`, security regressions. | Camera-observed action completion, accessibility evaluation, adaptive replay testing, independently measured false acceptance/rejection. |
| 5. Resident registration | Partial. Pinned desktop and Android clients build. Actual desktop resident controller rejects a synthetic blank ISO before returning candidates. Android emulator tests execute ONNX and verify rejection before registration storage. `integrations/native/validation.json`. | Complete native camera/UI/packet-generation E2E, live stream/challenge linkage, physical Android hardware and physical attacks. |
| 6. Operator authentication | Partial. Required prototype actions and native desktop checkpoint before the official identity matcher. Actual patched `BaseController` rejects a blank ISO candidate with zero matcher calls in a synthetic test. | Active evidence is not connected to the native adapter, so valid operator face authentication is blocked. Native UI and offline authentication E2E remain unverified. |
| 7. Supervisor authentication | Partial. Native desktop checkpoint before the same upstream matcher, exercised with the supervisor flag. | Active evidence connection, supervisor override/bypass audit, successful identity matching and offline E2E. |
| 8. Configuration | Partial. Per-workflow thresholds, active enablement, required counts, challenge pools, timeout, retry limit, global liveness enablement, configurable guidance, enum/range validation. Disabled liveness never produces a verified capture. | Integration with MOSIP's configuration framework, durable offline policy files, authenticated online synchronization. API settings reset on restart. |
| 9. Error handling | Implemented at prototype scope. Missing/multiple/poor-quality faces, invalid BGR data, unavailable model, exceptions, disconnect, timeout, retry exhaustion, concurrent requests, invalid configuration. | Real vendor communication faults and recovery, complete hardware/OS matrix. |
| 10. UI/UX | Partial. Live preview, face guide, passive status, automatic active prompt, progress, safe failure messages, retry availability, diagnostics, narrow-screen layout, keyboard focus and live announcements. | Official Desktop/Android client screens, human accessibility/usability tests, camera/action E2E. |

## Good-to-have tasks

| Requirement | Status and evidence | Limit |
|---|---|---|
| Configurable challenge pools | Implemented through `/configure` and `supported_challenges`. | Pool changes require an authenticated evaluator; settings are in memory. |
| Multiple facial actions | Implemented blink, smile, left/right turn, look up/down action logic. | Physical action detection quality is unmeasured. |
| Different workflow policies | Implemented resident/operator/supervisor profiles and security regressions. | Full MOSIP workflow integration is pending. |
| Configurable user guidance | Implemented validated state-to-message mapping. | Localization and accessibility-specific alternatives need review. |
| Diagnostic mode | Implemented browser diagnostics, `/info`, `/configuration`, `/status`, OpenCV diagnostic toggle. | Diagnostics remain for local evaluation. |
| Multiple biometric vendors | Partial common adapter interface and simulated vendor adapter. | Multiple physical vendor integrations are unverified. |
| Anonymized operational metrics | Implemented process-level aggregate counters without subject IDs/images. | No durable telemetry store or population representativeness. |
| Performance metrics | Implemented mean capture time, mean challenge time, retry/failure rates. Dataset tool records p50/p95 frame latency. | Android latency, power, memory, and population accuracy are unmeasured. |
| Device capability discovery | Implemented structured device type, security level, modes, resolutions, simulation status. | Physical vendor capability accuracy requires hardware verification. |

## Bonus tasks

| Requirement | Status and evidence | Limit |
|---|---|---|
| Mock L0/L1 device | Implemented explicit simulators, marked uncertified and without hardware-liveness claims. | Simulation only. |
| Automated liveness scenarios | Implemented action, workflow, retry, quality, and policy tests. | Injected telemetry tests establish control flow, not face-action model accuracy. |
| Automated PAD attack scenarios | Implemented synthetic print/glare/replay fixtures and active PAD regressions. | No representative physical attack dataset. |
| Interoperability testing framework | Partial common device contract tests and portable Java gate tests. | No real cross-vendor or official native-client E2E matrix. |
| Model version management | Implemented model provenance, checksums, signed version metadata, persisted downgrade high-water mark. | Model approval/revocation distribution and multi-process deployment need integration. |
| Secure offline model updates | Implemented Ed25519 verification, manifest/payload integrity, version checks, atomic model replacement, retained rollback ceiling. | Public-key provisioning, revocation, disk-failure testing, and transactional metadata are deployment work. |
| Low-resource Android optimization | Unverified. Small research model and portable Java policy code are useful starting points. | On-device inference, measured latency/RAM/energy, Camera/SBI integration, and APK E2E required. Python desktop inference is not Android optimization. |
| Hardware acceleration | Partial ONNX provider discovery and CPU fallback. | Available GPU/NPU execution and parity must be measured on target hardware. |

## Deliverables and submission

| Deliverable | Available artifact | Remaining work |
|---|---|---|
| Technical design, interfaces, security, sequences | `TECHNICAL_DESIGN.md`, `SEQUENCE_DIAGRAMS.md`, `NATIVE_INTEGRATION.md`, `MODEL_CARD.md` | Validate integration choices with actual device/client APIs. |
| UI/UX design | Runnable responsive console and OpenCV prototype | Native Android/desktop client implementation and human evaluation. |
| Code and version history | Git repository, Python/Java source, tests, CI, pinned dependencies | Verify remote commit and CI run for each release. |
| Working prototype | Local browser and desktop demos | Hardware liveness demonstration with the deployed model. |
| Pitch presentation | `pitch/index.html` | Team identity, final measured results, rehearsal. |
| Optional demo video | Recording script in `DEMO_AND_SUBMISSION.md` | Record and verify a real 2-5 minute demo; no recording is claimed here. |
| Test data and results | Attributed NASA static fixture, synthetic tests, validation report, private dataset evaluator | Review landmark-model distribution terms; collect consented test subjects/attacks. |
| API and installation instructions | `README.md`, `API.md`, OpenAPI, dependency lock | Clean-machine native target setup. |
| Student credentials, cloud links, submission email | User-controlled external submission | Do not put student IDs or credentials in the public repository. |

The unresolved native integration and physical attack evaluation are mandatory gaps. Bonus coverage does not compensate for them. A test count, generic adapter, successful model load, or returned JPEG cannot close those gaps.
