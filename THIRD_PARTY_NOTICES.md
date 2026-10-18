# Third-party notices

## MiniFASNet research PAD model

The exported MiniFASNet V2 ONNX model is derived from `minivision-ai/Silent-Face-Anti-Spoofing` at commit `b6d5f04ad78778917853b25c778acef6d5626d15`. The upstream repository declares Apache License 2.0. A copy is retained at `third_party/Silent-Face-Anti-Spoofing-LICENSE.txt`. The export changes serialization to ONNX and does not claim new training or the upstream ensemble's performance. See `assets/models/minifasnet_v2.onnx.json` for checksums and `docs/MODEL_CARD.md` for preprocessing and limits.

## Inherited assets

The self-contained pitch embeds the Manrope variable font from [Google Fonts](https://github.com/google/fonts/tree/main/ofl/manrope). It uses the SIL Open Font License. A copy is retained at `third_party/Manrope-OFL.txt`.

`assets/models/face_landmarker.task` and `tests/sample_images/*` were already present in the starting repository. Their individual origin, consent, and distribution terms were not documented there. This change does not certify their provenance or grant rights over those assets. Review or replace them before public submission packaging. In particular, a recorded face photo is not a bona fide live-person test sample.

OpenCV, MediaPipe, ONNX Runtime, NumPy, FastAPI, PyTorch used for model conversion, and other installed dependencies retain their respective licenses. PyTorch and the upstream training source are not required to run the packaged service. Runtime package versions are listed in `requirements.lock.txt`.
