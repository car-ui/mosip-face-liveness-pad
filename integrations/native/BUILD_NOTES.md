# Build notes for the pinned clients

These notes record the build configuration used for the native checkpoint work on Windows. They do not claim a live device test.

## Desktop

Use Temurin Java 11, Maven 3.9.16 and the pinned desktop revision in `README.md`. Apply the preparation script, then run the upstream reactor from its `registration` directory:

```text
mvn -DskipTests -pl registration-client -am compile
```

The local build used an existing Maven dependency cache in offline mode. The upstream parent compiler configuration reserves 1024 MB initially and allows 2024 MB. For this machine it was reduced locally to 64 MB and 384 MB, with `JAVA_TOOL_OPTIONS=-Xmx192m -XX:+UseSerialGC`. This adjustment is excluded from the integration patch. The reactor compiled all five selected modules, including the actual modified client controllers.

`DesktopControllerRejectionCheck.java` is compiled against that reactor's actual client and service classes and resolved dependencies. It needs JavaFX on its classpath because it constructs the resident controller's empty exception pane, but it does not launch an application window. Its optional argument is an existing portrait image fixture. The test converts image bytes to a face ISO using MOSIP's own `FaceEncoder`, then runs the patched acceptance paths. It does not simulate successful SBI signatures or certify any device.

## Android

The local build uses Flutter 3.10.4, Dart 3.0.3, Android Studio's JBR 21, Gradle 8.5 and the Android SDK. The pinned project already specifies AGP 8.3.2 and compile SDK 34. The native patch adds ONNX Runtime Android 1.23.2 and OpenCV 4.12.0.

Keep the build, Flutter package cache and Gradle cache on the same drive. The Kotlin/Flutter plugin setup failed when its build directory was on D: and its package sources were on C:. Generated `.flutter-plugins*` and package configuration must refer to the selected cache consistently. `android/local.properties` needs `sdk.dir` and `flutter.sdk`; local signing credentials must never be copied into this repository.

Run the upstream Pigeon generation commands from `pigeon.sh` to generate its 18 Java/Dart communication bridges. They are generated build inputs, not replacements for the patched `BiometricsDetailsApi` source.

All eight files declaring generated JSON/Freezed parts in this pinned revision are under `lib/model`. On this machine the unrestricted build runner exhausted memory while analyzing unrelated application/test sources. A local `build.yaml` restricted its source set:

```yaml
targets:
  $default:
    sources:
      - lib/model/**
      - pubspec.yaml
      - $package$
```

The following generated 29 outputs successfully:

```text
dart --old_gen_heap_size=1024 run build_runner build --low-resources-mode --build-filter=lib/model/** --delete-conflicting-outputs
```

The build runner configuration is a local build accommodation, excluded from the caller patch. The Windows, Linux and macOS desktop platform folders were temporarily renamed while working around Flutter's desktop-plugin symlink check. Then `flutter pub get --offline` completed and generated `io/flutter/plugins/GeneratedPluginRegistrant.java`. Android dependencies and generated bridges remained available; no machine-wide Developer Mode setting was changed.

Build the actual Android app with the upstream Gradle wrapper or equivalent Gradle 8.5 installation:

```text
gradle --no-daemon --max-workers=1 -Dorg.gradle.jvmargs="-Xmx2048m -XX:+UseSerialGC" :app:assembleDebug :app:assembleDebugAndroidTest
```

Both APKs built successfully. A 768 MB build heap filled during external bytecode merging; 2048 MB completed the full build. The incremental test-only rebuild used 768 MB. Build-machine memory is not an Android runtime benchmark. The upstream dependencies also emit Kotlin-metadata compatibility warnings with this pinned AGP/D8 toolchain. They are retained in the local build log and need toolchain/dependency alignment before a production release.

Separate ARM64 and x86_64 packages avoid shipping unused native libraries:

```text
gradle --no-daemon --max-workers=1 -Dorg.gradle.jvmargs="-Xmx2048m -XX:+UseSerialGC" -Psplit-per-abi=true -Ptarget-platform=android-arm64,android-x64 :app:assembleDebug
```

The caller patch makes the upstream release ABI list conditional so it does not conflict with Flutter's explicit split settings. The initial split-build ARM64 debug package was 219,846,672 bytes, compared with 503,198,515 bytes for the universal debug package. This is a packaging reduction, not a runtime RAM, power or accuracy measurement. ARM64 physical-device execution remains untested.

`validation.json` records build and execution results. The app APK's signature, ZIP integrity, packaged model hash, model license and PAD class descriptors were checked. The initial universal APK has four native ABIs. The split packages contain one ABI each and remain large debug builds. Emulator execution uses an isolated API 34 Google ATD x86_64 image, one virtual CPU and 2048 MB RAM. The emulator raised the requested memory to that amount. Its camera is disabled, and its data/configuration live on D: without changing the user's existing AVD data.

Run the focused instrumentation class after installing the app and test APKs:

```text
adb shell am instrument -w -r -e class io.mosip.registration_client.api_services.NativePadAcceptanceTest io.mosip.registration_client.test/androidx.test.runner.AndroidJUnitRunner
```

The SBI parser and client repositories are test doubles. Android JNI libraries, ONNX inference, ISO decoding, and `BiometricsDetailsApi.parseRCaptureResponse` execute in the actual app process. Neither an emulator nor a portrait fixture establishes physical presentation-attack accuracy.

The first instrumentation attempt had one test-fixture failure because the mocked Activity did not supply its asset manager and cache directory. The fixture now supplies those real target-application resources. A fresh-process run passed all four tests. The model and capture acceptance code were not bypassed to obtain that result.

The current CPU-count-aware build passes five instrumentation tests in 17.635 seconds, plus two further benchmark-only fresh-process runs. It uses one intra-op thread on the one-CPU emulator. Both native clients rebuild successfully with that shared engine change. The current ARM64 debug package is 220,254,144 bytes. The x86_64 app and instrumentation APK were installed and tested together; ARM64 remains untested on hardware. See `docs/ANDROID_BENCHMARK.md` for every timing/PSS observation and the limits of the measurements.


## Signed active evidence

The newer client build passes 12 tests, including the actual SBI response parser with an RSA fixture crypto provider and the actual onboarding API. Run both classes with:

```text
adb shell am instrument -w -r -e class io.mosip.registration_client.api_services.NativePadAcceptanceTest,io.mosip.facepad.AndroidActiveEvidenceTest io.mosip.registration_client.test/androidx.test.runner.AndroidJUnitRunner
```

The producer patch targets the deprecated root app of `mosip/android-camera-mds` at `d1ec22a542294b798f5b9c5bb97428deabb2064b`. Use `prepare_native_clients.py camera-sbi` and follow `docs/CAMERA_SBI_INTEGRATION.md`. Production use of the extension requires an existing provisioned SBI certificate trusted by the client. No device key or trust bypass is installed by this patch.
