# Reliability investigation and execution plan

19 October 2026. This plan follows the research below and precedes further
inference/state-machine edits. It supersedes the assumption that a detector
replacement alone resolves the reported physical failure.

## Research completed before implementation

The current application rejected user-reported live captures at 0.212, 0.420,
0.447 and 0.387. The last three are retained in the physical-run audit. There
was also a session reaching active challenges at rolling score 0.625. These are
separate sessions, not a reconstructed continuous score sequence. The logs do
not contain enough information to estimate the person's error rate.

Inspection confirms two architectural problems. One per-frame attack verdict
immediately terminates passive evaluation despite the presence of a temporal
buffer. During actions, the same rule terminates the session on a single model
outlier. The existing tests mostly prescribe this immediate failure behavior;
they cannot establish that it is a suitable video decision policy.

The [original Minivision project](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/b6d5f04ad78778917853b25c778acef6d5626d15/README_EN.md)
warns that camera, scene and head pose affect results. Its reference uses model
fusion, which was reviewed in RESEARCH_AND_REBUILD.md. Replacing a wrapper or
changing the detector does not independently solve model generalization.

The [OpenVINO anti-spoof-mn3 specification](https://docs.openvino.ai/2023.3/omz_models_model_anti_spoof_mn3.html)
describes a separate MobileNetV3 binary classifier trained on CelebA-Spoof. Its
original ONNX input is RGB 128 by 128 with model-specific channel mean/scale.
Its output is probabilities, with class 0 live, rather than MiniFASNet's three
logits with class 1 live. Applying a second softmax would be incorrect. The
[upstream demo](https://github.com/kprokofi/light-weight-face-anti-spoofing/blob/82a2c26bacff5462c6f9320c34ae0363ccbed497/demo/demo.py)
uses a tight detected-face crop rather than MiniFASNet's 2.7 context crop.

The model is 12,270,179 bytes. Its download was verified against the SHA-384 in
[Open Model Zoo's pinned descriptor](https://github.com/openvinotoolkit/open_model_zoo/blob/2c9b5c563ab3a202d085a42e2bbfc48f77961f4b/models/public/anti-spoof-mn3/model.yml).
The resulting SHA-256 is
`c4c99af04603b62d7e44f6f4daeb33e0daeccc696008c0b1d62f6f5cebbb3262`.
The [original model license](https://github.com/kprokofi/light-weight-face-anti-spoofing/blob/82a2c26bacff5462c6f9320c34ae0363ccbed497/LICENSE)
is MIT. No new runtime is required because the download is ONNX.

The [NIST PAD evaluation API](https://pages.nist.gov/frvt/api/FRVT_pad_api_v1.1.pdf)
supports image and video-frame input, fixed operating thresholds, and separately
measured attack and bona fide errors. It does not prescribe our proposed window
length or demonstrate this model's accuracy on this laptop. Those choices below
are engineering parameters requiring physical validation, not NIST approval.

## Plan and acceptance checks

1. Preserve the failing evidence. Add deterministic tests for a single suspect
   frame, sustained low scores, recovery, sparse/nonfinite inputs and a suspect
   frame arriving at action completion. Use explicit score doubles, without
   labelling them physical accuracy tests.
2. Introduce a bounded session PAD gate. Every suspect observation immediately
   blocks capture and clears completed actions. Confirm rejection from a short
   sustained sequence. Never let previous high scores average away a new attack.
   Require fresh clear observations after a suspect frame. Engine failure remains
   an immediate error. Expose the confirmation policy and record it in audits.
3. Add the MobileNetV3 model as an explicit research profile, with verified
   provenance, RGB normalization, tight crop, probability validation and no second
   softmax. Compare it with the existing models on identical inputs. Keep its
   performance claims separate from this project's measured results.
4. Improve acquisition. Provide a short preview/settling period before feeding
   frames to verification. Keep text stable and prevent a reset key held down
   from continuously creating new sessions. Do not display a success to hide an
   unresolved rejection.
5. Run regression and model-contract tests, real-model fixture comparisons and
   source-package validation. Update the launcher to the exact verified source,
   push coherent milestones with CI skipped, and retain an in-repository resume
   checkpoint. Do not repeatedly ask the user to test while changing parameters.

## Decision boundaries

The existing rejection cutoff is not lowered. A sequence policy changes when
evidence is sufficient for a terminal decision, not whether suspect frames may
be accepted. The candidate model is not made the default solely because its live
scores are higher. No model, threshold or window is called calibrated without
development and held-out physical attack/live trials. The official MOSIP client
and native Android paths require separate implementation and validation.

## Execution record

Steps 1 through 4 are implemented. The default evidence gate requires at least
five consecutive low-score observations spanning 0.5 seconds to confirm
rejection. Recovery requires five fresh non-attack observations spanning 0.25
seconds. Gaps over 0.75 seconds reset streaks. Ten seconds without stable
evidence produces an inconclusive failure. These are explicit engineering
defaults, not calibrated operating points. Suspect frames immediately clear
actions and passive history; acceptance is impossible while collecting evidence.
The pipeline gate is evaluated before any capture-success path.

The MN3 adapter validates probabilities rather than applying another softmax.
It uses the documented RGB normalization and tight crop. Its fixture scores,
including 0.999 on the YuNet-cropped static NASA image, are recorded in
`research-backend-mn3-fixtures.json`. This is not physical attack accuracy and
does not justify selecting the model as the default. All comparison results,
including unfavourable ones, are retained.

Acquisition now has two seconds of preview before evidence collection. Reset
auto-repeat is suppressed. Rejection remains visible in the bottom card; the
large face-covering rejection modal is diagnostic-only. Recent bounded scores
are included with terminal PAD rejections, without saving face images.

For step 5, all 151 Python tests passed in 28.06 seconds, and an eight-frame
explicit simulator UI startup/settling/exit smoke run completed. These checks
validate software behavior. No new successful physical action session or
physical attack rejection is claimed. The final source package must also be
verified after commit before updating the laptop launcher.
