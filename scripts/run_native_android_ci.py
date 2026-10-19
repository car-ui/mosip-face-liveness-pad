"""Run reference SBI instrumentation only on the explicitly named isolated emulator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def stream_sha256(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def file_sha256(path: Path):
    with path.open("rb") as stream:
        return stream_sha256(stream)


def require_passed(text: str, expected: int = 6):
    if (not re.search(rf"^OK \({expected} tests\)\s*$", text, re.MULTILINE)
            or "FAILURES!!!" in text or "INSTRUMENTATION_FAILED" in text
            or "INSTRUMENTATION_ABORTED" in text
            or not re.search(r"^INSTRUMENTATION_CODE: -1\s*$", text, re.MULTILINE)):
        raise ValueError("Native instrumentation did not report a complete passing suite")


def verify_apk(path: Path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate APK archive entry")
        models = ["minifasnet_v2.onnx", "facemesh_v2.onnx", "face_detection_yunet_2023mar.onnx"]
        notices = ["CAMERA-SBI-LICENSE.txt", "LANDMARK-MODEL-LICENSE.txt", "MODEL-LICENSE.txt",
                   "ONNX-Runtime-LICENSE.txt", "OpenCV-LICENSE.txt", "FACE-DETECTOR-LICENSE.txt"]
        required = {"assets/facepad/" + name for name in models + notices}
        if not required.issubset(set(names)):
            raise ValueError("APK is missing a current model or runtime notice")
        if archive.testzip() is not None:
            raise ValueError("APK archive integrity failure")
        for name in models:
            expected = file_sha256(ROOT / "assets/models" / name)
            with archive.open("assets/facepad/" + name) as stream:
                actual = stream_sha256(stream)
            if actual != expected:
                raise ValueError(f"APK model mismatch: {name}")
        for name in notices:
            if len(archive.read("assets/facepad/" + name)) < 100:
                raise ValueError(f"Missing runtime notice: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--avd-name", required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--test-apk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adb = shutil.which("adb")
    if not adb or not re.fullmatch(r"emulator-\d+", args.serial):
        raise SystemExit("A named isolated Android emulator and adb are required")
    prefix = [adb, "-s", args.serial]

    def call(*command, timeout=90):
        return subprocess.check_output([*prefix, *command], text=True, stderr=subprocess.STDOUT,
                                       timeout=timeout)

    names = call("emu", "avd", "name").splitlines()
    if args.avd_name not in names:
        raise SystemExit("Emulator name differs from the explicit test target; refusing installation")
    if call("shell", "getprop", "sys.boot_completed").strip() != "1":
        raise SystemExit("Test emulator has not finished booting")
    args.output.mkdir(parents=True, exist_ok=True)
    verify_apk(args.apk)
    report = {"scope": "Reference SBI, camera-disabled emulator; no human actions, physical attacks or production PKI",
              "serial": args.serial, "avd": args.avd_name, "tests": 8, "status": "RUNNING", "apks": []}
    for path in [args.apk, args.test_apk]:
        report["apks"].append({"file": path.name, "bytes": path.stat().st_size,
                               "sha256": file_sha256(path)})
    result = args.output / "result.json"
    result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        for path in [args.apk, args.test_apk]:
            output = call("install", "-r", "-t", str(path.resolve()), timeout=180)
            if "Success" not in output:
                raise RuntimeError("APK installation did not succeed")
        call("shell", "pm", "grant", "nprime.reg.sbi.face", "android.permission.CAMERA")
        log = args.output / "instrumentation.txt"
        try:
            with log.open("w", encoding="utf-8", newline="\n") as stream:
                subprocess.run([*prefix, "shell", "am", "instrument", "-w", "-r", "-e", "class",
                                "nprime.reg.sbi.googlevision.CameraOwnerPadTest,nprime.reg.sbi.googlevision.PhysicalPadHarnessTest",
                                "nprime.reg.sbi.face.test/androidx.test.runner.AndroidJUnitRunner"],
                               stdout=stream, stderr=subprocess.STDOUT, text=True, timeout=300, check=True)
        except subprocess.TimeoutExpired as failure:
            call("shell", "am", "force-stop", "nprime.reg.sbi.face")
            raise RuntimeError("Native instrumentation exceeded five minutes") from failure
        require_passed(log.read_text(encoding="utf-8"), 8)
        report.update(status="PASS", result_sha256=file_sha256(log))
    except Exception:
        report["status"] = "FAIL"
        raise
    finally:
        result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        try:
            (args.output / "logcat.txt").write_text(call("logcat", "-d", "-s", "AndroidRuntime", "TestRunner"), encoding="utf-8")
        except Exception:
            pass
    print("PASS eight reference SBI/debug harness tests; raw output and exact APK checksums saved")


if __name__ == "__main__":
    main()
