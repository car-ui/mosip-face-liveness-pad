"""Check prepared native source/assets without changing a checkout or its Git index."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_native_clients import PINS

MODULES = {"desktop": "registration/registration-client/src/main", "android": "android/app/src/main",
           "camera-sbi": "app/src/main"}


def expected_files(root, platform, checkout):
    base = root / "integrations/native"
    module = checkout / MODULES[platform]
    pairs = []
    for group in ("common", platform):
        sources = sorted((base / group).rglob("*.java"))
        if not sources:
            raise ValueError(f"Native source group is empty: {group}")
        pairs.extend((source, module / "java" / source.relative_to(base / group)) for source in sources)
    resources = module / ("resources/facepad" if platform == "desktop" else "assets/facepad")
    for name in ("minifasnet_v2.onnx", "facemesh_v2.onnx", "face_detection_yunet_2023mar.onnx"):
        for suffix in ("", ".json"):
            pairs.append((root / "assets/models" / (name + suffix), resources / (name + suffix)))
    licenses = {"Silent-Face-Anti-Spoofing-LICENSE.txt": "MODEL-LICENSE.txt",
                "MediaPipe-LICENSE.txt": "LANDMARK-MODEL-LICENSE.txt", "YuNet-LICENSE.txt": "FACE-DETECTOR-LICENSE.txt",
                "ONNX-Runtime-LICENSE.txt": "ONNX-Runtime-LICENSE.txt", "OpenCV-LICENSE.txt": "OpenCV-LICENSE.txt"}
    if platform == "camera-sbi":
        licenses["android-camera-mds-MPL-2.0.txt"] = "CAMERA-SBI-LICENSE.txt"
    pairs.extend((root / "third_party" / source, resources / target) for source, target in licenses.items())
    pairs.append((base / "assets/haarcascade_frontalface_default.xml", resources / "haarcascade_frontalface_default.xml"))
    if platform in ("android", "camera-sbi"):
        group = "android-test" if platform == "android" else "camera-sbi-test"
        sources = sorted((base / group).rglob("*.java"))
        if not sources:
            raise ValueError(f"Native source group is empty: {group}")
        pairs.extend((source, module.parent / "androidTest/java" / source.relative_to(base / group))
                     for source in sources)
        pairs.append((root / "tests/sample_images/astronaut.png", module.parent / "androidTest/assets/astronaut.png"))
        for name in ("blank-face.iso", "portrait-face.iso") if platform == "android" else ("blank-face.iso",):
            pairs.append((base / "tests/fixtures" / name, module.parent / "androidTest/assets" / name))
    if platform == "camera-sbi":
        group = base / "camera-sbi-debug"
        sources = sorted(source for source in group.rglob("*") if source.is_file())
        if not sources:
            raise ValueError("Native source group is empty: camera-sbi-debug")
        pairs.extend((source, module.parent / "debug" / source.relative_to(group))
                     for source in sources)
    return pairs


def digest(path):
    if path.suffix in (".java", ".xml", ".json", ".txt"):
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_copies(root, platform, checkout):
    records, mismatches = [], []
    for source, target in expected_files(root, platform, checkout):
        expected = digest(source)
        actual = digest(target) if target.is_file() else None
        relative = target.relative_to(checkout).as_posix()
        records.append({"path": relative, "sha256": expected})
        if actual != expected:
            mismatches.append(relative)
    return records, mismatches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=PINS)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    pin = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    records, mismatches = verify_copies(ROOT, args.platform, checkout)
    patch = subprocess.run(["git", "apply", "--reverse", "--check", str(ROOT / "integrations/native" / (args.platform + ".patch"))],
                           cwd=checkout, capture_output=True, text=True)
    passed = pin == PINS[args.platform] and not mismatches and patch.returncode == 0
    report = {"status": "PASS" if passed else "FAIL", "platform": args.platform, "upstreamCommit": pin,
              "patchPresent": patch.returncode == 0, "filesChecked": len(records), "mismatches": mismatches,
              "fingerprints": records, "textLineEndings": "LF",
              "scope": "Prepared generated source/assets and patch hunks. Not a build, full upstream-content attestation or physical validation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']} {args.platform}: {len(records)} prepared files; {len(mismatches)} mismatches; patch present={report['patchPresent']}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
