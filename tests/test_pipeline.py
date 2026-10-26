import pytest
import numpy as np
from src.core.pipeline import LivenessPipeline, PipelineState, LivenessDecision
from src.core.config import WorkflowType, LivenessConfig, PADVerdict
from src.core.passive_pad import PADResult
from src.core.session_pad import SessionPADGate
from src.devices.mock_l0_device import MockL0Device
from src.devices.base import MockScenario, VideoFrame


def test_pipeline_workflow_resident():
    config = LivenessConfig()
    pipeline = LivenessPipeline(config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    assert pipeline.state == PipelineState.FACE_DETECTION
    assert pipeline.workflow == WorkflowType.RESIDENT_REGISTRATION


def test_pipeline_processes_mock_stream():
    device = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE, fps=30)
    device.connect()
    pipeline = LivenessPipeline(workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    results = []
    for _ in range(10):
        success, frame = device.read_frame()
        assert success is True
        res = pipeline.process_frame(frame)
        results.append(res)
        
    device.disconnect()
    
    assert len(results) == 10
    for r in results:
        assert r.status_text != ""
        assert r.detailed_guidance != ""
        assert 0.0 <= r.progress <= 1.0


def test_pipeline_high_confidence_passive_pass(controlled_pipeline, valid_frame):
    # Fixed high PAD scores and moving face centers exercise policy acceptance.
    # A recorded sample photo cannot establish bona fide liveness.
    pipeline = controlled_pipeline
    for _ in range(25):
        result = pipeline.process_frame(valid_frame)
    assert result.state == PipelineState.CAPTURE_SUCCESS
    assert result.decision == LivenessDecision.PASSED
    assert result.captured_face_image is not None


def test_pipeline_passive_escalation_to_active_challenge(controlled_pipeline, valid_frame, monkeypatch):
    # Exercise uncertain-score policy independently of image inference and host speed.
    pipeline = controlled_pipeline
    pipeline.policy.passive_threshold = 0.95
    pipeline.pad_gate = SessionPADGate()
    monkeypatch.setattr(pipeline.pad_detector, "evaluate_passive_liveness", lambda *a: PADResult(
        PADVerdict.UNCERTAIN, False, .70, .98, False, None, "TEST_DOUBLE"))
    clock = [100.0]
    monkeypatch.setattr("src.core.pipeline.time.monotonic", lambda: clock[0])

    # Frame count alone cannot bypass the real evidence gate's minimum duration.
    for _ in range(40):
        result = pipeline.process_frame(valid_frame)
        assert result.state == PipelineState.PASSIVE_LIVENESS
        assert result.active_challenge is None
        assert result.captured_face_image is None

    # Advance virtual camera time, rather than sleeping or relying on model latency.
    for _ in range(40):
        clock[0] += .05
        result = pipeline.process_frame(valid_frame)
        assert result.captured_face_image is None
        if result.state == PipelineState.ACTIVE_CHALLENGE:
            break
    assert result.state == PipelineState.ACTIVE_CHALLENGE
    assert result.decision == LivenessDecision.ACTIVE_CHALLENGE_REQUIRED
    assert result.active_challenge is not None
    assert pipeline.challenge_manager.completed_challenges == []


def test_pipeline_presentation_attack_rejection_when_active_disabled(controlled_attack_pipeline, valid_frame):
    # Injected attack verdict checks policy handling independently of photo content.
    pipeline = controlled_attack_pipeline
    pipeline.policy.active_liveness_enabled = False
    
    attack_rejected = False
    for _ in range(35):
        res = pipeline.process_frame(valid_frame)
        if res.state == PipelineState.ATTACK_REJECTED:
            attack_rejected = True
            assert res.decision == LivenessDecision.ATTACK_DETECTED
            assert res.pad_result.attack_detected is True
            break

    assert attack_rejected is True


def test_pipeline_invalid_frame_handling():
    pipeline = LivenessPipeline()
    pipeline.reset()
    
    invalid_frame = VideoFrame(
        frame_id=1,
        timestamp_ms=0.0,
        image=np.empty((0, 0, 0), dtype=np.uint8),
        width=0,
        height=0
    )
    res = pipeline.process_frame(invalid_frame)
    assert res.state == PipelineState.DEVICE_ERROR
    assert res.decision == LivenessDecision.ERROR


def test_pipeline_definite_attack_rejected_even_when_active_enabled(controlled_attack_pipeline, valid_frame):
    """An injected attack verdict must reject even when active liveness is enabled."""
    pipeline = controlled_attack_pipeline
    pipeline.policy.active_liveness_enabled = True
    pipeline.policy.escalate_attacks_to_active = False

    attack_rejected = False
    for _ in range(15):
        res = pipeline.process_frame(valid_frame)
        if res.state == PipelineState.ATTACK_REJECTED:
            attack_rejected = True
            assert res.decision == LivenessDecision.ATTACK_DETECTED
            assert res.pad_result.attack_detected is True
            break

    assert attack_rejected is True


def test_pipeline_accepts_explicitly_completed_challenge_double(controlled_pipeline, valid_frame):
    """Exercise the completion transition, separately from real action inference."""
    pipeline = controlled_pipeline
    pipeline.policy.passive_threshold = 1.0
    pipeline.policy.min_challenges = 1
    pipeline.reset()
    for _ in range(30):
        result = pipeline.process_frame(valid_frame)
        if result.state == PipelineState.ACTIVE_CHALLENGE:
            break
    assert pipeline.state == PipelineState.ACTIVE_CHALLENGE
    challenge = pipeline.challenge_manager.active_challenge_state
    assert challenge is not None
    # This is a completion double, not a scripted or observed physical action.
    challenge.is_completed = True
    result = pipeline.process_frame(valid_frame)
    assert result.state == PipelineState.CAPTURE_SUCCESS
    assert result.decision == LivenessDecision.PASSED
    assert result.captured_face_image is not None


def test_pipeline_retry_exhaustion():
    """Verifies that repeated challenge failures transition to MAX_RETRIES_EXCEEDED."""
    config = LivenessConfig()
    config.resident_policy.max_retries = 2
    pipeline = LivenessPipeline(config=config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()

    # Artificially exhaust retries
    pipeline.challenge_manager.current_retry = 2
    pipeline.challenge_manager.active_challenge_state = pipeline.challenge_manager.generate_next_challenge()
    pipeline.challenge_manager.active_challenge_state.is_active = False
    pipeline.challenge_manager.active_challenge_state.is_completed = False
    pipeline.state = PipelineState.ACTIVE_CHALLENGE

    device = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    device.connect()
    success, frame = device.read_frame()
    assert success is True

    res = pipeline.process_frame(frame)
    device.disconnect()
    assert res.state == PipelineState.MAX_RETRIES_EXCEEDED
    assert res.can_retry is False

