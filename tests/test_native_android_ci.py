import pytest

from scripts.run_native_android_ci import require_passed
from scripts import run_native_android_ci as native_ci
import zipfile


def test_complete_android_success():
    require_passed("Time: 1.2\nOK (6 tests)\n\nINSTRUMENTATION_CODE: -1\n")


@pytest.mark.parametrize("output", [
    "INSTRUMENTATION_CODE: 0\n",
    "OK (6 tests)\n",
    "OK (5 tests)\nINSTRUMENTATION_CODE: -1\n",
    "OK (6 tests)\nFAILURES!!!\nINSTRUMENTATION_CODE: -1\n",
    "OK (6 tests)\nINSTRUMENTATION_FAILED: process crashed\nINSTRUMENTATION_CODE: -1\n",
    "OK (6 tests)\nINSTRUMENTATION_ABORTED\nINSTRUMENTATION_CODE: -1\n",
])
def test_exit_status_or_partial_output_cannot_claim_success(output):
    with pytest.raises(ValueError, match="complete passing"):
        require_passed(output)


@pytest.mark.parametrize("fault", [None, "missing_detector", "changed_detector", "missing_detector_notice", "duplicate"])
def test_apk_verification_includes_current_detector(tmp_path, monkeypatch, fault):
    monkeypatch.setattr(native_ci, "ROOT", tmp_path)
    model_dir = tmp_path / "assets/models"
    model_dir.mkdir(parents=True)
    models = ["minifasnet_v2.onnx", "facemesh_v2.onnx", "face_detection_yunet_2023mar.onnx"]
    for name in models:
        (model_dir / name).write_bytes(("verified-" + name).encode())
    apk = tmp_path / "test.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        for name in models:
            if fault == "missing_detector" and "yunet" in name:
                continue
            payload = (model_dir / name).read_bytes()
            if fault == "changed_detector" and "yunet" in name:
                payload += b"changed"
            archive.writestr("assets/facepad/" + name, payload)
        for name in ["CAMERA-SBI-LICENSE.txt", "LANDMARK-MODEL-LICENSE.txt", "MODEL-LICENSE.txt",
                     "ONNX-Runtime-LICENSE.txt", "OpenCV-LICENSE.txt", "FACE-DETECTOR-LICENSE.txt"]:
            if fault == "missing_detector_notice" and name == "FACE-DETECTOR-LICENSE.txt":
                continue
            archive.writestr("assets/facepad/" + name, b"notice" * 30)
        if fault == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate"):
                archive.writestr("assets/facepad/minifasnet_v2.onnx", b"second entry")
    if fault is None:
        native_ci.verify_apk(apk)
    else:
        with pytest.raises(ValueError):
            native_ci.verify_apk(apk)
