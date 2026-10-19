"""User-facing progress follows completed work, not a transient pose measurement."""
from types import SimpleNamespace
import time

from src.core.active_liveness import ChallengeState
from src.core.config import ChallengeType, LivenessDecision
from src.core.pipeline import PipelineState, PipelineStepResult
from src.ui.desktop_client import DesktopRegistrationClient


def client():
    instance = DesktopRegistrationClient.__new__(DesktopRegistrationClient)
    instance.pipeline = SimpleNamespace(session_id="test")
    instance._prompt_key = None
    return instance


def test_turn_progress_does_not_claim_overall_completion():
    ui = client()
    action = ChallengeState(ChallengeType.TURN_LEFT, True, time.time(), 12,
                            False, .9, True, "Return to center")
    result = PipelineStepResult(PipelineState.ACTIVE_CHALLENGE,
                                LivenessDecision.ACTIVE_CHALLENGE_REQUIRED,
                                "", "", .95, active_challenge=action,
                                completed_actions=0, required_actions=2)
    assert ui._stage_progress(result) == (0, "0/2")
    result.completed_actions = 1
    assert ui._stage_progress(result) == (.5, "1/2")
    result.state = PipelineState.CAPTURE_SUCCESS
    assert ui._stage_progress(result) == (1, "Done")


def test_recovery_explicitly_explains_cleared_progress():
    ui = client()
    result = PipelineStepResult(PipelineState.PASSIVE_LIVENESS,
                                LivenessDecision.IN_PROGRESS, "Variable message", "", .12,
                                completed_actions=0, required_actions=2, restart_count=1)
    title, detail = ui._readable_prompt(result)
    assert title == "Rechecking liveness"
    assert "cleared" in detail
    assert ui._stage_progress(result) == (0, "0/2")


def test_audit_retains_numeric_scores_while_blocking_image_buffers():
    from src.core.audit_logger import BiometricAuditLogger, AuditEventType
    import numpy as np
    event = BiometricAuditLogger(log_to_console=False).log_event(
        AuditEventType.PAD_ATTACK_DETECTED,
        details={"recent_scores": [.1, .2], "observation_count": 5,
                 "raw_frame": np.zeros((2, 2, 3), np.uint8)})
    assert event["details"]["recent_scores"] == [.1, .2]
    assert event["details"]["observation_count"] == 5
    assert "raw_frame" not in event["details"]


def test_recovery_holds_new_challenges_while_pad_still_runs(controlled_pipeline, valid_frame, monkeypatch):
    pipeline = controlled_pipeline
    now = [10.0]
    monkeypatch.setattr("src.core.pipeline.time.monotonic", lambda: now[0])
    pipeline._record_restart("test observation changed")
    pipeline.state = PipelineState.PASSIVE_LIVENESS
    result = pipeline.process_frame(valid_frame)
    assert result.status_text == "Rechecking liveness"
    assert result.restart_count == 1
    assert pipeline._passive_frames_analyzed == 0
    assert pipeline.challenge_manager.active_challenge_state is None
    now[0] = 12.1
    pipeline.process_frame(valid_frame)
    assert pipeline._passive_frames_analyzed == 1
