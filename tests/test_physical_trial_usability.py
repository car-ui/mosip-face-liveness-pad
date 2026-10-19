"""Physical-trial regressions with explicit detector and clock doubles."""
from types import SimpleNamespace
import time

import numpy as np
import pytest

from src.core.face_detector import FaceQualityAssessor
from src.core.config import ChallengeType, LivenessDecision
from src.core.active_liveness import ChallengeState
from src.core.pipeline import PipelineState, PipelineStepResult
from src.ui.desktop_client import DesktopRegistrationClient


@pytest.mark.parametrize("haar,landmarks,count", [
    ([], [(80, 50, 100, 100)], 1),
    ([(40, 25, 50, 50)], [(80, 50, 100, 100)], 1),
    ([(5, 5, 20, 20)], [(180, 80, 100, 100)], 2),
    ([], [(80, 50, 100, 100), (90, 50, 100, 100)], 2),
    ([], [], 0),
])
def test_fresh_landmarks_supplement_haar_without_hiding_second_face(haar, landmarks, count):
    assessor = FaceQualityAssessor()
    assessor.face_cascade = SimpleNamespace(detectMultiScale=lambda *a, **k: haar)
    frame = np.zeros((240, 320, 3), np.uint8)
    assert len(assessor.detect_faces(frame, known_box=(80, 50, 100, 100),
                                    landmark_boxes=landmarks)) == count
    # A subsequent frame must never inherit the landmark box.
    if not haar:
        assert assessor.detect_faces(frame) == []


def test_main_action_stays_visible_and_feedback_has_reading_time(monkeypatch):
    client = DesktopRegistrationClient.__new__(DesktopRegistrationClient)
    client.pipeline = SimpleNamespace(session_id="test")
    client._prompt_key = None
    clock = [10.0]
    monkeypatch.setattr("src.ui.desktop_client.time.monotonic", lambda: clock[0])
    challenge = ChallengeState(ChallengeType.TURN_LEFT, True, time.time(), 12,
                               False, 0, False, "Face camera first")
    result = PipelineStepResult(PipelineState.ACTIVE_CHALLENGE,
                                LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                                "", "", 0, active_challenge=challenge)
    title, detail = client._readable_prompt(result)
    challenge.feedback_message = "Now return to center"
    clock[0] += .1
    assert client._readable_prompt(result) == (title, detail)
    clock[0] += 1
    assert "Now return to center" in client._readable_prompt(result)[1]
    result.state = PipelineState.ATTACK_REJECTED
    result.status_text = "Verification incomplete"
    assert client._readable_prompt(result)[0] == "Verification incomplete"


def test_failure_reason_survives_subsequent_frames(controlled_pipeline, valid_frame, monkeypatch):
    pipeline = controlled_pipeline
    pipeline.state = PipelineState.ACTIVE_CHALLENGE
    pipeline.challenge_manager.generate_next_challenge()
    pipeline.challenge_manager.current_retry = pipeline.policy.max_retries - 1
    monkeypatch.setattr(pipeline.quality_assessor, "assess_quality", lambda *a: SimpleNamespace(
        is_acceptable=False, face_count=0, error_message="Face not detected"))
    result = pipeline.process_frame(valid_frame)
    assert result.state == PipelineState.MAX_RETRIES_EXCEEDED
    assert "Face not detected" in result.detailed_guidance
    assert pipeline.process_frame(valid_frame) is result
    pipeline.reset()
    assert pipeline._terminal_result is None
