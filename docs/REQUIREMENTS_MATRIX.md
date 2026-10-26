# Problem 04 requirement evidence

Reviewed against the supplied [`04_Face_Liveness_Detection_and_Presentation.pdf`](../04_Face_Liveness_Detection_and_Presentation.pdf), including mandatory tasks on pages 6-9, bonus and good-to-have tasks on page 10, and deliverables on pages 11-12. The supplied [evaluation criteria](../Evaluation_Criteria_MOSIP_Decode_2026.pdf) assign 40/40/10/10 to functionality, quality, UX, and presentation. Status describes available evidence, not a jury score.

`Implemented` means code with automated verification at the stated scope. `Partial` means a prototype, simulator, or adapter exists but a required integration or real-world validation is missing. `Unverified` means this repository does not establish the requirement.

Across the 27 mandatory, good-to-have and bonus items, 16 are implemented at
their stated prototype scope and 11 remain partial. This is not a claim that
all 27 are fully accepted in production; the remaining physical-device,
cross-vendor, live-client and submission evidence is listed below.
The retained October 20 native build reports predate evidence version 2 and
describe the earlier milestone. Current camera-SBI source has since built and
passed camera-disabled instrumentation in CI run 40284447283. The Registration
Client's current source still needs a fresh APK and live integration acceptance.

## Mandatory tasks

| Requirement | Status and evidence | Remaining acceptance evidence |
|---|---|---|
| 1. L0/L1 device integration | Partial. Webcam adapter, common BGR frame interface, simulator scenarios, explicit capability discovery, disconnect handling. `tests/test_mock_device.py`, `tests/test_mds.py`. | Physical vendor L1 SDK, signed frame/attestation verification, device format coverage, at least two real vendors. Simulated L1 does not establish hardware integration. |
| 2. Passive liveness | Partial. Local ONNX inference and research heuristics, declared preprocessing, threshold comparisons, temporal decision buffer, model-error rejection. Development-only threshold selection enforces a predeclared APCER ceiling, minimum class count and the runtime-supported 0.46-0.99 threshold range; the master-manifest loader requires both splits, audits participant and attack-source separation, and prevents path escape. `scripts/evaluate_dataset.py`, `scripts/pad_manifest.py`, `scripts/select_pad_threshold.py`, `tests/test_passive_pad.py`, `tests/test_security_regressions.py`, `tests/test_evaluation.py`, `tests/test_pad_manifest.py`. | Consented independent bona fide/attack development and test sets, representative subjects/devices/lighting, threshold freeze, offline camera E2E. Tooling cannot substitute for collected data. |
| 3. Presentation attack detection | Partial. PAD gates passive and active acceptance; rejection returns no biometric payload. Strict ONNX mode cannot silently fall back after runtime errors. | Real printed-photo, screen-replay, 3D-mask, and injection tests as applicable; ISO/IEC 30107 evaluation protocol execution. Heuristic fixture rejection is not attack accuracy. |
| 4. Active liveness | Implemented at prototype scope. Random action selection, automatic prompts, temporal blink/smile/pose detection, per-frame PAD re-evaluation, action invalidation on face loss, multi-challenge progression. The recorded earlier native build bound Camera2 ISO to its own challenge and supplied a custom signed extension; eight camera and 17 client emulator checks ran with cameras disabled on API 34. Current camera-SBI source has CI build/instrumentation evidence; the Registration Client still needs a fresh APK. `tests/test_active_liveness.py`, security regressions and `docs/CAMERA_SBI_INTEGRATION.md`. | Two user-observed L0 prototype trials completed LEFT/BLINK and RIGHT/LEFT; a preceding trial was rejected. See `physical-webcam-observations.json`. Broader subjects/actions, accessibility, adaptive replay and independent error rates remain unverified. |
| 5. Resident registration | Partial. Recorded pinned desktop and Android builds rejected a synthetic blank ISO before capture storage. Android emulator tests executed ONNX; an additional actual-parser/onboarding-API test accepted signed fixture evidence once and rejected replay before a second write. Its RSA key, trust provider, completed-action metadata and repositories are fixtures. The current Registration Client source still needs a fresh APK. `integrations/native/validation.json`. | Complete native camera/UI/packet-generation E2E, live stream/challenge linkage, physical Android hardware and physical attacks. |
| 6. Operator authentication | Partial. The pinned desktop operator-authentication screen now runs a role-specific active preview and passes its one-use, exact-JPEG proof to the checkpoint before the identity matcher. The Login face method also passes a required capture gate into `SessionContext`; the service rejects calls that omit the gate. The updated five-module desktop reactor compiles with Maven tests skipped. | Live camera/UI verification, real SBI preview/final-capture compatibility, live action accuracy, successful identity matching and offline E2E remain unverified. JPEG2000 proof is blocked. |
| 7. Supervisor authentication | Partial. The EOD supervisor screen now uses the supervisor policy and active-preview checkpoint; the login face method chooses supervisor policy from the active user role. The updated five-module desktop reactor compiles with Maven tests skipped. | Live supervisor camera/UI verification, real identity matching and offline E2E remain unverified. Supervisor bypass auditing and successful live actions remain unverified. |
| 8. Configuration | Partial. Per-workflow thresholds, active enablement, required counts, supported challenge pools, timeout, retry limit, global liveness enablement, configurable guidance, enum/range validation. Disabled liveness never produces a verified capture. | Optional validated offline policy files and atomic authenticated API persistence exist in the Python interfaces. Desktop sessions enforce all parsed settings. Android version 2 evidence binds ordered action types and session timing to the exact consumed image; the client checks them against current policy after signature verification. `NativePadPolicy.toSbiCustomOptions()` serializes the cached workflow policy; the pinned Android client attaches it to face `CaptureRequest.customOpts`. The camera SBI converts the standard object form to its pinned DAO list-of-maps DTO and validates the full policy before camera access. Java round-trip/strictness checks pass, and both patches pass preparation against their exact upstream commits. A fresh Registration Client APK and end-to-end stricter-policy update/rejection checks remain. Arbitrary action families, guidance localization and online synchronization proof remain pending. See `OFFLINE_POLICY.md`, `NATIVE_POLICY.md` and `CAMERA_SBI_INTEGRATION.md`. |
| 9. Error handling | Implemented at prototype scope. Missing/multiple/poor-quality faces, invalid BGR data, unavailable model, exceptions, disconnect, timeout, retry exhaustion, concurrent requests, invalid configuration. | Real vendor communication faults and recovery, complete hardware/OS matrix. |
| 10. UI/UX | Partial. Live preview, face guide, passive status, automatic active prompt, progress, safe failure messages, retry availability, diagnostics, narrow-screen layout, keyboard focus and live announcements. A ready-to-run task protocol now covers resident/operator/supervisor workflows, screen readers, keyboard use, cancellation, retry comprehension and review gates. | Run the protocol with consented participants on official Desktop/Android screens and physical cameras, then fix and retest findings. |

## Good-to-have tasks

| Requirement | Status and evidence | Limit |
|---|---|---|
| Configurable challenge pools | Implemented through `/configure` and `supported_challenges`. | Pool changes require an authenticated evaluator. Optional offline policy files persist settings. |
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
| Interoperability testing framework | Implemented at prototype scope. A shared capability-contract validator and CLI check the webcam, mock device, and two parameterized simulated vendor adapters; malformed or contradictory security claims fail. `src/devices/interop.py`, `scripts/check_device_interoperability.py`, `tests/test_interoperability.py`. | Physical cross-vendor devices, vendor SDKs, official native-client matrix and trusted L1 signing/tamper validation. |
| Model version management | Implemented model provenance, checksums, signed version metadata, persisted downgrade high-water mark. | Model approval/revocation distribution and multi-process deployment need integration. |
| Secure offline model updates | Implemented Ed25519 verification, manifest/payload integrity, version checks, atomic model replacement, retained rollback ceiling. | Public-key provisioning, revocation, disk-failure testing, and transactional metadata are deployment work. |
| Low-resource Android optimization | Partial. Actual Android ONNX inference, CPU-count-aware thread selection, split APKs, and three fresh-process timing/PSS measurements per build on a one-CPU API 34 emulator. `ANDROID_BENCHMARK.md`. | Physical ARM64 latency/RAM/energy, camera/SBI and full-workflow measurement remain unverified. Whole-process emulator PSS is not incremental model memory. |
| Hardware acceleration | Partial ONNX provider discovery and CPU fallback; `scripts/benchmark_onnx_providers.py` compares deterministic outputs, latency and profile-reported node assignments against CPU. The retained Windows run found exact CPU/Azure parity, but all 14,300 profiled nodes ran on CPU and none on Azure. | Measure GPU/NPU/NNAPI parity and actual node placement on a physical Android target. Provider availability alone does not prove accelerated execution. See `integrations/native/evidence/provider-benchmark-20261023/`. |

## Deliverables and submission

| Deliverable | Available artifact | Remaining work |
|---|---|---|
| Technical design, interfaces, security, sequences | `TECHNICAL_DESIGN.md`, `SEQUENCE_DIAGRAMS.md`, `NATIVE_INTEGRATION.md`, `MODEL_CARD.md` | Validate integration choices with actual device/client APIs. |
| UI/UX design | Runnable responsive console, OpenCV prototype, and workflow diagrams | Live native-client UI acceptance, participant evaluation, and a separate wireframe/mockup export if supplied. |
| Code and version history | Git repository, Python/Java source, tests, CI, pinned dependencies | Verify remote commit and CI run for each release. |
| Working prototype | Local browser and desktop demos | Hardware liveness demonstration with the deployed model. |
| Pitch presentation | `pitch/index.html` | Team identity, final measured results, rehearsal. |
| Required demo video | Recording script in `DEMO_AND_SUBMISSION.md` | The original guide stars "Video Demo*" as mandatory. A typical 2-5 minute recording is missing; earlier optional-video wording was incorrect. |
| Test data and results | Attributed NASA static fixture, model-card license links, synthetic tests, validation report, private dataset evaluator | Collect consented test subjects/attacks and measure native action/PAD accuracy. |
| API and installation instructions | `README.md`, `API.md`, OpenAPI, dependency lock | Clean-machine native target setup. |
| Student credentials, cloud links, submission email | Source repository is public; other submission actions are incomplete | Each student ID upload, other mandatory artifact uploads, team details, and email to MOSIP remain pending. Do not put student IDs or credentials in the public repository. |

The unresolved native integration and physical attack evaluation are mandatory gaps. Bonus coverage does not compensate for them. A test count, generic adapter, successful model load, or returned JPEG cannot close those gaps.
