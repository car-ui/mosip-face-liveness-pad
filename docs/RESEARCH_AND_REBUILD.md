# Research and rebuild after the laptop trial failures

Reviewed on 19 October 2026. The target is an offline MOSIP liveness/PAD gate,
not a face-recognition login or a face-filter demo. This review covers the Python
laptop pipeline. Changes here do not automatically change the native Java or
Android gates. The supplied brief remains the acceptance specification; see
[the requirement evidence matrix](REQUIREMENTS_MATRIX.md).

## What was checked first

The deployed model manifest, source export, colour order, tensor layout, crop
expansion, output classes, thresholds, detection paths, action state machine,
retry handling, UI and actual laptop logs were inspected. The two anonymous
camera diagnostics saved numbers only, not face images.

Observed failures:

- The live trial stopped at score 0.371 with rejection cutoff 0.45. Given the
  user's report, this is an apparent bona fide rejection. It is not attack proof.
- Turning trials produced face-count interruptions and five-second timeouts.
  The failing frames were not retained, so their exact detection cause cannot be
  recovered. A screenshot subsequently produced one face from both detectors.
- A 60-frame diagnostic passed quality on every frame, with scores 0.665 to
  0.999. It did not reproduce the rejection and did not complete challenges.
- A separate 90-frame comparison found no faces with either detector. It is a
  nonresponse diagnostic and supplies no live/attack accuracy evidence.
- On a deterministic two-face NASA composite, the old downscaled Haar detector
  found only one face. This failure is reproducible without another human trial.

## Existing solutions and independent assessment

| Candidate | Source and useful capability | Decision for this rebuild |
|---|---|---|
| Silent-Face-Anti-Spoofing | [Original source and demo](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/b6d5f04ad78778917853b25c778acef6d5626d15/test.py). Separate crop scales, three-class inference and model fusion. Apache-2.0 source retained locally. | Keep V2 as the deployed baseline. Export V1SE reproducibly for comparison, without assuming the ensemble improves target-camera accuracy. |
| OpenCV YuNet | [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet). Neural multi-face detection with confidence filtering and nonmaximum suppression. MIT asset license. | Use the March 2023 asset compatible with installed OpenCV 4.11. Pin hash and source. Use one source of detection geometry. |
| MediaPipe Face Landmarker | [Official guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python). Landmarks, blendshapes, tracking modes and optional face transforms. | Retain for action observations. Do not union one landmark outline with a detector rectangle as though they were different people. Multiple landmark faces still block acceptance. |
| RetinaFace / SCRFD | [Original PAD detector](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/b6d5f04ad78778917853b25c778acef6d5626d15/src/anti_spoof_predict.py), [InsightFace licensing](https://github.com/deepinsight/insightface#license). Stronger detector families are viable candidates, but pretrained weights have their own terms. | Do not introduce another model stack before measuring the lighter packaged detector. Code license alone does not establish weight distribution rights. |
| UniFace / yakhyo implementation | [UniFace](https://github.com/yakhyo/uniface), [standalone MiniFASNet implementation](https://github.com/yakhyo/face-anti-spoofing). Existing inference and tracking utilities. | Useful implementation references. Their MiniFASNet support does not supply an independently validated replacement model. Avoid adding the whole library for a model already supported locally. |
| DeepFace FasNet wrapper | A FasNet source path appeared in search, but its current GitHub/raw endpoints returned 404 during this review. | No current source verification, so no implementation or dependency decision is based on it. |
| New small ONNX PAD projects | [facenox](https://github.com/facenox/face-antispoof-onnx) publishes another MiniFAS-derived model and reported metrics. | Candidate for a later held-out comparison. Repository accuracy claims are not measurements on this camera, subject population or attack instruments. No silent model swap. |

The [NIST passive PAD evaluation](https://www.nist.gov/publications/face-analysis-technology-evaluation-fate-part-10-performance-passive-software-based)
evaluates software PAD against defined presentation attack instruments. That
supports an evaluation plan with explicit instruments and errors, rather than
using action-unit tests or a successful screenshot as an accuracy estimate.

## Findings that change the implementation

### Detection and spoof crops must have one source

The old detector ran Haar at half resolution. The first turning repair appended
current landmark rectangles when they did not overlap enough with Haar. That
can count two outlines of the same head and can switch the PAD crop between
different geometries. These are design risks; neither is proven to explain the
exact unsaved failing frame.

The default is now YuNet, confidence 0.9 and NMS 0.3, with verified packaged
weights. One YuNet detection remains one even if the landmark outline differs.
No YuNet detection means no accepted face, even if a landmark outline exists.
Two independently observed landmark faces still block capture. The old Haar
path remains explicitly selectable for comparison and regression testing.

### Preprocessing is part of the model

The [upstream crop code](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/b6d5f04ad78778917853b25c778acef6d5626d15/src/generate_patches.py)
expands each detected rectangle, shifts it inside image bounds and resizes it.
Our V2 profile already uses BGR values 0..255, NCHW 80 by 80, live class 1 and
one softmax. An RGB/ImageNet-normalization repair would be incorrect for these
weights. No such change was made.

The upstream reference combines predictions from model files. Its V1SE weights
need a 4.0 crop rather than V2's 2.7. The new exporter verifies the pinned V1SE
source and weights, then compares ONNX and PyTorch on six seeded tensors.
Maximum absolute logit difference was 0.0000020265579223632812. This verifies
conversion, not PAD accuracy.

### An ensemble is an experiment, not a guaranteed fix

The default static-fixture comparison produced a V2 score of 0.816 and V1SE
score of 0.974 on the single NASA photo under YuNet. Their arithmetic mean is
0.895. A four-pixel horizontal crop shift moved V2 between 0.816 and 0.957.
The same static fixture is not a bona fide live sample. These numbers show crop
sensitivity and the risk of treating model averaging as an automatic improvement.
They do not measure physical screen-replay performance.

Consequently, the verification pipeline keeps its explicit V2 baseline and
thresholds. The comparison tool exposes both model observations without
silently making the ensemble an acceptance decision.

### People need time to read and prepare

Each generated action now has a two-second preparation phase before observing
the action and its 12-second deadline. Preparation frames cannot satisfy an
action. Main instructions remain visible; secondary feedback has reading time.
Failures are immediate, retain their reason, and display model score/cutoff when
applicable. A rejection is no longer worded as proof that the user is not live.
The Python head-turn value remains a symmetry proxy, not calibrated degrees.
Replacing it with pose matrices needs measured direction/neutral-range checks
before enabling a different threshold convention.

## Reproduce the comparisons

```powershell
python scripts/compare_research_backends.py --output output/local/backend-fixtures.json
python scripts/compare_research_backends.py --camera --frames 90 --output output/local/backend-camera.json
python scripts/export_minifasnet.py --upstream PATH_TO_PINNED_UPSTREAM --variant v1se
python -m pytest -q
```

The camera option is explicit and bounded. It saves numeric observations only.
It does not assign a live/attack ground truth or generate a verified capture.
The committed [fixture report](research-backend-fixtures.json) is reproducible
except for latency. It is a small diagnostic, not an independent PAD benchmark.

## Acceptance gates before another reliability claim

1. Real model checks must include zero, one and multiple face fixtures, detector
   failure, model integrity failure, unavailable inference and crop contracts.
2. Actions must reject wrong direction, invalid starting pose, landmark loss,
   timeout and actions performed during preparation. No biometric may escape a
   failed or uncertain trial.
3. Development data must include consented live sessions and actual print and
   display attacks under different cameras and lighting. Use development
   sessions to choose parameters, then freeze them.
4. Held-out sessions must be independent of tuning. Report bona fide rejection,
   attack acceptance by instrument, nonresponses and retries. Report full trial
   outcomes rather than a favourable selection of frames. Use the existing
   [evaluation protocol](EVALUATION_PROTOCOL.md).
5. A full live trial and rejected physical attacks must then be demonstrated in
   the native MOSIP client path with the configured gate before downstream use.
   Neither a Python pass nor the current native fixture tests close that gate.

The research and architectural repair are implemented. Physical PAD robustness,
human action reliability and an official client demonstration remain open. A
larger test count cannot substitute for those results.
