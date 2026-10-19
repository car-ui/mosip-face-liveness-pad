# Research PAD model card

## Identity and provenance

The packaged PAD model is MiniFASNet V2 from [Minivision's Silent-Face-Anti-Spoofing repository](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing), pinned to commit `b6d5f04ad78778917853b25c778acef6d5626d15`. The upstream weight file is `2.7_80x80_MiniFASNetV2.pth`, SHA-256 `a5eb02e1843f19b5386b953cc4c9f011c3f985d0ee2bb9819eea9a142099bec0`. The upstream repository declares Apache-2.0; its license is retained in `third_party/Silent-Face-Anti-Spoofing-LICENSE.txt`.

The exported model is `assets/models/minifasnet_v2.onnx`. Its exact hash, source hash, conversion check, input/output convention, and upstream commit are recorded in the adjacent JSON manifest. It is a single research model, not the upstream two-model ensemble or an independently trained MOSIP-specific model.

## Input and output

- Input is BGR `float32`, unnormalized pixel values 0..255, tensor shape `[1, 3, 80, 80]`.
- Expand the detected face rectangle by 2.7 around its center, shift/clamp to image bounds, then resize to 80×80 with bilinear interpolation. Context around the face is part of the model contract.
- Output is three logits. Apply softmax once. Class index 1 is the live class; the other class probabilities sum to the spoof score.
- The resident, operator, and supervisor thresholds are application policy values. They have not been calibrated against a representative MOSIP deployment population.
- The generic fallback contract is a separate binary ImageNet-normalized profile. Arbitrary ONNX models do not become compatible merely because they load.

The adapter validates model checksum, expected input shape, class count, finite outputs, and score bounds. Strict ONNX mode returns processing failure if the model is missing or inference fails. Changing to a heuristic engine is an explicit configuration choice.

## Conversion verification

`scripts/export_minifasnet.py` loads only the pinned weight checksum using `torch.load(..., weights_only=True)`, checks the upstream source checksum, exports ONNX opset 13, and compares ONNX Runtime CPU logits with PyTorch CPU logits on six tensors generated with seed 20261018. The maximum absolute logit difference observed was `2.6226043701171875e-06`.

This establishes numerical conversion parity on those tensors. It does not establish bona fide acceptance, spoof rejection, cross-device accuracy, calibration, demographic performance, or resistance to unseen attacks.

## Rebuild

Use a separate build environment with PyTorch 2.8.0 CPU, NumPy, ONNX, and ONNX Runtime. PyTorch is not a runtime dependency for the application. The export was exercised on CPython 3.11.15 with NumPy 2.4.6, ONNX 1.23.2, and ONNX Runtime 1.31.0.

```text
git clone --no-checkout https://github.com/minivision-ai/Silent-Face-Anti-Spoofing.git upstream-silent-face
git -C upstream-silent-face fetch origin b6d5f04ad78778917853b25c778acef6d5626d15
git -C upstream-silent-face checkout b6d5f04ad78778917853b25c778acef6d5626d15 -- src resources LICENSE
python scripts/export_minifasnet.py --upstream upstream-silent-face
```

The selective checkout avoids an upstream filename that Windows cannot check out. Runtime installation needs only `requirements.lock.txt` and the packaged ONNX/manifest, not the upstream tree or PyTorch.

## Intended use and limits

The optional `anti-spoof-mn3.onnx` profile is a different MobileNetV3 classifier,
not another MiniFASNet serialization. Its original Open Model Zoo asset is
SHA-384 verified and retained with the model's MIT license. It requires RGB
128 by 128 input with its declared channel mean/scale and returns two
probabilities with live class 0. The runtime validates them without a second
softmax. Its manifest documents the full contract and provenance. It is an
explicit research option and is not the default or an automatic fallback.
See `RELIABILITY_PLAN.md` for the research, comparison and limitations.

The 19 October research rebuild adds a separately manifested V1SE model with
4.0 crop scale for explicit comparisons. The default verification pipeline still
uses V2 alone. Its six conversion comparisons had maximum absolute logit error
`2.0265579223632812e-06`. No accuracy advantage is established for model fusion.
See [the research review](RESEARCH_AND_REBUILD.md) and the committed diagnostic
fixture report. The Python face detector is now the separately licensed YuNet
model; native detector changes require their own integration and validation.

Use for offline prototype development and controlled evaluation. Training data composition, consent, coverage, and target-population representativeness have not been independently established in this project. Upstream performance figures are not this project's measured results.

RGB PAD is sensitive to camera sensors, image processing, illumination, print/display materials, crop accuracy, and face pose. The [upstream README](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/b6d5f04ad78778917853b25c778acef6d5626d15/README_EN.md) describes deployment-dependent limitations. A blinking or smiling face can still be replayed or synthesized; action detection does not prove source authenticity. There is no claim of reliable mask, deepfake, injection, or adaptive replay detection here.

The inherited `face_landmarker.task` is a different model used for geometry/actions. Loading it does not establish passive PAD capability. Its provenance and distribution terms require a separate asset review.

During the browser check, the synthetic screen-replay fixture received a rolling passive score of approximately 0.997 from the packaged research model. The motion/action gate prevented image acceptance, and the attempt expired without completing an action. This is a concrete limitation of the model/fixture combination. It is not evidence that passive PAD reliably detects screen replay. A moving or adaptive replay needs separate adversarial evaluation, and deployment thresholds cannot be justified by conversion parity.

## Deployment evaluation still required

Freeze thresholds before testing, separate development and test subjects, record capture devices and lighting, report error rates for each presentation attack instrument group, include failure-to-acquire/nonresponse counts, and measure every supported target device. Use the [evaluation protocol](EVALUATION_PROTOCOL.md). No ISO/IEC 30107 certification is claimed.
