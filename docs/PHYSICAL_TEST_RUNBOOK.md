# Physical test handoff

Physical results have not been collected. These instructions describe work to perform after the software build and automated checks pass.

## Native Android camera trial

The debug reference SBI app includes a separate launcher named **PAD physical test**. It opens the same `NativePadCameraActivity` used by SBI capture. It tests the camera and action engines without production signing keys, registration or authentication. Release builds exclude this launcher.

Use the exact tested debug APK and record its SHA-256 from the delivery manifest. Install it on a consenting participant's Android device running Android 8 or later. Open **PAD physical test**, choose the actual presentation, then press **Start camera trial**. Android requests camera permission if needed.

For an initial diagnostic sequence:

1. Select **Real person**. Use a real person, with their face centered and sufficient light. Follow the randomly ordered blink and turn prompts, including the return to neutral. Run five separate attempts.
2. Select **Printed face photo**. Hold a printed face photograph in front of the camera, without a live face visible alongside it. Run five separate attempts. Keep print and lighting conditions consistent within a group.
3. Select **Face video on another screen**. Present a face video on a separate screen. Keep live faces outside the capture. Run five separate attempts, then record an adaptive replay separately if available.
4. Run an interruption check by cancelling or backgrounding capture. It must not report an accepted capture.
5. Choose **Export anonymous report** and save the JSON locally. Keep a private note of print material, screen type, lighting, distance and participant/source grouping.

The report records device model, Android API, model hashes, thresholds, duration and capture outcome. It contains no photograph, ISO biometric, identity or capture transaction. The app stores it privately and does not automatically send it anywhere. Export before clearing app data or reinstalling. It retains at most 1,000 attempts.

Retain accepted attacks as failures. A cancelled, timed-out or failed attempt is a failed/incomplete capture, not measured evidence of a particular PAD classification. The launcher does not calculate APCER or BPCER. Five attempts per group are a diagnostic starting point, not an independent accuracy study. Do not tune thresholds on these attempts and describe those same attempts as held-out validation.

## Laptop-only alternative

Without an Android device, the existing OpenCV prototype can use a laptop webcam:

```powershell
$env:MOSIP_PAD_MODE = "ONNX"
$env:MOSIP_PAD_MODEL = "assets/models/minifasnet_v2.onnx"
python run_desktop_app.py --workflow OPERATOR_AUTHENTICATION
```

Run this from the installed project environment, without `--mock`. Follow the positioning and active prompts. A prototype webcam result does not establish execution in the official desktop Registration Client, Android camera SBI or an L1 device. Keep the software/device scope with every result.

## What these trials cannot establish

The debug launcher checks the camera and native PAD/action path. It does not test a production SBI certificate chain, official registration storage, packet generation or identity matching. Signed parser/storage integration has separate controlled automated tests. A complete submission still needs a linked native-client camera run and the device/attack matrix in `EVALUATION_PROTOCOL.md`.
