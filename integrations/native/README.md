# Native capture checkpoints

This directory adds an offline, in-process PAD checkpoint to pinned MOSIP client sources. It supplements the Python prototype. It does not establish a completed live registration, a live client UI rejection, or physical attack accuracy.

| Client | Upstream | Commit |
| --- | --- | --- |
| Android | `mosip/android-registration-client`, v1.1.1 | `8f4643a694f3b5e66e0491f077a8630ab5667658` |
| Desktop | `mosip/registration-client`, release-1.2.0 | `935306e2fd38bff2803697468e595026b1d18cec` |

Run `python scripts/prepare_native_clients.py desktop PATH_TO_CLEAN_CHECKOUT`, or use `android` for Android. The preparer checks the exact commit and refuses a dirty checkout. It applies the small caller patch, installs the shared Java engine and platform adapter, and copies the packaged ONNX model and face detector into application resources.

The desktop patch also repairs the existing preview stream reader. Multipart headers are bounded to 16 KB and JPEG payloads to 8 MB. The reader rejects EOF, truncated payloads, duplicate or invalid lengths, and invalid JPEG markers. Resident and onboarding stream availability checks preserve the first byte. Preview updates use the JavaFX thread with one pending update, and an old stream session cannot clear its replacement. Stopping a stream clears cached frame bytes.

## Acceptance paths

Desktop checks resident face and exception-photo candidates in `GenericBiometricsController` before deduplication, registration storage, or the success alert. `BiometricsController` checks operator-onboarding captures. Both checks run in the background capture task before it returns its candidates. `BaseController.captureAndValidateFace` checks operator and supervisor captures before the identity matcher. Android checks `BiometricsDetailsApi.parseRCaptureResponse` after existing SBI signature/transaction validation and before registration or operator-onboarding storage. Rejection completes the Flutter callback with an error and shows a reason.

The engine verifies the model SHA-256, requires exactly one detected face, uses the MiniFASNet 2.7x context crop, raw BGR channels, and the model's live output index. Invalid images, unavailable native libraries, model corruption and inference errors reject the capture. Model scores at or below 0.45 reject as an attack. Scores below 0.85 require active evidence. These are research thresholds, not measured operating points. This checkpoint does not yet provide the prototype's temporal checks, image-quality policy or retries.

**Active evidence is not supplied by these adapters yet.** Operator/supervisor face authentication and operator onboarding therefore reject with `ACTIVE_CHALLENGE_REQUIRED` even if the passive model returns a high score. This is a deliberately incomplete, fail-closed integration. It must not be described as functional operator authentication or successful active liveness. Resident candidates with high passive scores may pass this checkpoint. The model has known replay weaknesses described in `docs/MODEL_CARD.md`.

Android receives a completed capture URI from a separate SBI app. Adding active challenges requires cooperation with the app that owns that camera session. A recorded capture alone cannot prove a requested action happened during the current challenge. Desktop also still needs its live stream connected to challenge evaluation and the exact final candidate.

## Verification

The current CPU-count-aware build passes five Android instrumentation tests. Its benchmark makes 100 timed inference calls after ten warmups, checks every score against Python, and records process memory. Three fresh processes were measured for both the previous two-thread build and the adaptive one-thread build on the one-CPU emulator. All results and limits are in [the Android benchmark report](../../docs/ANDROID_BENCHMARK.md). This adds an emulator baseline; physical ARM64 execution and energy use remain untested.

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
