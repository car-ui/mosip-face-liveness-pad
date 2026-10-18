"""Compare actual Java landmark inference with Python ORT and check rejection paths."""
import argparse
import os
from pathlib import Path
import subprocess
import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def run(java_home: Path, onnx_jar: Path, opencv_jar: Path, output: Path):
    output = output.resolve(); output.mkdir(parents=True, exist_ok=True)
    options = ort.SessionOptions(); options.intra_op_num_threads = 1; options.inter_op_num_threads = 1
    engine = ort.InferenceSession(str(ROOT / "assets/models/facemesh_v2.onnx"), options, providers=["CPUExecutionProvider"])
    image = Image.open(ROOT / "tests/sample_images/astronaut.png").convert("RGB")
    crop = image.crop((147,39,300,192)).resize((256,256), Image.Resampling.BILINEAR)
    tensor = np.asarray(crop, dtype=np.float32)[None] / 255
    expected = engine.run(["Identity"], {engine.get_inputs()[0].name: tensor})[0]
    input_file, expected_file = output / "input.f32", output / "expected.f32"
    tensor.astype("<f4").tofile(input_file); expected.astype("<f4").tofile(expected_file)
    del engine
    suffix = ".exe" if os.name == "nt" else ""
    classpath = os.pathsep.join(str(p.resolve()) for p in [output, onnx_jar, opencv_jar])
    sources = sorted((ROOT / "integrations/native/common/io/mosip/facepad").glob("*.java"))
    sources.append(ROOT / "integrations/native/tests/NativeLandmarkEngineCheck.java")
    subprocess.run([str(java_home / "bin" / ("javac" + suffix)), "-J-Xmx192m", "--release", "8", "-cp", classpath,
                    "-d", str(output), *map(str,sources)], check=True)
    result = subprocess.run([str(java_home / "bin" / ("java" + suffix)), "-Xmx128m", "-XX:+UseSerialGC",
                             "-Djava.io.tmpdir=" + str(output), "-cp", classpath, "NativeLandmarkEngineCheck",
                             str(ROOT), str(input_file), str(expected_file)], text=True, capture_output=True, timeout=120)
    (output / "native-landmark-check.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout)
    if result.returncode:
        raise SystemExit(f"Landmark check failed; inspect {output / 'native-landmark-check.log'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--onnx-jar", type=Path, required=True)
    parser.add_argument("--opencv-jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/local/native-landmarks")
    a = parser.parse_args()
    run(a.java_home, a.onnx_jar, a.opencv_jar, a.output)
