"""Security properties use injected scores/actions; they do not measure PAD accuracy."""
import hashlib
import json
from dataclasses import replace
import numpy as np
import pytest
from src.core.config import WorkflowType, PADMode, PADVerdict
from src.core.pipeline import PipelineState
from src.core.passive_pad import PassivePADDetector, PADResult
from src.core.face_detector import FaceQualityAssessor, QualityMetrics
from src.core.model_updater import SecureModelUpdateManager
from src.core.audit_logger import BiometricAuditLogger, AuditEventType
from src.core.metrics import OperationalMetrics


@pytest.mark.parametrize("workflow", [WorkflowType.OPERATOR_AUTHENTICATION, WorkflowType.SUPERVISOR_AUTHENTICATION])
def test_high_passive_score_cannot_skip_authentication_challenges(controlled_pipeline, valid_frame, workflow):
    p = controlled_pipeline
    p.set_workflow(workflow)
    for _ in range(26):
        result = p.process_frame(valid_frame)
    assert result.state == PipelineState.ACTIVE_CHALLENGE
    assert result.captured_face_image is None


@pytest.mark.parametrize("verdict", [PADVerdict.PRESENTATION_ATTACK, PADVerdict.PROCESSING_ERROR])
def test_active_action_never_overrides_pad_failure(controlled_pipeline, valid_frame, monkeypatch, verdict):
    p = controlled_pipeline
    p.state = PipelineState.ACTIVE_CHALLENGE
    p.challenge_manager.generate_next_challenge().is_completed = True
    monkeypatch.setattr(p.pad_detector, "evaluate_passive_liveness", lambda *a: PADResult(
        verdict, False, .01, .9, verdict == PADVerdict.PRESENTATION_ATTACK, None, "TEST_DOUBLE"))
    result = p.process_frame(valid_frame)
    assert result.state in (PipelineState.ATTACK_REJECTED, PipelineState.DEVICE_ERROR)
    assert result.captured_face_image is None


def test_terminal_attack_cannot_restart_when_face_changes(controlled_pipeline, valid_frame):
    p = controlled_pipeline
    p.state = PipelineState.ATTACK_REJECTED
    for _ in range(40):
        result = p.process_frame(valid_frame)
        assert result.state == PipelineState.ATTACK_REJECTED
        assert result.captured_face_image is None


def test_active_inference_runs_once_per_frame(controlled_pipeline, valid_frame, monkeypatch):
    p = controlled_pipeline
    p.state = PipelineState.ACTIVE_CHALLENGE
    p.challenge_manager.generate_next_challenge()
    calls = []
    original = p.active_detector.process_frame
    def counted(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(p.active_detector, "process_frame", counted)
    p.process_frame(valid_frame)
    assert len(calls) == 1


def test_face_loss_invalidates_action_and_passive_history(controlled_pipeline, valid_frame, monkeypatch):
    p = controlled_pipeline
    p.state = PipelineState.ACTIVE_CHALLENGE
    p.challenge_manager.generate_next_challenge().is_completed = True
    p.challenge_manager.completed_challenges.append(p.config.supported_challenges[0])
    monkeypatch.setattr(p.quality_assessor, "assess_quality", lambda *a: QualityMetrics(
        False, 0, 0, False, 0, False, 0, False))
    r = p.process_frame(valid_frame)
    assert r.state == PipelineState.RETRY_PENDING
    assert p.challenge_manager.completed_challenges == []
    assert p.challenge_manager.active_challenge_state is None
    assert p.temporal_buffer.analyze().frame_count == 0


def test_disabled_active_fallback_exhausts_retry_limit(controlled_pipeline, valid_frame):
    p = controlled_pipeline
    p.policy.active_liveness_enabled = False
    p.policy.passive_threshold = 1
    p.policy.max_retries = 1
    for _ in range(25):
        r = p.process_frame(valid_frame)
    assert r.state == PipelineState.MAX_RETRIES_EXCEEDED
    assert p.challenge_manager.current_retry == 1


@pytest.mark.parametrize("image", [np.zeros((20, 20), np.uint8), np.zeros((20, 20, 4), np.uint8),
                                  np.zeros((20, 20, 3), np.float32)])
def test_invalid_pixel_layout_fails_closed(controlled_pipeline, valid_frame, image):
    r = controlled_pipeline.process_frame(replace(valid_frame, image=image, width=20, height=20))
    assert r.state == PipelineState.DEVICE_ERROR
    assert r.captured_face_image is None


def test_detector_exception_fails_closed(controlled_pipeline, valid_frame, monkeypatch):
    def broken(*args):
        raise RuntimeError("sensitive internal details")
    monkeypatch.setattr(controlled_pipeline.active_detector, "process_frame", broken)
    r = controlled_pipeline.process_frame(valid_frame)
    assert r.state == PipelineState.DEVICE_ERROR
    assert "sensitive" not in r.detailed_guidance


def test_known_face_box_does_not_hide_second_face(monkeypatch):
    assessor = FaceQualityAssessor()
    class Cascade:
        def detectMultiScale(self, *a, **k):
            return [(10, 10, 50, 50), (100, 10, 50, 50)]
    monkeypatch.setattr(assessor, "face_cascade", Cascade())
    faces = assessor.detect_faces(np.zeros((240, 320, 3), np.uint8), known_box=(20, 20, 100, 100))
    assert len(faces) == 2


def test_strict_onnx_runtime_failure_never_uses_heuristics(monkeypatch):
    detector = PassivePADDetector(mode=PADMode.ONNX_ONLY)
    monkeypatch.setattr(detector._onnx_backend, "is_available", lambda: True)
    def broken(*args):
        raise RuntimeError("model runtime failed")
    monkeypatch.setattr(detector._onnx_backend, "evaluate", broken)
    monkeypatch.setattr(detector._heuristic_backend, "evaluate", lambda *a: pytest.fail("unsafe fallback"))
    r = detector.evaluate_passive_liveness(np.zeros((100, 100, 3), np.uint8), (0, 0, 100, 100))
    assert r.verdict == PADVerdict.PROCESSING_ERROR


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1, 2])
def test_nonfinite_and_out_of_range_pad_scores_cannot_pass(monkeypatch, score):
    detector = PassivePADDetector(mode=PADMode.HEURISTIC_ONLY)
    monkeypatch.setattr(detector._heuristic_backend, "evaluate", lambda *a: (score, .9, False, None, {}))
    r = detector.evaluate_passive_liveness(np.zeros((100, 100, 3), np.uint8), (0, 0, 100, 100))
    assert r.verdict == PADVerdict.PROCESSING_ERROR


def test_model_updates_require_explicit_key(tmp_path):
    with pytest.raises(ValueError):
        SecureModelUpdateManager(str(tmp_path))


def test_model_version_metadata_is_authenticated(tmp_path):
    m = SecureModelUpdateManager(str(tmp_path), signing_key=b"local-test-key")
    pkg = m.generate_signed_package("pad", "1.0.0", b"model")
    pkg.version = "999.0.0"
    assert m.install_update(pkg, "pad.onnx")[0] is False
    assert not (tmp_path / "pad.onnx").exists()


@pytest.mark.parametrize("name", ["../outside.onnx", "..\\outside.onnx", "C:\\outside.onnx", "pad.onnx:alternate"])
def test_model_update_path_cannot_escape_directory(tmp_path, name):
    m = SecureModelUpdateManager(str(tmp_path), signing_key=b"local-test-key")
    pkg = m.generate_signed_package("pad", "1.0.0", b"model")
    assert m.install_update(pkg, name)[0] is False


def test_installed_version_survives_manager_restart(tmp_path):
    key = b"local-test-key"
    m = SecureModelUpdateManager(str(tmp_path), signing_key=key)
    assert m.install_update(m.generate_signed_package("pad", "2.0.0", b"new"), "pad.onnx")[0]
    m = SecureModelUpdateManager(str(tmp_path), signing_key=key)
    assert not m.install_update(m.generate_signed_package("pad", "1.0.0", b"old"), "pad.onnx")[0]
    assert (tmp_path / "pad.onnx").read_bytes() == b"new"


def test_asymmetric_model_update_verifies_offline(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = Ed25519PrivateKey.generate()
    publisher = SecureModelUpdateManager(str(tmp_path / "publisher"), verification_key=key.public_key(), private_key=key)
    receiver = SecureModelUpdateManager(str(tmp_path / "receiver"), verification_key=key.public_key())
    pkg = publisher.generate_signed_package("pad", "1.0.0", b"offline-model")
    assert receiver.install_update(pkg, "pad.onnx")[0]
    pkg.model_name = "different-model"
    assert not receiver.install_update(pkg, "other.onnx")[0]


@pytest.mark.parametrize("version", ["1", "1.2", "1.2.3.4", "-1.0.0", "1.0.0-rc1", "x.y.z"])
def test_invalid_versions_rejected(tmp_path, version):
    m = SecureModelUpdateManager(str(tmp_path), signing_key=b"local-test-key")
    assert not m.validate_version(version, None)


def test_nested_biometrics_are_removed_and_audit_chain_links():
    audit = BiometricAuditLogger(log_to_console=False)
    a = audit.log_event(AuditEventType.QUALITY_CHECK, details={"nested": {
        "image": "base64-sensitive", "residentId": "private", "buffer": b"private",
        "values": [np.ones((2, 2))], "score": .8}})
    b = audit.log_event(AuditEventType.CAPTURE_REJECTED)
    assert "sensitive" not in json.dumps(a)
    assert "private" not in json.dumps(a)
    assert b["previousHash"] == a["entryHash"]
    digest = a.pop("entryHash")
    assert hashlib.sha256(json.dumps(a, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == digest


def test_anonymous_metrics_use_completed_sessions():
    m = OperationalMetrics()
    assert m.snapshot()["averageCaptureSeconds"] is None
    m.record("SUCCESS", 2, 0, 1)
    m.record("TIMEOUT", 4, 1, 3)
    r = m.snapshot()
    assert r["sessions"] == 2 and r["averageCaptureSeconds"] == 3
    assert r["retryRate"] == .5 and r["failureRate"] == .5
    assert r["averageChallengeSeconds"] == 2
