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


def require_passed(text: str, expected: int = 6):
    if (not re.search(rf"^OK \({expected} tests\)\s*$", text, re.MULTILINE)
            or "FAILURES!!!" in text or "INSTRUMENTATION_FAILED" in text
            or "INSTRUMENTATION_ABORTED" in text
            or not re.search(r"^INSTRUMENTATION_CODE: -1\s*$", text, re.MULTILINE)):
        raise ValueError("Native instrumentation did not report a complete passing suite")


def verify_apk(path: Path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("APK archive integrity failure")
        for name in ["minifasnet_v2.onnx", "facemesh_v2.onnx"]:
            expected = hashlib.sha256((ROOT / "assets/models" / name).read_bytes()).digest()
            if hashlib.sha256(archive.read("assets/facepad/" + name)).digest() != expected:
                raise ValueError(f"APK model mismatch: {name}")
        for name in ["CAMERA-SBI-LICENSE.txt", "LANDMARK-MODEL-LICENSE.txt", "MODEL-LICENSE.txt",
                     "ONNX-Runtime-LICENSE.txt", "OpenCV-LICENSE.txt"]:
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
              "serial": args.serial, "avd": args.avd_name, "tests": 6, "status": "RUNNING", "apks": []}
    for path in [args.apk, args.test_apk]:
        report["apks"].append({"file": path.name, "bytes": path.stat().st_size,
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    result = args.output / "result.json"
    result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        for path in [args.apk, args.test_apk]:
            output = call("install", "-r", "-t", str(path.resolve()), timeout=180)
            if "Success" not in output:
                raise RuntimeError("APK installation did not succeed")
        call("shell", "pm", "grant", "nprime.reg.sbi.face", "android.permission.CAMERA")
        try:
            output = call("shell", "am", "instrument", "-w", "-r", "-e", "class",
                          "nprime.reg.sbi.googlevision.CameraOwnerPadTest",
                          "nprime.reg.sbi.face.test/androidx.test.runner.AndroidJUnitRunner", timeout=300)
        except subprocess.TimeoutExpired as failure:
            output = failure.output or b""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            (args.output / "instrumentation.txt").write_text(output, encoding="utf-8")
            call("shell", "am", "force-stop", "nprime.reg.sbi.face")
            raise RuntimeError("Native instrumentation exceeded five minutes") from failure
        log = args.output / "instrumentation.txt"
        log.write_text(output, encoding="utf-8", newline="\n")
        require_passed(output)
        report.update(status="PASS", result_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    except Exception:
        report["status"] = "FAIL"
        raise
    finally:
        result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        try:
            (args.output / "logcat.txt").write_text(call("logcat", "-d", "-s", "AndroidRuntime", "TestRunner"), encoding="utf-8")
        except Exception:
            pass
    print("PASS six reference SBI tests; raw output and exact APK checksums saved")


if __name__ == "__main__":
    main()
