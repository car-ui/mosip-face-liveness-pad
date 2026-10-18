# Camera-owning reference SBI

The Android registration client receives a completed ISO face capture from a separate SBI app. It cannot prove a live action by examining that final photograph alone. This patch adds an active camera session to the reference app that owns the capture.

The target is [MOSIP android-camera-mds](https://github.com/mosip/android-camera-mds/tree/d1ec22a542294b798f5b9c5bb97428deabb2064b), commit `d1ec22a542294b798f5b9c5bb97428deabb2064b`. Upstream marks this root application deprecated. This is research integration in that reference app, with no claim of certified SBI hardware or production support.

## Capture behavior

The existing capture intent opens the new internal `NativePadCameraActivity`. Camera2 supplies JPEG frames to the same native PAD and landmark engines used by the client adapters. Both models are pinned by SHA-256. The session requests a blink and a randomized turn, including a return to neutral. Face loss resets the actions. A successful session consumes its proof once for the exact final JPEG, then embeds those bytes in the ISO record. It does not request a second photograph.

The preview displays the frame being analyzed and the current action prompt. Camera permission denial, unavailable cameras, native initialization errors, cancellation, interruption and timeout return an empty failed capture. The activity disables screenshots. JPEG frames stay in memory; the application does not save them as photographs.

The implementation normalizes all eight EXIF orientations before analysis and removes metadata when it re-encodes the JPEG. It chooses a supported JPEG size between 480 by 360 and 1280 by 1280 pixels and keeps two camera buffers. The choice favors lower image size to limit inference work. Camera throughput, sustained thermal behavior and successful human actions still need physical testing.

The final image-quality score combines whole-frame exposure and Laplacian sharpness. It is an uncalibrated research heuristic, separate from PAD confidence. The app compares it with the existing request's quality threshold. It is not a measured ISO image-quality score.

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

The reference application's MPL-2.0 license is included in `third_party/android-camera-mds-MPL-2.0.txt`. The patch does not redistribute its bundled third-party JARs. Review those upstream dependencies before distributing an assembled SBI application.

## Evidence limits

The instrumentation suite checks real native model initialization, rejection of blank and repeated static frames, session closure, ISO JPEG preservation, all eight EXIF orientations, and an empty failed result when the camera-disabled emulator has no camera. Its static fixture is the attributed NASA photograph already used by the repository. These checks do not establish physical spoof rejection or successful human action detection.

The camera activity returns active metadata to its internal caller. The SBI includes that object inside its existing signed capture payload, with the exact ISO digest, both model hashes, completion time and current capture transaction. The patched Android registration client reads it only after its existing SBI signature, certificate-trust, timestamp and transaction checks. A private persistent ledger consumes each transaction once. Evidence expires after 30 seconds, with at most two seconds of future clock skew. The final image still passes the registration client's own face and PAD checks; an attack or inference error cannot be overridden by active metadata.

This extension requires both patched applications and a correctly provisioned SBI device signing certificate trusted by the registration client. No signing key, developer trust bypass or simulated certificate is installed by these patches. It is a custom integration extension and has not been certified against an official SBI conformance suite. A compromised trusted SBI could fabricate its assertions; this software does not provide hardware attestation.

The Android parser tests use a generated RSA fixture key through an explicit test crypto provider. They exercise real signature verification and the upstream response parser, while certificate-chain trust is represented by that fixture provider. Their completed-action metadata is simulated for a static portrait. Successful human actions, production PKI, physical camera capture and registration packet generation remain unverified.
