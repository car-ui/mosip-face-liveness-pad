import pytest
import numpy as np
from src.core.active_liveness import ActiveLivenessDetector, ChallengeState
from src.core.config import ChallengeType


def test_ear_calculation():
    detector = ActiveLivenessDetector()
    
    # 6 mock points for open eye: [corner1, top1, top2, corner2, bottom2, bottom1]
    # Horizontal width = 40 (x: 10 to 50), vertical height = 12 (y: 20 vs 32)
    open_eye = np.array([
        [10.0, 26.0],  # p1: corner left
        [22.0, 20.0],  # p2: top1
        [38.0, 20.0],  # p3: top2
        [50.0, 26.0],  # p4: corner right
        [38.0, 32.0],  # p5: bottom2
        [22.0, 32.0],  # p6: bottom1
    ], dtype=np.float64)
    
    landmarks = np.zeros((468, 2), dtype=np.float64)
    for i, idx in enumerate([33, 160, 158, 133, 153, 144]):
        landmarks[idx] = open_eye[i]
        
    ear = detector.calculate_ear(landmarks, [33, 160, 158, 133, 153, 144])
    # v1 = 12, v2 = 12, h = 40 => EAR = 24 / 80 = 0.30
    assert 0.28 <= ear <= 0.32


def test_challenge_manager_state():
    from src.core.challenge_manager import ChallengeManager
    from src.core.config import WorkflowPolicy, WorkflowType
    
    policy = WorkflowPolicy(
        workflow_type=WorkflowType.RESIDENT_REGISTRATION,
        min_challenges=2,
        challenge_timeout_seconds=5.0,
        max_retries=3
    )
    manager = ChallengeManager(policy)
    
    assert not manager.is_all_challenges_satisfied()
    assert manager.can_retry()
    
    c1 = manager.generate_next_challenge()
    assert c1.is_active is True
    assert c1.timeout_seconds == 5.0
    
    # Simulate completion
    c1.is_completed = True
    manager.record_challenge_success()
    assert len(manager.completed_challenges) == 1
    assert not manager.is_all_challenges_satisfied()
    
    c2 = manager.generate_next_challenge()
    c2.is_completed = True
    manager.record_challenge_success()
    assert len(manager.completed_challenges) == 2
    assert manager.is_all_challenges_satisfied()
