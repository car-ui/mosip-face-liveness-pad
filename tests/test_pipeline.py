import pytest
import numpy as np
from src.core.pipeline import LivenessPipeline, PipelineState, LivenessDecision
from src.core.config import WorkflowType, LivenessConfig
from src.devices.mock_l0_device import MockL0Device


def test_pipeline_workflow_resident():
    config = LivenessConfig()
    pipeline = LivenessPipeline(config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    assert pipeline.state == PipelineState.DETECTING_FACE
    assert pipeline.workflow == WorkflowType.RESIDENT_REGISTRATION


def test_pipeline_processes_mock_stream():
    device = MockL0Device(fps=30)
    device.connect()
    pipeline = LivenessPipeline(workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    
    # Process 10 frames from mock device
    results = []
    for _ in range(10):
        success, frame = device.read_frame()
        assert success is True
        res = pipeline.process_frame(frame)
        results.append(res)
        
    device.disconnect()
    
    assert len(results) == 10
    # Every step returns a structured result with status and guidance
    for r in results:
        assert r.status_text != ""
        assert r.detailed_guidance != ""
        assert 0.0 <= r.progress <= 1.0
