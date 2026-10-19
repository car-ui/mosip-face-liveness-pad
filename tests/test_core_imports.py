"""Offline tools must not initialize the vision stack just by importing their package."""
from pathlib import Path
import subprocess
import sys


def test_offline_update_and_configuration_import_without_vision_libraries():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", "\n".join([
        "import sys",
        "from src.core import LivenessConfig, WorkflowType",
        "from src.core.model_updater import SecureModelUpdateManager",
        "assert LivenessConfig().get_policy(WorkflowType.RESIDENT_REGISTRATION)",
        "assert not {'cv2', 'mediapipe', 'onnxruntime', 'numpy'} & sys.modules.keys()",
        "print('PASS offline imports without vision runtimes')",
    ])], cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "PASS offline imports" in result.stdout


def test_public_core_exports_preserve_class_identity():
    import src.core as core
    from src.core.pipeline import LivenessPipeline
    from src.core.face_detector import DetectedFace
    assert core.LivenessPipeline is LivenessPipeline
    assert core.DetectedFace is DetectedFace
    assert set(core.__all__).issubset(dir(core))
