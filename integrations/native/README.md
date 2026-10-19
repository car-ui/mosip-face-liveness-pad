# Native capture checkpoints

## Current native source, 19 October

The shared source now uses a hash-pinned portable YuNet decoder. PAD and action
landmarks use the same face box. Native sessions collect bounded PAD evidence,
clear action credit on suspect frames, allow reading time, and display action
counts. JPEG/PNG/JP2/J2K dimensions are checked before image allocation. See
[image limits](../../docs/ENCODED_IMAGE_BOUNDS.md).

The adapters read workflow-specific thresholds and active settings from the
host clients' configuration caches. Operator/supervisor proof is bound to its
role and parsed policy. See [native policy keys](../../docs/NATIVE_POLICY.md).
Current desktop controller checks exercise configuration selection, malformed
policy rejection and PAD veto before matching. The recorded portrait is rejected
by the current model/crop, so it does not exercise positive identity matching.
The earlier positive fixture results below describe older builds.

Historical Android APK/instrumentation results below do not validate these new
sources. A new camera-SBI app/test build succeeded; final source/package checks
and the registration-client rebuild are recorded separately. No physical attack
accuracy, production certificate trust or live native UI success is claimed.


This directory adds an offline, in-process PAD checkpoint to pinned MOSIP client sources. It supplements the Python prototype. It does not establish a completed live registration, a live client UI rejection, or physical attack accuracy.

| Client | Upstream | Commit |
| --- | --- | --- |
| Android | `mosip/android-registration-client`, v1.1.1 | `8f4643a694f3b5e66e0491f077a8630ab5667658` |
| Desktop | `mosip/registration-client`, release-1.2.0 | `935306e2fd38bff2803697468e595026b1d18cec` |
| Reference camera SBI | `mosip/android-camera-mds`, deprecated root app | `d1ec22a542294b798f5b9c5bb97428deabb2064b` |

Run `python scripts/prepare_native_clients.py desktop PATH_TO_CLEAN_CHECKOUT`, or use `android` for Android. The preparer checks the exact commit and refuses a dirty checkout. It applies the small caller patch, installs the shared Java engine and platform adapter, and copies the packaged ONNX model and face detector into application resources.

The desktop patch also repairs the existing preview stream reader. Multipart headers are bounded to 16 KB and JPEG payloads to 8 MB. The reader rejects EOF, truncated payloads, duplicate or invalid lengths, and invalid JPEG markers. Resident and onboarding stream availability checks preserve the first byte. Preview updates use the JavaFX thread with one pending update, and an old stream session cannot clear its replacement. Stopping a stream clears cached frame bytes.

## Acceptance paths

Desktop checks resident face and exception-photo candidates in `GenericBiometricsController` before deduplication, registration storage, or the success alert. `BiometricsController` checks operator-onboarding captures. Both checks run in the background capture task before it returns its candidates. `BaseController.captureAndValidateFace` checks operator and supervisor captures before the identity matcher. Android checks `BiometricsDetailsApi.parseRCaptureResponse` after existing SBI signature/transaction validation and before registration or operator-onboarding storage. Rejection completes the Flutter callback with an error and shows a reason.

The engine verifies the model SHA-256, requires exactly one detected face, uses the MiniFASNet 2.7x context crop, raw BGR channels, and the model's live output index. Invalid images, unavailable native libraries, model corruption and inference errors reject the capture. Model scores at or below 0.45 reject as an attack. Scores below 0.85 require active evidence. These are research thresholds, not measured operating points. This checkpoint does not yet provide the prototype's temporal checks, image-quality policy or retries.

The desktop operator/supervisor authentication flow now starts a native active preview from Scan, displays action prompts in its instruction area and passes the same session to the capture checkpoint. A completed proof is valid once for the exact JPEG bytes within two seconds. The actual `BaseController` positive path is checked with injected action geometry and an identity matcher double; mismatched final bytes reject before matching. This is not successful live-person authentication. JPEG2000 candidates cannot use this proof path. Desktop onboarding and other screens without connected evidence remain blocked when active checks are required. Android can consume the custom signed camera-SBI evidence through the transaction-bound extension described below. See [native active-challenge scope](../../docs/NATIVE_ACTIVE_CHALLENGES.md).

Android receives a completed capture URI from a separate SBI app. Adding active challenges requires cooperation with the app that owns that camera session. A recorded capture alone cannot prove a requested action happened during the current challenge. Desktop still needs a real SBI camera run to establish preview/final-candidate compatibility and successful live actions.

The `camera-sbi` target adds a Camera2 capture activity to the pinned reference SBI. It analyzes its own frames and constructs the final ISO from the exact JPEG that completed the challenge. The registration client consumes its active result only after the existing SBI signature, certificate-trust, timestamp and transaction checks, followed by its own PAD check. Persistent one-use transaction records reject replay. Actual parser and onboarding API tests use a temporary RSA fixture key, simulated action metadata and repository doubles. Production PKI and successful human capture remain unverified. See [capture behavior, build steps and evidence limits](../../docs/CAMERA_SBI_INTEGRATION.md).

## Verification

The CPU-count-aware baseline passed five Android instrumentation tests; the earlier landmark build passed six. Its benchmark makes 100 timed inference calls after ten warmups, checks every score against Python, and records process memory. Three fresh processes were measured for both the previous two-thread build and the adaptive one-thread build on the one-CPU emulator. All results and limits are in [the Android benchmark report](../../docs/ANDROID_BENCHMARK.md). This adds an emulator baseline; physical ARM64 execution and energy use remain untested.

Fourteen pure Java stream-framing checks pass, including consecutive parts, fragmented reads, zero-byte reads and malformed inputs. The actual patched upstream `Streamer` also passes consecutive-frame, bounded EOF and disconnect-cleanup checks. The five-module desktop reactor compiles with these changes. These are controlled stream inputs, not a physical camera demonstration.

`tests/DesktopStreamLifecycleCheck.java` also exercises the actual preview worker and JavaFX `ImageView` with a synthetic JPEG. It verifies preview-thread ownership, a defensive copy of cached JPEG bytes, delayed disconnection of a replaced camera, and cache cleanup on stop. It opens no window and uses no camera. This is not the full native registration UI.

After preparing and compiling the desktop reactor, provide its resolved Maven runtime classpath as one line in a text file. Include dependencies from the client and its reactor modules. Run `python scripts/check_native_desktop.py --java-home JAVA_11_HOME --checkout DESKTOP_CHECKOUT --classpath-file RUNTIME_CLASSPATH_FILE --output CHECK_OUTPUT --preview`. The script adds the four reactor class directories, compiles the checks, and retains their logs and a JSON report. Omit `--preview` on a machine without a display, or supply a virtual display on Linux. Maven's `dependency:build-classpath` can produce the dependency classpath after the reactor artifacts have been installed; do not substitute a list of every cached JAR.

The desktop reactor compiled with Java 11 after adding the checkpoints. On this memory-constrained machine only, the upstream compiler's 1 GB initial / 2 GB maximum heap was reduced to 64 MB / 384 MB. That build-only adjustment is not part of the caller patch. The Android app and test APKs also built successfully. Four focused API 34 emulator tests passed in 17.673 seconds, including actual Android ONNX inference and resident/operator-onboarding rejection before storage. The camera was disabled.

The four tests passed again against the separate x86_64 APK in 14.829 seconds. The ARM64 package was built and checked for signature, ZIP integrity, model hash and correct ABI contents; it has not run on physical hardware. Its 219,846,672-byte debug package is 56.31% smaller than the universal package. APK size reduction does not establish Android runtime resource use.

Packages with the additional runtime license notices were rebuilt and verified separately. The updated ARM64 package is 219,852,032 bytes and the x86_64 package is 257,688,059 bytes. Their DEX files, native libraries, model and pre-existing PAD assets exactly match the packages used for emulator verification. The notice-only packages were not rerun on the emulator. Their distinct filenames and checksums are recorded in `validation.json`.

`tests/NativePadEngineCheck.java` executes actual Java ONNX inference and compares a raw input tensor with Python, then checks blank/malformed rejection, invalid tensor rejection and model checksum enforcement. Run it through `python scripts/check_native_engine.py --java-home JAVA_HOME --onnx-jar ONNX_JAR --opencv-jar OPENCV_JAR`. The Python/Java CI matrix also runs it.

`tests/DesktopControllerRejectionCheck.java` converts a synthetic blank JPEG to an ISO face record and checks the registration adapter and the actual patched upstream `BaseController`. Its SBI and identity matcher are explicit test doubles. The operator and supervisor calls must reject before the matcher is called. An optional portrait-fixture argument checks rejection of the attributed static NASA photograph and reports whether its passive score cleared the threshold. The current NASA fixture does not clear that threshold after the native image conversion. This check therefore does not establish rejection of a high-scoring photograph. These checks do not exercise the native UI or physical presentation attacks.

Use Java 11 for the desktop runtime. The cached ONNX Runtime 1.30.0 native library crashed during environment initialization with this machine's Android Studio JBR 21; the same check passed with Temurin 11. Android uses ONNX Runtime Android 1.23.2 and OpenCV 4.12.0. The emulator test executes those Android JNI libraries, not the desktop JARs. Its SBI parser and repositories are test doubles. Physical Android hardware and full camera/UI workflows remain untested. The [raw instrumentation result](evidence/android-instrumentation.txt) and [validation report](validation.json) record that scope.

The Haar XML retains its Intel/OpenCV redistribution notice inside the file. The desktop client uses MPL-2.0 and the Android client uses MIT. The packaged PAD model's provenance and license are documented in `assets/models` and `docs/MODEL_CARD.md`. Additional [build notes](BUILD_NOTES.md) record local resource limits and generation steps.

The earlier landmark APKs package both model files and their notices. The ARM64 debug build is 223,712,618 bytes and remains untested on physical hardware. The x86_64 build passes all six emulator tests in 36.023 seconds. An earlier run took 80.685 seconds; its raw output is retained. Timing remains sensitive to host load and does not establish a stable phone latency.


The signed-active Android client build passes 12 tests in 63.239 seconds. Its actual SBI parser verifies RSA through an explicit fixture crypto provider; its actual onboarding API stores a valid static-portrait fixture once and rejects replay before a second write. Separate checks cover expiry, wrong transactions/model/digest, incomplete evidence, clock rollback, ledger capacity, failed persistence and no-face rejection. The fixture supplies completed-action metadata. No production certificate chain or successful human action is represented by these tests. The raw output is `evidence/android-signed-active-instrumentation.txt`.
