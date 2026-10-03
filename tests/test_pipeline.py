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
