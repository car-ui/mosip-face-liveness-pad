# Local delivery status

19 October 2026. The user requested completion work with GitHub publication and
the demonstration left out. New changes are saved locally. Existing remote
visibility and published refs are not changed by this delivery.

## Completed in this pass

- Both Python interfaces now show completed-action counts instead of a
  per-action percentage that looked like overall verification progress.
- PAD-related restarts explicitly clear action credit, create an audit event
  and hold a short recovery interval before new instructions. PAD continues
  running during recovery. The policy does not retain invalid action credit.
- Main action instructions remain stable; browser secondary feedback has reading
  time. Camera/model scores remain separate from completed-action progress.
- Numeric score observations survive audit filtering under explicit numeric
  field names; raw image/frame buffers remain blocked.
- Optional validated offline policy files work in the desktop and service.
  Authenticated API changes are atomically saved before the running policy is
  changed. An example configuration and failure-path tests are included.
- The browser/service default trial deadline is 45 seconds to allow more room
  for two actions and preparation. Explicit request bounds remain 2 to 60 seconds.
- Actual laptop observations are summarized without images or subject IDs in
  `physical-webcam-observations.json`. Of three recorded trials, two ended in
  accepted prototype capture with completed actions; one was rejected. Some
  sequences restarted. This is not a population accuracy estimate.

## Validation

The workspace suite passed 165 tests in 31.71 seconds. Console JavaScript passed
Node syntax checking. A rendered static-fixture UI was visually inspected with
one of two actions completed. The native evidence validator passed 24 checksums
and matched six Android measurement logs. That last check establishes retained
evidence integrity, not new native execution or hardware validation. Fresh
committed-source package verification is performed at delivery.

## Requirements that remain genuinely open

The remaining gaps cannot be marked complete by adding prototype features:

1. Independent live and physical print/display/mask trials, with frozen settings,
   held-out subjects/sources, attack-group errors and nonresponse counts. There
   is still an apparent live-person rejection in the observed laptop trials.
2. A complete official desktop/Android client camera-to-acceptance run, including
   real identity matching where required. The accepted Python prototype trial
   does not establish official operator or supervisor authentication.
3. Physical Android and real L1/multiple-vendor integrations, production device
   certificate trust and actual vendor streaming/format compatibility. Current
   signed acceptance tests use declared crypto/repository fixtures.
4. Native platform adoption and validation of newer prototype detector/session
   policies, and integration with MOSIP's configuration framework. The Python
   policy-file implementation does not complete those native software tasks.
   Inspection confirmed the pinned desktop OpenCV 4.5.3 JAR does not contain
   `FaceDetectorYN`. The Python YuNet adapter therefore cannot be copied into
   the native client. Adopting it requires a native decoder or a validated
   dependency upgrade and rebuilt platform artifacts.

The source package, regression checks and research evidence are local reviewable
deliverables. The full mandatory hackathon scope is not declared complete.
Publication, repository visibility changes, a public release, demo recording and
external submission are excluded from this pass.

## Subsequent native milestone

Portable YuNet detection and bounded session PAD observations are now connected
in native source. The PAD decision and action landmark crop share the same face
box. All platform resource preparation includes the detector and its MIT notice.
See NATIVE_DETECTOR_PLAN.md for executed checks and remaining build limitations.
Native configuration framework adoption, APK rebuilds and physical native tests
remain open. Retained APKs must not be described as containing this new source.

The later validation attempt hit host resource exhaustion. Its result was 159
passes and six failures, followed by an OpenCV import failure from an exhausted
Windows paging file. The earlier 165-pass result remains historical evidence,
not a claim that this later run passed. Desktop controller validation was also
blocked by memory allocation. New source is saved locally with these limits.

To preserve disk headroom, the project model directory and Git storage now use
Windows directory junctions to D:/CodexWork/native-face-pad-20261018/workspace-models
and workspace-git. Paths in the checkout still work. The unused broken .venv was
preserved on D: as preserved-broken-workspace-venv. The supported launcher uses
the separate working D: Python environment. Repository connectivity was checked.


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

