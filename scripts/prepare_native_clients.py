"""Apply native checkpoints to clean, exact upstream revisions. Never resets a checkout."""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "android": "8f4643a694f3b5e66e0491f077a8630ab5667658",
    "desktop": "935306e2fd38bff2803697468e595026b1d18cec",
}


def prepare(platform: str, checkout: Path):
    checkout = checkout.resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=checkout, text=True).strip()
    if git("rev-parse", "HEAD") != PINS[platform]:
        raise SystemExit(f"Expected {platform} upstream {PINS[platform]}")
    if git("status", "--porcelain"):
        raise SystemExit("Use a clean checkout; existing changes will not be overwritten")
    base = ROOT / "integrations/native"
    patch = base / f"{platform}.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=checkout, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=checkout, check=True)
    module = checkout / ("android/app/src/main" if platform == "android" else "registration/registration-client/src/main")
    shutil.copytree(base / "common", module / "java", dirs_exist_ok=True)
    shutil.copytree(base / platform, module / "java", dirs_exist_ok=True)
    resources = module / ("assets/facepad" if platform == "android" else "resources/facepad")
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "assets/models/minifasnet_v2.onnx", resources / "minifasnet_v2.onnx")
    shutil.copyfile(ROOT / "assets/models/minifasnet_v2.onnx.json", resources / "minifasnet_v2.onnx.json")
    shutil.copyfile(ROOT / "third_party/Silent-Face-Anti-Spoofing-LICENSE.txt", resources / "MODEL-LICENSE.txt")
    shutil.copyfile(base / "assets/haarcascade_frontalface_default.xml", resources / "haarcascade_frontalface_default.xml")
    if platform == "android":
        tests = module.parent / "androidTest"
        shutil.copytree(base / "android-test", tests / "java", dirs_exist_ok=True)
        (tests / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base / "tests/fixtures/blank-face.iso", tests / "assets/blank-face.iso")
    print(f"Prepared {platform} {PINS[platform]} in {checkout}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=PINS)
    parser.add_argument("checkout", type=Path)
    args = parser.parse_args()
    prepare(args.platform, args.checkout)
