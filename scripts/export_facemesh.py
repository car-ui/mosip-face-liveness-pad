"""Convert the pinned MediaPipe landmark submodel and compare TFLite/ONNX outputs.

Conversion-only dependencies: tensorflow-cpu==2.15.1, tf2onnx==1.16.1,
onnx==1.17.0, onnxruntime==1.23.2, numpy==1.26.4, pillow==11.3.0.
Not service dependencies. Serialized graph hashes can differ across exports;
review the exact artifact and its parity report before changing the runtime pin.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def export(output: Path):
    import numpy as np
    import onnxruntime as ort
    import tensorflow as tf
    output.mkdir(parents=True, exist_ok=True)
    bundle = (ROOT / "assets/models/face_landmarker.task").read_bytes()
    if hashlib.sha256(bundle).hexdigest() != BUNDLE_SHA:
        raise ValueError("Unexpected landmark bundle checksum")
    source = output / "face_landmarks_detector.tflite"
    with zipfile.ZipFile(ROOT / "assets/models/face_landmarker.task") as archive:
        source.write_bytes(archive.read(source.name))
    model = output / "facemesh_v2.onnx"
    subprocess.run([sys.executable, "-m", "tf2onnx.convert", "--tflite", str(source),
                    "--output", str(model), "--opset", "17"], check=True)
    reference = tf.lite.Interpreter(model_path=str(source), num_threads=1)
    reference.allocate_tensors()
    options = ort.SessionOptions(); options.intra_op_num_threads = 1; options.inter_op_num_threads = 1
    converted = ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(42)
    cases = [("zeros", np.zeros((1,256,256,3), np.float32)), ("ones", np.ones((1,256,256,3), np.float32))]
    cases += [(f"random_{i}", rng.random((1,256,256,3), dtype=np.float32)) for i in range(5)]
    # Pillow is used only to read the attributed recorded fixture for parity.
    from PIL import Image
    image = Image.open(ROOT / "tests/sample_images/astronaut.png").convert("RGB")
    image = image.crop((147,39,300,192)).resize((256,256), Image.Resampling.BILINEAR)
    cases.append(("NASA_photo_crop", np.asarray(image, dtype=np.float32)[None] / 255))
    comparisons = []
    for label, value in cases:
        reference.set_tensor(reference.get_input_details()[0]["index"], value); reference.invoke()
        expected = {t["name"]: reference.get_tensor(t["index"]) for t in reference.get_output_details()}
        actual = converted.run(None, {converted.get_inputs()[0].name: value})
        for spec, result in zip(converted.get_outputs(), actual):
            error = float(np.max(np.abs(result - expected[spec.name])))
            if not np.allclose(result, expected[spec.name], atol=.002, rtol=.001):
                raise ValueError(f"Conversion mismatch {label} {spec.name}: {error}")
            comparisons.append({"case": label, "output": spec.name, "max_abs_error": error})
    report = {"bundle_sha256": BUNDLE_SHA, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "onnx_sha256": hashlib.sha256(model.read_bytes()).hexdigest(), "opset": 17,
              "comparisons": comparisons, "scope": "Serialization parity only; no liveness or action accuracy measurement"}
    (output / "facemesh-parity.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS {len(comparisons)} output comparisons; model SHA-256 {report['onnx_sha256']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    export(parser.parse_args().output)
