"""Explicit test doubles for state-machine tests, separate from image inference tests."""
import numpy as np
import pytest
from src.core.config import PADVerdict
from src.core.face_detector import DetectedFace, QualityMetrics
from src.core.passive_pad import PADResult, HeuristicPADBackend
from src.core.pipeline import LivenessPipeline
from src.core.session_pad import SessionPADGate
from src.devices.base import VideoFrame


@pytest.fixture(autouse=True)
def release_native_detectors(monkeypatch):
    from src.core.active_liveness import ActiveLivenessDetector
    created = []
    original = ActiveLivenessDetector.__init__
    def initialize(self, *args, **kwargs):
        original(self, *args, **kwargs)
        created.append(self)
    monkeypatch.setattr(ActiveLivenessDetector, "__init__", initialize)
    yield
    for detector in created:
        detector.close()


@pytest.fixture
def controlled_pipeline(monkeypatch):
    # Avoid native inference in control-flow tests. Real detector tests remain separate.
    monkeypatch.setattr("src.core.pipeline.ActiveLivenessDetector._setup_landmarker", lambda self: None)
    pipeline = LivenessPipeline()
    # Legacy control-flow tests use a single-observation gate. Dedicated video
    # evidence tests exercise the real multi-frame policy and clock separately.
    pipeline.pad_gate = SessionPADGate(attack_frames=1, attack_seconds=0,
                                       clear_frames=1, clear_seconds=0)
    face = DetectedFace(80, 50, 160, 140, .99)
    monkeypatch.setattr(pipeline.quality_assessor, "detect_faces", lambda *a, **k: [face])
    monkeypatch.setattr(pipeline.quality_assessor, "assess_quality", lambda *a: QualityMetrics(
        True, 1, 100, False, 120, False, .3, True))
    counter = [0]

    def telemetry(image, state=None):
        counter[0] += 1
        return {"landmarks_detected": True, "ear": .3, "smile_score": 0,
                "yaw": 0, "pitch": 0, "face_center": (150 + counter[0] % 4, 100)}, state

    monkeypatch.setattr(pipeline.active_detector, "process_frame", telemetry)
    monkeypatch.setattr(pipeline.pad_detector, "evaluate_passive_liveness", lambda *a: PADResult(
        PADVerdict.BONA_FIDE_LIVE, True, .99, .98, False, None, "TEST_DOUBLE",
        model_metadata=HeuristicPADBackend().get_metadata()))
    pipeline.reset()
    return pipeline


@pytest.fixture
def controlled_attack_pipeline(controlled_pipeline, monkeypatch):
    """Inject an attack verdict to test rejection handling, not image accuracy."""
    pipeline = controlled_pipeline
    monkeypatch.setattr(pipeline.pad_detector, "evaluate_passive_liveness", lambda *a: PADResult(
        PADVerdict.PRESENTATION_ATTACK, False, .01, .98, True, "TEST_FIXTURE", "TEST_DOUBLE"))
    return pipeline


@pytest.fixture
def valid_frame():
    return VideoFrame(1, 1, np.full((240, 320, 3), 120, np.uint8), 320, 240)
