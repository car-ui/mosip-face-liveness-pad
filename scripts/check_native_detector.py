"""Check portable native YuNet against OpenCV on identical real-model fixture inputs."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--onnx-jar", type=Path, required=True)
    parser.add_argument("--opencv-jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = ROOT / "assets/models/face_detection_yunet_2023mar.onnx"
    reference = cv2.FaceDetectorYN.create(str(model), "", (640, 640), .9, .3, 5000)
    photo = cv2.imread(str(ROOT / "tests/sample_images/astronaut.png"))
    small = cv2.resize(photo, (320, 320))
    inputs = [np.zeros((480, 640, 3), np.uint8), photo, cv2.flip(photo, 1),
              np.concatenate([small, small], axis=1)]
    for width, height in ((160, 200), (320, 240), (480, 640), (1280, 720)):
        inputs.append(cv2.resize(photo, (width, height)))
    cases = []
    for index, image in enumerate(inputs):
        h, w = image.shape[:2]
        scale = min(640 / w, 640 / h)
        width, height = int(round(w * scale)), int(round(h * scale))
        canvas = np.zeros((640, 640, 3), np.uint8)
        canvas[:height, :width] = cv2.resize(image, (width, height))
        _, detected = reference.detect(canvas)
        rows = []
        for face in detected if detected is not None else []:
            x, y, bw, bh = face[:4]
            x1, y1 = max(0, int(x / (width / w))), max(0, int(y / (height / h)))
            x2, y2 = min(w, int((x + bw) / (width / w))), min(h, int((y + bh) / (height / h)))
            if x2 > x1 and y2 > y1:
                rows.append([x1, y1, x2 - x1, y2 - y1, float(face[-1])])
        path = output / f"fixture-{index}.png"
        cv2.imwrite(str(path), image)
        cases.append("\t".join([str(path), str(len(rows)), *(",".join(map(str, row)) for row in rows)]))
    specification = output / "cases.tsv"
    specification.write_text("\n".join(cases) + "\n")
    suffix = ".exe" if os.name == "nt" else ""
    classpath = os.pathsep.join(map(str, [output, args.onnx_jar.resolve(), args.opencv_jar.resolve()]))
    sources = [ROOT / "integrations/native/common/io/mosip/facepad/NativeYuNet.java",
               ROOT / "integrations/native/tests/NativeYuNetCheck.java"]
    subprocess.run([str(args.java_home / "bin" / f"javac{suffix}"), "--release", "8", "-cp", classpath,
                    "-d", str(output), *map(str, sources)], check=True)
    result = subprocess.run([str(args.java_home / "bin" / f"java{suffix}"), "-Xmx192m",
                             f"-Djava.io.tmpdir={output}", "-cp", classpath,
                             "NativeYuNetCheck", str(model), str(specification)], capture_output=True,
                            text=True, timeout=120)
    (output / "native-detector-check.log").write_text(result.stdout + result.stderr)
    print(result.stdout)
    if result.returncode:
        raise RuntimeError(f"Native detector comparison failed; inspect {output}")
    (output / "result.json").write_text(json.dumps({"cases": len(inputs),
        "scope": "Real-model detector parity and invalid-input checks; no physical PAD accuracy claim",
        "result": result.stdout.strip()}, indent=2))


if __name__ == "__main__":
    main()
