"""Video decision policy tests with explicit scores/clocks, not accuracy claims."""
from src.core.config import PADVerdict
from src.core.session_pad import SessionPADGate, EvidenceState
import pytest


@pytest.mark.parametrize("field,value", [
    ("attack_frames", 1.5), ("clear_frames", True),
    ("attack_seconds", float("nan")), ("clear_seconds", float("inf")),
    ("max_gap_seconds", float("nan")), ("max_wait_seconds", float("nan")),
    ("max_wait_seconds", "10"),
])
def test_invalid_policy_values_cannot_disable_bounded_collection(field, value):
    with pytest.raises(ValueError, match="policy"):
        SessionPADGate(**{field: value})


@pytest.mark.parametrize("timestamp", [None, "1", True, float("nan"), float("inf")])
def test_invalid_observation_clock_returns_terminal_error(timestamp):
    gate = SessionPADGate()
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, timestamp).state == EvidenceState.ERROR
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, 1).state == EvidenceState.ERROR


def test_single_low_frame_blocks_but_does_not_finish_trial():
    gate = SessionPADGate()
    assert gate.observe(PADVerdict.PRESENTATION_ATTACK, 0).state == EvidenceState.COLLECTING
    assert gate.observe(PADVerdict.UNCERTAIN, .1).state == EvidenceState.COLLECTING
    for now in (.2, .3, .4):
        assert gate.observe(PADVerdict.UNCERTAIN, now).state == EvidenceState.COLLECTING
    assert gate.observe(PADVerdict.UNCERTAIN, .5).state == EvidenceState.CLEAR


def test_sustained_attack_requires_frame_count_and_elapsed_time():
    gate = SessionPADGate()
    for now in (0, .05, .1, .15, .2):
        assert gate.observe(PADVerdict.PRESENTATION_ATTACK, now).state == EvidenceState.COLLECTING
    assert gate.observe(PADVerdict.PRESENTATION_ATTACK, .6).state == EvidenceState.REJECTED
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, .7).state == EvidenceState.REJECTED


def test_high_history_cannot_average_away_a_new_attack():
    gate = SessionPADGate()
    for now in (0, .1, .2, .3, .4):
        result = gate.observe(PADVerdict.BONA_FIDE_LIVE, now)
    assert result.state == EvidenceState.CLEAR
    assert gate.observe(PADVerdict.PRESENTATION_ATTACK, .5).state == EvidenceState.COLLECTING
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, .6).state == EvidenceState.COLLECTING


def test_sparse_frames_cannot_satisfy_a_streak():
    gate = SessionPADGate()
    for now in (0, 2, 4, 6, 8):
        assert gate.observe(PADVerdict.BONA_FIDE_LIVE, now).state == EvidenceState.COLLECTING
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, 10.1).state == EvidenceState.INCONCLUSIVE


def test_engine_error_is_immediate_and_reset_clears_history():
    gate = SessionPADGate()
    assert gate.observe(PADVerdict.PROCESSING_ERROR, 0).state == EvidenceState.ERROR
    gate.reset()
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, 1).state == EvidenceState.COLLECTING


def test_suspect_frame_at_action_completion_invalidates_all_actions(
        controlled_pipeline, valid_frame, monkeypatch):
    from src.core.pipeline import PipelineState
    from src.core.config import ChallengeType
    from src.core.passive_pad import PADResult
    pipeline = controlled_pipeline
    pipeline.pad_gate = SessionPADGate()
    for now in (0, .1, .2, .3, .4):
        pipeline.pad_gate.observe(PADVerdict.BONA_FIDE_LIVE, now)
    pipeline.state = PipelineState.ACTIVE_CHALLENGE
    pipeline.challenge_manager.completed_challenges.append(ChallengeType.SMILE)
    action = pipeline.challenge_manager.generate_next_challenge()
    action.is_completed = True
    monkeypatch.setattr("src.core.pipeline.time.monotonic", lambda: .5)
    monkeypatch.setattr(pipeline.pad_detector, "evaluate_passive_liveness", lambda *a: PADResult(
        PADVerdict.PRESENTATION_ATTACK, False, .387, .5, True, None, "TEST_DOUBLE"))
    result = pipeline.process_frame(valid_frame)
    assert result.state == PipelineState.PASSIVE_LIVENESS
    assert result.captured_face_image is None
    assert pipeline.challenge_manager.completed_challenges == []
    assert pipeline.challenge_manager.active_challenge_state is None


def test_real_default_pipeline_gate_rejects_sustained_attack_without_leaking_image(
        controlled_attack_pipeline, valid_frame, monkeypatch):
    from src.core.pipeline import PipelineState
    pipeline = controlled_attack_pipeline
    pipeline.pad_gate = SessionPADGate()
    now = [0.0]
    monkeypatch.setattr("src.core.pipeline.time.monotonic", lambda: now[0])
    for elapsed in (0, .15, .3, .45):
        now[0] = elapsed
        result = pipeline.process_frame(valid_frame)
        assert result.state == PipelineState.PASSIVE_LIVENESS
        assert result.captured_face_image is None
    now[0] = .6
    result = pipeline.process_frame(valid_frame)
    assert result.state == PipelineState.ATTACK_REJECTED
    assert result.captured_face_image is None
    # Terminal decisions cannot be undone by changing the presented face.
    assert pipeline.process_frame(valid_frame) is result


def test_unknown_verdict_and_reversed_clock_fail_closed():
    gate = SessionPADGate()
    assert gate.observe("invalid", 0).state == EvidenceState.ERROR
    gate.reset()
    gate.observe(PADVerdict.BONA_FIDE_LIVE, 1)
    assert gate.observe(PADVerdict.BONA_FIDE_LIVE, .5).state == EvidenceState.ERROR
