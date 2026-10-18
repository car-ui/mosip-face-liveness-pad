# Third-party notices

## MiniFASNet research PAD model

The exported MiniFASNet V2 ONNX model is derived from `minivision-ai/Silent-Face-Anti-Spoofing` at commit `b6d5f04ad78778917853b25c778acef6d5626d15`. The upstream repository declares Apache License 2.0. A copy is retained at `third_party/Silent-Face-Anti-Spoofing-LICENSE.txt`. The export changes serialization to ONNX and does not claim new training or the upstream ensemble's performance. See `assets/models/minifasnet_v2.onnx.json` for checksums and `docs/MODEL_CARD.md` for preprocessing and limits.

## Native inference runtimes

Android uses ONNX Runtime 1.23.2 under the MIT license and OpenCV 4.12.0 under Apache License 2.0. Copies of the upstream notices are retained in `third_party/ONNX-Runtime-LICENSE.txt` and `third_party/OpenCV-LICENSE.txt`. The native preparer installs both notices alongside the model in application resources, since the Android client's general packaging rules exclude some META-INF license files. Desktop uses ONNX Runtime 1.30.0 and OpenCV 4.5.3-4; those packages retain their own notices. The Haar cascade also retains its Intel/OpenCV notice in the XML file.

## Font, landmark model and image fixture

The self-contained pitch embeds the Manrope variable font from [Google Fonts](https://github.com/google/fonts/tree/main/ofl/manrope). It uses the SIL Open Font License. A copy is retained at `third_party/Manrope-OFL.txt`.

The inherited `assets/models/face_landmarker.task` exactly matches Google's [Face Landmarker float16 version 1 download](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task), SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. This verifies byte provenance; it does not grant new rights or establish the model's distribution terms. Review the model-specific terms before submission.

The inherited photographs with undocumented provenance have been replaced by a public-domain NASA photograph distributed by scikit-image. See `tests/sample_images/README.md` for its source, attribution, checksum and test scope. A recorded face photo is not a bona fide live-person sample.

OpenCV, MediaPipe, ONNX Runtime, NumPy, FastAPI, PyTorch used for model conversion, and other installed dependencies retain their respective licenses. PyTorch and the upstream training source are not required to run the packaged service. Runtime package versions are listed in `requirements.lock.txt`.
