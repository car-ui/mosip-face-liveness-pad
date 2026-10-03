import pytest
from src.core.config import LivenessConfig, WorkflowType
from src.core.pipeline import LivenessPipeline


def test_resident_registration_workflow_policy():
    config = LivenessConfig()
    pipeline = LivenessPipeline(config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    
    policy = pipeline.policy
    assert policy.workflow_type == WorkflowType.RESIDENT_REGISTRATION
    assert policy.passive_threshold == 0.82
    assert policy.min_challenges == 1
    assert policy.max_retries == 3
    assert policy.active_liveness_enabled is True


def test_operator_authentication_workflow_policy():
    config = LivenessConfig()
    pipeline = LivenessPipeline(config, workflow=WorkflowType.OPERATOR_AUTHENTICATION)
    
    policy = pipeline.policy
    assert policy.workflow_type == WorkflowType.OPERATOR_AUTHENTICATION
    # Higher threshold for operator
    assert policy.passive_threshold >= 0.85
    assert policy.min_challenges >= 1
    assert policy.max_retries <= 3


def test_supervisor_authentication_workflow_policy():
    config = LivenessConfig()
    pipeline = LivenessPipeline(config, workflow=WorkflowType.SUPERVISOR_AUTHENTICATION)
    
    policy = pipeline.policy
    assert policy.workflow_type == WorkflowType.SUPERVISOR_AUTHENTICATION
    # Strictest threshold and multiple challenges for supervisor
    assert policy.passive_threshold >= 0.90
    assert policy.min_challenges >= 2
    assert policy.max_retries <= 2


def test_workflow_switching_resets_session():
    config = LivenessConfig()
    pipeline = LivenessPipeline(config, workflow=WorkflowType.RESIDENT_REGISTRATION)
    pipeline.reset()
    assert pipeline.workflow == WorkflowType.RESIDENT_REGISTRATION
    
    # Switch to supervisor
    pipeline.set_workflow(WorkflowType.SUPERVISOR_AUTHENTICATION)
    assert pipeline.workflow == WorkflowType.SUPERVISOR_AUTHENTICATION
    assert pipeline.policy.min_challenges >= 2
