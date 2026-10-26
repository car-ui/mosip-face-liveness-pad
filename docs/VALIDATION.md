# Validation evidence

Latest CI update, 26 October: commit `450f877` passed Ubuntu and Windows Python,
evidence-integrity, portable Java and actual Java/ONNX checks. The updated full
Python suite passed 227 tests locally. Current camera-SBI source built and
passed camera-disabled instrumentation in
[run 40284447283](https://github.com/car-ui/mosip-face-liveness-pad/actions/runs/40284447283).
The earlier retained reports below remain historical evidence; the current
Registration Client APK and live physical acceptance are still outstanding.

This report summarizes the latest retained checks for the implemented code milestone `de68e6f`. The repository HEAD also includes later evidence/documentation commits. Results below are software and emulator checks; they are not measurements of physical attack accuracy or successful real-person action completion.

On 23 October 2026, a fresh run of the full current working-tree Python suite
passed **225 tests** (32.23 seconds wall time; 32.155 seconds reported by
pytest) on the bundled Python 3.12 runtime with the exact packages from
`requirements.lock.txt` installed under ignored `tmp/`. The run had one
Starlette/httpx deprecation warning and includes the current evaluation,
private-manifest integrity, threshold-selection and interoperability tests.
The sanitized JUnit report is retained at
[`integrations/native/evidence/python-suite-20261023.xml`](../integrations/native/evidence/python-suite-20261023.xml).
The 199-pass results below are retained earlier runs and clean-package checks.

## Recorded checks

| Area | Result | What it establishes |
|---|---|---|
| Python regression suite | 225 passed in 32.23 seconds wall time (32.155 seconds pytest time) on the current working tree. JUnit report: [`python-suite-20261023.xml`](../integrations/native/evidence/python-suite-20261023.xml). Earlier, a clean source-package extraction verified 205 file hashes and passed 199 tests in 16.68 seconds. | Regression coverage for prototype policy, API, model contracts, device abstractions, security properties and packaging checks. Injected inputs and fixtures do not establish human or attack accuracy. |
| Native Desktop build | Five-module Java 11 reactor build passed. Actual patched controller rejection and JavaFX preview/lifecycle checks passed. | The pinned Desktop source compiles and its acceptance checkpoints reject controlled synthetic inputs before storage/matching. It does not establish a full live camera-to-client workflow. |
| Android Registration Client | Split app and test APK build passed; 17 instrumentation tests passed on the API 34 `NATIVE_PAD_API34` emulator. | Native model execution, signed fixture parsing, one-use storage acceptance, and policy-bound evidence checks on an emulator with cameras disabled. |
| Reference camera SBI | App and test APK build passed; eight instrumentation tests passed on the same camera-disabled API 34 emulator. | Native model behavior, static-frame rejection, ISO/image binding, metadata handling, and no-camera failure. No successful human action is represented. |
| Native package and source evidence | All five APK signatures, ZIP integrity, ABI/model/license checks passed. All three prepared client checkouts matched their expected files and patches; the evidence validator passed 26 checksum checks. | Reproducibility and artifact integrity for the recorded package set. It does not establish production signing trust or physical-device compatibility. |

Raw native logs, package checksums, and source fingerprints are retained in [`integrations/native/evidence/policy-session-20261020`](../integrations/native/evidence/policy-session-20261020). The consolidated native report is [`integrations/native/validation.json`](../integrations/native/validation.json). The exact scope and remaining requirements are in the [requirement matrix](REQUIREMENTS_MATRIX.md) and [evaluation protocol](EVALUATION_PROTOCOL.md).

## Focused current-source checks

On 22 October, the Java 8 policy/session sources compiled with `javac --release 8`;
`NativePadPolicyCheck` and `NativeActiveSessionCheck` passed. A synthetic
camera-evidence fixture also completed a configured three-blink session and
checked the resulting count, timeout and retry claims. Stub PAD/landmark types
were used for this control-flow check, so it does not validate ONNX, OpenCV or a
real camera.

The updated cached-policy to SBI `customOpts` serializer and camera request
reader also compiled with Java 8. `NativePadPolicyCheck` and
`CameraSbiRequestPolicyCheck` passed the complete policy round-trip, typed
intent mapping, defaults, partial/malformed-policy rejection and disabled
policy checks using an in-memory request DTO. The test does not execute the
patched official Registration Client or a built camera SBI.

These two Java checks were rerun against the current working-tree sources on
23 October; both passed with `javac --release 8`.

The PAD evaluator now consumes a private master manifest with development and
test rows. `scripts/pad_manifest.py` requires both classes in both splits and
checks that participant and physical attack-source pseudonyms do not cross the
split boundary. It also rejects duplicate clips and path traversal. Evaluation
reports contain neither video paths nor group pseudonyms, and the threshold
selector requires the passed split-audit marker. The manifest-integrity and
threshold-provenance regressions are included in the 225-test suite. No clip
data was available to calculate real APCER or BPCER.

The Android Registration Client patch was prepared from a clean checkout at
upstream commit `8f4643a694f3b5e66e0491f077a8630ab5667658`; the retained
[preparation report](../integrations/native/evidence/android-prepared-20261023.json)
verifies the exact patch and copied source/assets. The pinned patch sets the
cached resident/operator policy on the outgoing face `CaptureRequest.customOpts`.
Direct PAD checkpoint rejections display a generic retry message and return a
sanitized Flutter error; face-capture SBI failures also use generic retry
guidance. Detailed exceptions remain in internal logs. The reference SBI patch was checked against
`d1ec22a542294b798f5b9c5bb97428deabb2064b`; preparation applied the parser
normalization from standard JSON object to the pinned DAO's list-of-maps field
and copied the current sources and tests. This confirms patch applicability and
source preparation only; neither APK was rebuilt.

An earlier pinned Desktop client source build installed through the five
reactor modules required by `registration-client`, with Maven tests skipped.
On 23 October, the updated patch was applied to a clean checkout at the exact
upstream commit and the five-module reactor compiled through `registration-client`.
The builds used JDK 21 and a command-line Lombok 1.18.30 override because the
workspace does not have JDK 11 and pinned Lombok 1.18.16 is not a reliable JDK
21 compiler dependency. No pinned source or POM was changed for this override.
The latest compile skipped the Git metadata plugin because its inherited
`.git` path points inside child modules. The Desktop controller harness from
the earlier build compiled, then the JVM crashed inside `onnxruntime.dll` while
creating `OrtEnvironment` on this Windows/JDK 21 host. The earlier Java 11
controller and preview results remain the only passing runtime-harness
evidence; the latest compile does not establish current native PAD runtime
behavior or live camera/UI acceptance.

Python 3.12 syntax compilation passed for the changed evaluator, threshold
selector, provider benchmark and device-contract files. An earlier focused
device-capability import check used a minimal OpenCV shim; the later full pytest
run passed with the locked dependencies, and the separate interoperability CLI
ran with OpenCV installed. Neither validates physical vendor devices. `git diff --check` and
`git apply --stat integrations/native/camera-sbi.patch` and `git apply --check`
against the exact camera-SBI checkout also passed.

The provider benchmark ran on 23 October with ONNX Runtime 1.31.0. CPU and
Azure providers returned identical outputs (maximum absolute difference 0.0).
The profile assigned all 14,300 nodes to CPU and none to Azure, so no
accelerated execution was observed. CPU p50/p95 were 1.5871/2.1148 ms; Azure
provider-request p50/p95 were 6.9766/23.8105 ms, including CPU fallback. The
raw report and profile are retained under
[`integrations/native/evidence/provider-benchmark-20261023`](../integrations/native/evidence/provider-benchmark-20261023).
This desktop result does not measure Android GPU/NPU/NNAPI or prove hardware
acceleration.

The focused evaluation, interoperability and usability-protocol selection
passed 14 tests on 23 October. The capability CLI report is retained at
[`integrations/native/evidence/interoperability-20261023.json`](../integrations/native/evidence/interoperability-20261023.json).
It validates the webcam interface contract, mock adapter and two simulated
vendor adapters; it does not open the physical webcam or establish real vendor
support.

The current working-tree source archive was generated and independently
verified by `scripts/package_release.py --worktree`; its manifest covers the
included files and the ZIP checksum is reported by the script. This does not
package or validate native application binaries.

This working folder has no system Gradle, Android SDK or `adb`. A temporary
Maven 3.9.9 distribution was used for the successful Desktop source build. The
updated Android patches could not be rebuilt here, and retained APK evidence is
for the earlier source milestone.

## Automated coverage

The Python suite includes regressions for PAD attack/error veto during active verification, mandatory operator/supervisor actions, face loss, terminal rejection, invalid frame data, detector/model failures, concurrency, preview non-mutation, policy validation, secure model updates, audit redaction, retry/timeout behavior, and explicit simulator labeling. Java and native tests additionally exercise session/role binding, replay rejection, exact-image digest binding, one-use acceptance, signed transaction evidence, malformed policy rejection, and bounded image/frame parsing.

Model conversion and runtime checks compare packaged ONNX behavior with declared reference outputs. These are model/runtime compatibility checks, not bona fide-versus-attack accuracy measurements. Historical figures are retained in the model benchmark and research notes with their narrower scope.

## Not established by these checks

- Physical L0/L1 device integration, multiple real vendors, or signed hardware attestation.
- Representative, consented print, display, mask, or injection evaluation with frozen thresholds and held-out subjects.
- Successful live action detection in the Desktop or Android client, full camera-to-storage UI flows, or real identity matching.
- Production certificate-chain provisioning/trust, formal SBI conformance, ISO image conformance, or authenticated online policy synchronization.
- Human accessibility/usability, sustained physical Android latency, RAM, power or thermal behavior.
- A recorded demo video or final external submission artifacts.

See [`LOCAL_DELIVERY_STATUS.md`](LOCAL_DELIVERY_STATUS.md) for the latest delivery summary and [`DEMO_AND_SUBMISSION.md`](DEMO_AND_SUBMISSION.md) for the outstanding submission work.
