# Resume checkpoint

The current branch is `new/hackathon-quality`. Resolve its exact commit with
`git rev-parse HEAD`; the predecessor was `30686fb13db650fb4a58dbfcc90dc2a8a3c8e38d`.
Keep new commits local, with `[skip ci]` in commit messages. The user's latest
scope excludes GitHub publication and the demo. Do not push or change visibility.
Do not run GitHub Actions because the user's allowance is exhausted.

Read `RELIABILITY_PLAN.md` before making more inference changes. The user asked
for research first, a written plan second, then implementation. That sequence
has been followed for the session evidence gate and optional MN3 profile.

Protected: do not add or change the untracked root `ps4.pdf` and
`evaluation criteria.pdf`. Do not publish the user's screenshots, camera images
or private diagnostic files. No physical-trial images were saved by diagnostics.

Validation: 151 tests passed; simulator UI settling/exit smoke passed. Previous
141-test source archive also passed after extraction. The new model uses a
verified official download and retained MIT license. Models remain uncalibrated
for this camera and population. There is still no completed physical native
MOSIP client demonstration.

Local artifacts/runtime: `D:\CodexWork\native-face-pad-20261018` and Python
`D:\CodexWork\face-pad-clean-20261018\Scripts\python.exe`. Keep installs,
archives and temporary files on D because C has little free space. The launcher
is `artifacts\START-LAPTOP-PHYSICAL-TRIAL.cmd`; verify it points to a clean
extraction of the latest committed release rather than a patched old extraction.

Next evidence work: evaluate labelled independent live/physical-attack sessions
using the fixed model and complete session policy. Do not lower thresholds,
switch models based on higher live scores, or call score-double tests physical
accuracy. The user does not want another request to retry while the software is
being changed. Native Java/Android policy changes require separate work and tests.

Latest local work adds action-count progress, explicit restart recovery, numeric score audit fields and validated offline policy persistence. The user now excludes GitHub publication and the demo. Do not push new commits or change visibility. See LOCAL_DELIVERY_STATUS.md and the retained physical webcam observations. The remote baseline remains 2ac8c92.


Native continuation: read NATIVE_DETECTOR_PLAN.md. Portable YuNet and shared-face
frame wiring passed real model parity checks. Bounded native PAD evidence and
recovery passed the Java action checks. Native sources/resources were synced to
three prepared D: checkouts. Full new APK/controller validation is not complete.
Host C: exhaustion and Windows paging-file exhaustion blocked later checks.
Do not repeat resource-heavy builds until headroom is available. Do not claim
old APKs contain this milestone. Model files and Git storage are now junctions
to workspace-models and workspace-git under the D: artifact root. The old broken
.venv is preserved there as preserved-broken-workspace-venv. No remote push.


Latest validation after resource recovery: all 165 Python tests passed in 16.51
seconds. The completion-transition test now uses explicit controlled inputs,
instead of relying on a real detector and timed gate inside a fixed frame loop.
The native action test also passed after recompiling the final source. Desktop
controller checks subsequently passed on the new detector. Blank ISO captures
were rejected before storage, operator/supervisor rejection made zero matcher
calls, and a completed action double could not override the recorded portrait's
PAD attack verdict. This fixture no longer exercises positive matcher acceptance.
See native-yunet-controller-check.json. Earlier resource failures remain in logs;
Android rebuilds, physical attack accuracy and live client UI remain unverified.


Timed pass in progress until 19:23 IST on 19 October. Latest working Python
source passes 186 tests in a fresh D: copy and the original workspace with
PYTHONPYCACHEPREFIX on D:. Root default-cache runs had early collection/runtime
interruptions; preserve logs and use a fresh cache. The source regression was
not reproduced with fresh cache locations. scripts/check_local.ps1 provides
isolated caches/logs and a machine-readable result; full wrapper run is pending.
Native clock rollback, arbitrary clock origins, two-second instruction reading,
action counts, bounded JPEG/PNG/JP2/J2K preflight and cached workflow policies are
implemented. Pure Java header/policy/session checks and actual Java model checks
passed. Patched desktop controllers compiled with --release 11 on JDK 21 and
passed role-specific cache and PAD-veto checks. Both updated patches prepared
from clean pinned upstream clones. See NATIVE_POLICY.md and ENCODED_IMAGE_BOUNDS.md.
The reference camera SBI and test APK rebuilt successfully with the new detector;
subsequent JP2 guard changes need its final incremental rebuild. Android client
build failed spawning Flutter/Git under Windows paging-file pressure. Retry with
one JVM, bounded compiler/heap and the previous two-ABI Flutter target set before
considering a private SDK wrapper. Do not modify the installed Flutter SDK.
A Java 11 toolchain was located at C:/CodexTools/temurin-11.0.32/jdk-11.0.32.1+1;
Maven is at C:/CodexTools/apache-maven-3.9.16. Prefer it for the final desktop
reactor build/check rather than assuming Java 11 is unavailable.
Offline updater now rejects an empty saved ceiling and stages/fsyncs the version
record before replacement. Six updater tests passed. Offline imports no longer
load vision libraries eagerly. Keep all artifacts/temp/cache on D:. No pushes,
GitHub Actions, physical phone actions, user camera requests or demo work.

## Publication checkpoint, 19 October 2026

The user subsequently authorized pushing this work and merging into the default
branch. The freshly fetched default is main at 2ac8c92. This supersedes the
previous local-only instruction; demo work and visibility changes remain excluded.

The latest five-module desktop reactor build passed using Java 11 in 58.739
seconds, including the preview JPEG preflight and revised preparation prompts.
The final portable native action check passed after recompiling current source.
The new prepared-source verifier passed 13 unit tests. Both Android prepared
checkouts passed generated-source/assets and patch verification, at 30 camera-SBI
and 27 registration-client files. This is not a final APK rebuild or execution.
The desktop verifier matched 21 generated files, but reverse patch checking
failed against the prepared POM's build-only changes. That check remains FAIL.

The earlier full Python source runs passed 186 tests. The final wrapper attempt
failed during collection inside Python/pytest with SystemError before tests ran.
Its FAIL report is retained under D:/CodexWork/native-face-pad-20261018/push-regression.
The 13 new verifier tests passed separately. Do not report 199 passing together.

Final Android APK rebuilds, native JavaFX lifecycle checks, physical attacks,
live official-client workflows, real identity matching and L1/vendor validation
are still pending. Parallel agents were interrupted by the account usage limit.
The successful desktop build log is desktop-final-jdk11-reactor-build.log under
the same D: artifact root. The laptop launcher still targets the older f5a678d
source extraction; it has not been retargeted to the publication checkpoint.
The original supplied PDFs and private camera evidence remain excluded from Git.

## Delivery completion checkpoint, 19 October 2026 (Evening)

This checkpoint establishes the successful completion and verification of the full Python test suite, native desktop validation, reference camera-SBI APK rebuild, and Android registration client APK rebuild under explicit resource constraints.

1. **Full Python Suite Execution (199 Tests Passing)**:
   - Command: `scripts/check_local.ps1` with explicit `-SourceDirectory` targeting the repository checkout, Python runtime `D:/CodexWork/face-pad-clean-20261018/Scripts/python.exe`, and output directory `D:/CodexWork/native-face-pad-20261018/full-suite-run`.
   - Result: All 199 tests passed (186 core + 13 native preparation) in 33.82s (0 failures, 0 errors, 0 skipped).
   - Pytest collection diagnosis: The previous `SystemError` during pytest collection at commit `f10cbb2` was caused by AST parsing traceback formatting during an interrupted collection in a shared cache. Executing with isolated pycache on D: (`PYTHONPYCACHEPREFIX=D:/CodexWork/native-face-pad-20261018/full-suite-run/pycache`) and `-p no:cacheprovider` ran cleanly and reproducibly.
   - Retained report: `D:/CodexWork/native-face-pad-20261018/full-suite-run/20261019T142245795Z-357159ff/result.json`.

2. **Native Desktop Verification & Lifecycle Check**:
   - Resolved POM reverse patch-check discrepancy: normalized `integrations/native/desktop.patch` and `android.patch` line endings to LF on disk.
   - `scripts/verify_native_preparation.py` verified all three checkouts:
     - Desktop: 21 prepared files; 0 mismatches; patch present=True.
     - Android: 27 prepared files; 0 mismatches; patch present=True.
     - Camera-SBI: 30 prepared files; 0 mismatches; patch present=True.
   - Refined `integrations/native/tests/DesktopStreamLifecycleCheck.java`: updated guidance assertion to accept initial bounded PAD session prompt (`"Checking liveness"` or `"Look straight"`) for the synthetic blank frame fixture.
   - Executed `scripts/check_native_desktop.py` with Java 11 (`C:/CodexTools/temurin-11.0.32/jdk-11.0.32.1+1`), `--preview`, and classpath file `D:/CodexWork/native-face-pad-20261018/desktop-classpath.txt`.
   - Both `DesktopControllerRejectionCheck` and `DesktopStreamLifecycleCheck` passed cleanly.
   - Retained report: `D:/CodexWork/native-face-pad-20261018/desktop-publication-check/report.json`.

3. **Reference Camera SBI Rebuild & Verification**:
   - Rebuilt reference camera SBI debug APK and test APK using isolated Java 21 (`D:/CodexWork/native-face-pad-20261018/jbr-native-check/bin/java.exe`) and single-JVM bounded settings in 30 seconds.
   - Verified APK ZIP integrity, model hashes (`minifasnet_v2.onnx`, `facemesh_v2.onnx`, `face_detection_yunet_2023mar.onnx`), runtime notices, ABI (`x86_64`), and v2 APK signature with `apksigner`.
   - Distinct artifacts archived to `D:/CodexWork/native-face-pad-20261018/artifacts/camera-sbi-rebuilt-20261019`:
     - `camera-sbi-debug.apk`: 94,316,807 bytes, SHA-256 `676ecf0a089b7835730b54c1cd616fc9c75ac3f32662dd6d6835b8ef2844f145`.
     - `camera-sbi-androidTest.apk`: 1,879,121 bytes, SHA-256 `c3a541dbae8bc2e019db931dda996aed8bceb57dbe6d47cbfbda3760a83e96e6`.
     - Verification report: `verification.json`.

4. **Android Registration Client Rebuild & Verification**:
   - Addressed Jetifier heap exhaustion on large modern binaries by adding `opencv`, `onnxruntime`, and Flutter engine debug JARs (`x86_64_debug.*`, `arm64_v8a_debug.*`, `x86_debug.*`, `armeabi_v7a_debug.*`, `flutter_embedding_debug.*`, `io.flutter.*`) to `-Pandroid.jetifier.ignorelist`.
   - Resolved D8 dex merging out-of-memory error during `:app:mergeExtDexDebug` by removing aggressive GC heap shrinking parameters (`-XX:MinHeapFreeRatio=5 -XX:MaxHeapFreeRatio=15`) and setting bounded heap to 1536 MB (`-Xmx1536m`), matching the project's `gradle.properties` configuration.
   - Full build (`:app:assembleDebug` and `:app:assembleDebugAndroidTest`) succeeded in 8m 54s (448 actionable tasks: 108 executed, 340 up-to-date).
   - Verified ZIP integrity, exact model hashes, runtime notices, ABI splits (`x86_64` and `arm64-v8a`), and v2 APK signatures with `apksigner`.
   - Distinct artifacts archived to `D:/CodexWork/native-face-pad-20261018/artifacts/registration-client-rebuilt-20261019`:
     - `app-x86_64-debug.apk`: 261,021,276 bytes, SHA-256 `bdc5e259a4a3f997393a1de04e8774dec1f9e4a5a031024439aa4a630ef4c2be`.
     - `app-arm64-v8a-debug.apk`: 223,185,249 bytes, SHA-256 `55c8a1ab4cbef8810bf1ad9384e09dd650d2074046c9575589cbf0bad547d649`.
     - `app-debug-androidTest.apk`: 2,802,864 bytes, SHA-256 `408cbffb802be92002ce452bf13acbdb19d5acfd852745d047664baf95a19bc8`.
     - Verification report: `verification.json`.

5. **Test Inventory and Device Boundaries**:
   - Verified test count in source:
     - Registration client test sources: 14 tests (6 in `AndroidActiveEvidenceTest`, 8 in `NativePadAcceptanceTest`).
     - Camera-SBI test sources: 8 tests (6 in `CameraOwnerPadTest`, 2 in `PhysicalPadHarnessTest`).
   - No test emulator was running during build or verification (`adb devices` was empty). Per explicit safety instructions, no emulator was launched and no physical phone operations were performed.

6. **Evidence Boundaries**:
   - Checks are conducted with injected test doubles, synthetic images, and unit/integration harnesses.
   - Offline tests do not attest to live camera physical attack accuracy or production certificate authority chains.

7. **Release Packaging, Clean Package Extraction & Launcher Retargeting**:
   - Packaged committed release tree using `scripts/package_release.py`:
     - Archive: `D:/CodexWork/native-face-pad-20261018/artifacts/face-liveness-source-70f02e7.zip`
     - SHA-256: `14aa996b47d94c4e7e6baf1c9ea903b7942a4f1d09215326139920e4c1a474f4`
     - 201 files verified against `RELEASE_MANIFEST.json`.
   - Extracted to fresh directory `D:/CodexWork/native-face-pad-20261018/source-check-70f02e7` and verified all 201 file hashes against `RELEASE_MANIFEST.json`.
   - Scoped PowerShell native CLI error action handling in `scripts/check_local.ps1` to prevent non-fatal stderr warnings (e.g. OpenCV libpng sRGB profile warnings) from aborting the pipeline.
   - Executed full 199-test suite against the freshly extracted source package: all 199 tests passed in 24.87s (`D:/CodexWork/native-face-pad-20261018/extracted-check-suite-verified/20261019T160055551Z-287a7ea0/result.json`).
   - Retargeted launcher `D:/CodexWork/native-face-pad-20261018/artifacts/START-LAPTOP-PHYSICAL-TRIAL.cmd` to `source-check-70f02e7`, added `PYTHONPYCACHEPREFIX=D:\CodexWork\native-face-pad-20261018\pycache`, preserved strict ONNX mode, and validated via `--check` flag (exit code 0, without opening physical camera).

8. **Native Policy Extension & Release Package 4485441**:
   - Implemented configurable `actionCount` (1..4), `timeoutSeconds` (5..60), and `maxRetries` (0..5) with fail-closed bounds checking in `NativePadPolicy.java`.
   - Added test coverage in `NativePadPolicyCheck.java` for defaults, role-based overrides, alternate keys (`mosip.facepad.<role>.action.count`, `timeout_seconds`, `max_retries`), and strict rejection of out-of-bounds/malformed values.
   - Re-verified landmark/action pipeline (`scripts/check_native_landmarks.py` passed all stages).
   - Synchronized `NativePadPolicy.java` across prepared checkouts (`desktop`, `android`, `camera-sbi`).
   - Re-verified all 3 checkouts via `scripts/verify_native_preparation.py`: 0 mismatches, patch present=True.
   - Updated documentation in `docs/NATIVE_POLICY.md`, `docs/REQUIREMENTS_MATRIX.md`, and `config/native-policy.example.properties`.
   - Full Python test suite passed: 199 passed in 46.34s on repository checkout (`D:/CodexWork/native-face-pad-20261018/tmp/local-check-policy/20261019T174246758Z-d1f9fbdb/result.json`).
   - Packaged release archive `D:/CodexWork/native-face-pad-20261018/artifacts/face-liveness-source-4485441.zip` (SHA-256: `641b1713a15708cfbb606bae33c59905a16cd628691fb11a7d2857e9ad64e64f`).
   - Extracted to fresh directory `D:/CodexWork/native-face-pad-20261018/source-check-4485441` and verified all 201 file hashes against `RELEASE_MANIFEST.json`.
   - Executed full 199-test suite against the freshly extracted source package: all 199 tests passed in 27.39s (`D:/CodexWork/native-face-pad-20261018/extracted-check-suite-4485441/20261019T174650451Z-dc2fb848/result.json`).
   - Retargeted launcher `D:/CodexWork/native-face-pad-20261018/artifacts/START-LAPTOP-PHYSICAL-TRIAL.cmd` to `source-check-4485441` and verified via `--check` flag (exit code 0).
   - Both `origin/new/hackathon-quality` and `origin/main` synchronized at commit `44854414c43cc3dcbfc52c1d2688ab978c5419d5`.



## Latest continuation, 20 October

Resume from the latest main after fetching. Code milestone de68e6f actually wires
the policy action count, timeout and retry limit into frame sessions and checks
Android signed minimum counts. Do not regress this into parser-only support.
All three native source copies and patches verified. Java11 desktop reactor,
controller and JavaFX checks passed. Both Android app/test builds passed; current
API34 camera-disabled instrumentation passed 17 registration and eight camera
tests. All five APK signatures and app models/notices/ZIP integrity verified.
Emulator was shut down; no phone actions. Current source tests:199 PASS; clean
205-file code package de68e6f:199 PASS16.68sec. Launcher retargeted and --checkPASS.
Current APKs: D:/CodexWork/native-face-pad-20261018/artifacts/native-final-20261020.
Combined summary.json binds source fingerprints, artifact hashes and test logs.
Retained public records: integrations/native/evidence/policy-session-20261020.
See LOCAL_DELIVERY_STATUS.md for the current consolidated state and remaining
physical, official-client, production trust and native configuration gaps.
Publication/merge authorized; no Actions, public visibility changes or demo.
