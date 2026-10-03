import pytest
import numpy as np
import time
from src.core.active_liveness import ActiveLivenessDetector, ChallengeState
from src.core.challenge_manager import ChallengeManager
from src.core.config import ChallengeType, WorkflowPolicy, WorkflowType


def test_ear_calculation():
    detector = ActiveLivenessDetector()
    
    # Mock open eye points: [corner left, top1, top2, corner right, bottom2, bottom1]
    open_eye = np.array([
        [10.0, 26.0],
        [22.0, 20.0],
        [38.0, 20.0],
        [50.0, 26.0],
        [38.0, 32.0],
        [22.0, 32.0],
    ], dtype=np.float64)
    
    landmarks = np.zeros((468, 2), dtype=np.float64)
    for i, idx in enumerate([33, 160, 158, 133, 153, 144]):
        landmarks[idx] = open_eye[i]
        
    ear = detector.calculate_ear(landmarks, [33, 160, 158, 133, 153, 144])
    assert 0.28 <= ear <= 0.32


def test_head_pose_estimation():
    detector = ActiveLivenessDetector()
    landmarks = np.zeros((468, 2), dtype=np.float64)
    # Center face:
    # Nose (1) at (320, 240)
    # Right eye outer (33) at (260, 220) -> d_r = 60
    # Left eye outer (263) at (380, 220) -> d_l = 60
    # Forehead (10) at (320, 150) -> d_up = 90
    # Chin (152) at (320, 330) -> d_down = 90
    landmarks[1] = [320.0, 240.0]
    landmarks[33] = [260.0, 220.0]
    landmarks[263] = [380.0, 220.0]
    landmarks[10] = [320.0, 150.0]
    landmarks[152] = [320.0, 330.0]

    yaw, pitch, roll = detector.estimate_head_pose(landmarks, 640, 480)
    assert abs(yaw) < 2.0
    assert abs(pitch) < 2.0


def test_challenge_manager_state():
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


def test_temporal_blink_sequence():
    detector = ActiveLivenessDetector()
    state = ChallengeState(
        challenge=ChallengeType.BLINK,
        is_active=True,
        start_time=time.time(),
        timeout_seconds=5.0,
        is_completed=False,
        progress=0.0,
        action_detected=False,
        feedback_message="Init"
    )

    # 4 baseline frames with open eyes
    for _ in range(4):
        state = detector._evaluate_challenge(state, {"landmarks_detected": True, "ear": 0.30, "blink_score": 0.05, "yaw": 0.0})

    # Eyes open -> waiting closing
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "ear": 0.30, "blink_score": 0.05, "yaw": 0.0})
    assert state.stage == "WAITING_CLOSING"
    assert not state.is_completed

    # Eyes close
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "ear": 0.18, "blink_score": 0.65, "yaw": 0.0})
    assert state.stage == "EYES_CLOSED"
    assert not state.is_completed

    # Eyes reopen
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "ear": 0.29, "blink_score": 0.10, "yaw": 0.0})
    assert state.stage == "VERIFIED"
    assert state.is_completed is True


def test_temporal_smile_hold():
    detector = ActiveLivenessDetector()
    state = ChallengeState(
        challenge=ChallengeType.SMILE,
        is_active=True,
        start_time=time.time(),
        timeout_seconds=5.0,
        is_completed=False,
        progress=0.0,
        action_detected=False,
        feedback_message="Init"
    )

    # 4 baseline neutral frames (smile = 0.10)
    for _ in range(4):
        state = detector._evaluate_challenge(state, {"landmarks_detected": True, "smile_score": 0.10, "yaw": 0.0})

    # Subject smiles dynamically (smile = 0.50, delta = 0.40 > 0.15)
    # Frame 1 of smile:
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "smile_score": 0.50, "yaw": 0.0})
    assert state.consecutive_action_frames == 1
    assert not state.is_completed

    # Frame 2 of smile:
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "smile_score": 0.50, "yaw": 0.0})
    assert state.consecutive_action_frames == 2
    assert not state.is_completed

    # Frame 3 of smile (meets 3 consecutive frames requirement):
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "smile_score": 0.50, "yaw": 0.0})
    assert state.consecutive_action_frames == 3
    assert state.is_completed is True
    assert state.stage == "VERIFIED"


def test_temporal_head_turn_left():
    detector = ActiveLivenessDetector()
    state = ChallengeState(
        challenge=ChallengeType.TURN_LEFT,
        is_active=True,
        start_time=time.time(),
        timeout_seconds=5.0,
        is_completed=False,
        progress=0.0,
        action_detected=False,
        feedback_message="Init"
    )

    # 4 baseline frames at center (yaw = 0.0)
    for _ in range(4):
        state = detector._evaluate_challenge(state, {"landmarks_detected": True, "yaw": 0.0})

    # Turn left (yaw = 18.0)
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "yaw": 18.0})
    assert state.stage == "TURNED_LEFT"
    assert not state.is_completed

    # Return to center (yaw = 2.0)
    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "yaw": 2.0})
    assert state.stage == "VERIFIED"
    assert state.is_completed is True


def test_challenge_timeout():
    detector = ActiveLivenessDetector()
    state = ChallengeState(
        challenge=ChallengeType.BLINK,
        is_active=True,
        start_time=time.time() - 10.0,  # 10 seconds ago
        timeout_seconds=5.0,
        is_completed=False,
        progress=0.0,
        action_detected=False,
        feedback_message="Init"
    )

    state = detector._evaluate_challenge(state, {"landmarks_detected": True, "ear": 0.30, "blink_score": 0.0, "yaw": 0.0})
    assert state.is_active is False
    assert state.is_completed is False
    assert "timed out" in state.feedback_message.lower()
