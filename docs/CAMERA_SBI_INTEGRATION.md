# Camera-owning reference SBI

The Android registration client receives a completed ISO face capture from a separate SBI app. It cannot prove a live action by examining that final photograph alone. This patch adds an active camera session to the reference app that owns the capture.

The target is [MOSIP android-camera-mds](https://github.com/mosip/android-camera-mds/tree/d1ec22a542294b798f5b9c5bb97428deabb2064b), commit `d1ec22a542294b798f5b9c5bb97428deabb2064b`. Upstream marks this root application deprecated. This is research integration in that reference app, with no claim of certified SBI hardware or production support.

## Capture behavior

The existing capture intent opens the new internal `NativePadCameraActivity`. Camera2 supplies JPEG frames to the same native PAD and landmark engines used by the client adapters. Both models are pinned by SHA-256. The activity accepts a validated capture policy for action count, challenge pool, timeout and recovery limit; when no caller extras are supplied it defaults to two actions, `blink,turn`, 20 seconds and two retries. It chooses actions from that pool, including a return to neutral after every action. Face loss resets the actions. A successful session consumes its proof once for the exact final JPEG, then embeds those bytes in the ISO record. It does not request a second photograph.

The preview displays the frame being analyzed and the current action prompt. Camera permission denial, unavailable cameras, native initialization errors, cancellation, interruption and timeout return an empty failed capture. The activity disables screenshots. JPEG frames stay in memory; the application does not save them as photographs.

The implementation normalizes all eight EXIF orientations before analysis and removes metadata when it re-encodes the JPEG. It chooses a supported JPEG size between 480 by 360 and 1280 by 1280 pixels and keeps two camera buffers. The choice favors lower image size to limit inference work. Camera throughput, sustained thermal behavior and successful human actions still need physical testing.

The final image-quality score combines whole-frame exposure and Laplacian sharpness. It is an uncalibrated research heuristic, separate from PAD confidence. The app compares it with the existing request's quality threshold. It is not a measured ISO image-quality score. ISO captures above 750 KiB fail before returning an Activity result, to leave room under Android's Binder transaction limit.

The debug source set adds a separate **PAD physical test** launcher. It invokes the same camera activity with a fresh transaction, a 30-second limit and quality threshold 60, then saves an anonymous trial result. It has no registration, authentication or production-signing role. See [the physical test runbook](PHYSICAL_TEST_RUNBOOK.md). Release builds exclude this launcher.

## Reproduce the source

Use a new checkout at the exact revision. The preparer refuses existing modifications.

```powershell
git clone https://github.com/mosip/android-camera-mds.git CAMERA_SBI_CHECKOUT
git -C CAMERA_SBI_CHECKOUT checkout d1ec22a542294b798f5b9c5bb97428deabb2064b
python scripts/prepare_native_clients.py camera-sbi CAMERA_SBI_CHECKOUT
```

The patch updates the legacy root app to Android Gradle Plugin 8.3.2, namespace configuration and compile SDK 34. Its target SDK remains 30. Build with JDK 21, Gradle 8.5, Android SDK platform 34 and build tools 35.0.0. Configure the checkout's local SDK path, then run Gradle externally because its inherited wrapper is older.

```powershell
gradle -p CAMERA_SBI_CHECKOUT --no-daemon --max-workers=1 :app:assembleDebug :app:assembleDebugAndroidTest
```

For a smaller debug package, pass `-PfacePadAbi=arm64-v8a` for an ARM64 phone or `-PfacePadAbi=x86_64` for an x86_64 emulator. Omitting it retains the universal APK. Other values fail at configuration time. The smaller packages retain the exact code, models, notices and relevant native libraries from the universal build; removing other architectures does not demonstrate lower runtime memory use or faster inference.

The reference application's MPL-2.0 license is included in `third_party/android-camera-mds-MPL-2.0.txt`. The patch does not redistribute its bundled third-party JARs. Review those upstream dependencies before distributing an assembled SBI application.

## Evidence limits

The instrumentation suite checks real native model initialization, rejection of blank and repeated static frames, session closure, ISO JPEG preservation, all eight EXIF orientations, and an empty failed result when the camera-disabled emulator has no camera. Its static fixture is the attributed NASA photograph already used by the repository. These checks do not establish physical spoof rejection or successful human action detection.

The camera activity returns active metadata to its internal caller. Evidence version 2 is minted only after the native session consumes the exact final JPEG. The SBI includes the ordered action types, action count, session start, effective timeout, allowed and used retries, completion time, exact ISO digest, both model hashes and current capture transaction inside its existing signed capture payload. The patched Android registration client reads it only after its existing SBI signature, certificate-trust, timestamp and transaction checks. It checks the action types against the current client pool, the observed duration against both the SBI timeout and current client policy, and used retries against the current retry limit. A private persistent ledger consumes each transaction once. Evidence expires after 30 seconds, with at most two seconds of future clock skew; version 1 proofs are rejected. The final image still passes the registration client's own face and PAD checks; an attack or inference error cannot be overridden by active metadata.

The pinned Android Registration Client patch adds `customOpts` to the SBI `CaptureRequest` DTO and fills it at `BiometricsDetailsApi.rcapture()` for face/exception-photo capture from the current resident/operator policy cache. The MOSIP SBI specification defines `customOpts` as an object, while this pinned camera DAO exposes it as `List<Map<String,String>>`. The SBI now converts an incoming object into that legacy DTO representation before deserialization, then reads both its DAO list and JSON-backed object forms. `NativePadPolicy.toSbiCustomOptions()` serializes the validated snapshot; `CameraSbiRequestPolicy` rejects partial, mistyped or out-of-range values before camera access. If no policy values are provided, the SBI uses two actions, a `blink,turn` pool, 20 seconds and two retries. These request values are untrusted hints. The registration client remains the acceptance authority and compares signed results against its independently loaded current policy before storage. Both patches and the preparation workflow apply to the exact pinned upstream commits, but neither patched app has been rebuilt here. This extension also requires both patched applications and a correctly provisioned SBI device signing certificate trusted by the registration client. No signing key, developer trust bypass or simulated certificate is installed by these patches. It is a custom integration extension and has not been certified against an official SBI conformance suite. A compromised trusted SBI could fabricate its assertions; this software does not provide hardware attestation. See the [MOSIP SBI capture specification](https://github.com/mosip/documentation/blob/1.2.0/docs/id-lifecycle-management/supporting-components/biometrics/sbispec.md) for the standard `customOpts` request field.

The Android parser tests use a generated RSA fixture key through an explicit test crypto provider. They exercise real signature verification and the upstream response parser, while certificate-chain trust is represented by that fixture provider. Their completed-action, session-duration and retry claims are generated from injected action geometry, not output from a live camera. Successful human actions, production PKI, physical camera capture and registration packet generation remain unverified. The source path now carries cached client settings through standard SBI `customOpts` and the camera DAO conversion; rebuild both apps and verify stricter policy updates and mismatched evidence end to end.

## Clean-runner Android CI

`.github/workflows/native-android.yml` builds the exact reference SBI revision on Ubuntu with JDK 21 and Gradle 8.5, then runs eight instrumentation tests on an API 34 x86_64 Google ATD emulator. Both emulated cameras are disabled. It runs for relevant changes on `main` and pull requests, or by manual workflow dispatch. The earlier six-test version completed successfully in [hosted run 39165055387](https://github.com/car-ui/mosip-face-liveness-pad/actions/runs/39165055387), with raw output and APK checksums retained in the native validation report. The eight-test debug-launcher version has local emulator evidence. Further pushes use `[skip ci]` while the account's Actions allowance is exhausted. No additional hosted run is required to execute the driver locally on the explicitly named test emulator.

The workflow uses commit-pinned actions and read-only repository permissions. The [emulator action's documented KVM setup](https://github.com/ReactiveCircus/android-emulator-runner#running-hardware-accelerated-emulators-on-linux-runners) supplies acceleration. The test driver refuses any emulator whose AVD name differs from its explicit target. It checks the APK's exact models and notices before installation and preserves raw instrumentation output, diagnostic logs and APK checksums. It requires a complete eight-test success report; an `adb` exit code alone is insufficient. The artifact contains logs and checksums, without redistributing the assembled reference SBI APK.
