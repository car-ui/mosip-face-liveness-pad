import pytest
import numpy as np
from src.core.pipeline import LivenessPipeline, PipelineState, LivenessDecision
from src.core.config import WorkflowType, LivenessConfig
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


def test_pipeline_high_confidence_passive_pass():
    device = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    device.connect()
    
    # Configure low threshold for fast direct passive pass test
    config = LivenessConfig()
    config.resident_policy.passive_threshold = 0.50
    pipeline = LivenessPipeline(config=config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    passed = False
    for _ in range(35):
        success, frame = device.read_frame()
        res = pipeline.process_frame(frame)
        if res.state == PipelineState.CAPTURE_SUCCESS:
            passed = True
            assert res.decision == LivenessDecision.PASSED
            assert res.captured_face_image is not None
            break

    device.disconnect()
    assert passed is True


def test_pipeline_passive_escalation_to_active_challenge():
    device = MockL0Device(scenario=MockScenario.STATIC_PHOTO_ATTACK)
    device.connect()
    
    # Strict threshold requires active challenge
    config = LivenessConfig()
    config.resident_policy.passive_threshold = 0.95
    pipeline = LivenessPipeline(config=config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    active_triggered = False
    for _ in range(40):
        success, frame = device.read_frame()
        res = pipeline.process_frame(frame)
        if res.state == PipelineState.ACTIVE_CHALLENGE:
            active_triggered = True
            assert res.active_challenge is not None
            break

    device.disconnect()
    assert active_triggered is True


def test_pipeline_presentation_attack_rejection_when_active_disabled():
    device = MockL0Device(scenario=MockScenario.SCREEN_REPLAY_ATTACK)
    device.connect()
    
    config = LivenessConfig()
    # Disable active liveness fallback to test immediate rejection
    config.resident_policy.active_liveness_enabled = False
    pipeline = LivenessPipeline(config=config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    attack_rejected = False
    for _ in range(35):
        success, frame = device.read_frame()
        res = pipeline.process_frame(frame)
        if res.state == PipelineState.ATTACK_REJECTED:
            attack_rejected = True
            assert res.decision == LivenessDecision.ATTACK_DETECTED
            assert res.pad_result.attack_detected is True
            break

    device.disconnect()
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


def test_pipeline_definite_attack_rejected_even_when_active_enabled():
    """Confirms definite attacks are rejected immediately even if active liveness is enabled."""
    device = MockL0Device(scenario=MockScenario.SCREEN_REPLAY_ATTACK)
    device.connect()

    config = LivenessConfig()
    config.resident_policy.active_liveness_enabled = True
    config.resident_policy.escalate_attacks_to_active = False

    pipeline = LivenessPipeline(config=config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()

    attack_rejected = False
    for _ in range(15):
        success, frame = device.read_frame()
        res = pipeline.process_frame(frame)
        if res.state == PipelineState.ATTACK_REJECTED:
            attack_rejected = True
            assert res.decision == LivenessDecision.ATTACK_DETECTED
            assert res.pad_result.attack_detected is True
            break

    device.disconnect()
    assert attack_rejected is True


def test_pipeline_active_challenge_success_with_scripted_action():
    """Verifies that an active challenge completes and reaches CAPTURE_SUCCESS upon valid action."""
    device = MockL0Device(scenario=MockScenario.STATIC_PHOTO_ATTACK)
    device.connect()

    config = LivenessConfig()
    config.resident_policy.passive_threshold = 0.95  # Forces active escalation
    config.resident_policy.min_challenges = 1

    pipeline = LivenessPipeline(config=config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()

    # Step until active challenge starts
    for _ in range(30):
        success, frame = device.read_frame()
        res = pipeline.process_frame(frame)
        if res.state == PipelineState.ACTIVE_CHALLENGE:
            break

    assert pipeline.state == PipelineState.ACTIVE_CHALLENGE
    challenge = pipeline.challenge_manager.active_challenge_state
    assert challenge is not None

    # Manually mark the challenge completed to test pipeline transition
    challenge.is_completed = True
    success, frame = device.read_frame()
    res = pipeline.process_frame(frame)

    assert res.state == PipelineState.CAPTURE_SUCCESS
    assert res.decision == LivenessDecision.PASSED
    assert res.captured_face_image is not None
    device.disconnect()


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

