"""Compile and execute the native ONNX parity check with explicit dependency JARs."""
import argparse
import os
from pathlib import Path
import subprocess

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]


def run(java_home: Path, onnx_jar: Path, opencv_jar: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    extension = ".exe" if os.name == "nt" else ""
    javac = java_home / "bin" / ("javac" + extension)
    java = java_home / "bin" / ("java" + extension)
    options = ort.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(ROOT / "assets/models/minifasnet_v2.onnx"), options,
                                  providers=["CPUExecutionProvider"])
    data = np.random.default_rng(17).uniform(0, 255, (1, 3, 80, 80)).astype("<f4")
    tensor = output / "parity.f32"
    data.tofile(tensor)
    logits = session.run(None, {session.get_inputs()[0].name: data})[0][0]
    probabilities = np.exp(logits - logits.max())
    probabilities /= probabilities.sum()
    expected = float(probabilities[1])
    del session
    classpath = os.pathsep.join(str(p.resolve()) for p in [output, onnx_jar, opencv_jar])
    subprocess.run([str(javac), "-J-Xmx192m", "--release", "8", "-cp", classpath,
                    "-d", str(output), str(ROOT / "integrations/native/common/io/mosip/facepad/NativePadEngine.java"),
                    str(ROOT / "integrations/native/common/io/mosip/facepad/NativeYuNet.java"),
                    str(ROOT / "integrations/native/tests/NativePadEngineCheck.java")], check=True)
    result = subprocess.run([str(java), "-Xmx128m", "-XX:+UseSerialGC", "-Djava.io.tmpdir=" + str(output),
                             "-cp", classpath, "NativePadEngineCheck", str(ROOT), str(tensor), str(expected)],
                            text=True, capture_output=True, check=True)
    (output / "native-engine-check.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--onnx-jar", type=Path, required=True)
    parser.add_argument("--opencv-jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/local/native-check")
    args = parser.parse_args()
    run(args.java_home, args.onnx_jar, args.opencv_jar, args.output)
