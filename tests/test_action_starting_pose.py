import time
import pytest
from src.core.active_liveness import ActiveLivenessDetector, ChallengeState
from src.core.config import ChallengeType


def challenge(kind):
    return ChallengeState(kind,True,time.time(),10,False,0,False,'Start')


def values(**changes):
    return {'landmarks_detected':True,'ear':.3,'blink_score':.05,
            'smile_score':.1,'yaw':0,'pitch':0,**changes}


def test_closed_eyes_cannot_establish_blink_starting_pose():
    d=ActiveLivenessDetector(model_path='not-needed-for-telemetry-tests')
    s=challenge(ChallengeType.BLINK)
    for _ in range(12):
        d._evaluate_challenge(s,values(ear=.1,blink_score=.8))
    assert s.baseline_frames_recorded==0 and not s.is_completed


@pytest.mark.parametrize('kind,pitch',[(ChallengeType.LOOK_UP,-15),(ChallengeType.LOOK_DOWN,15)])
def test_pitch_requires_neutral_movement_and_return(kind,pitch):
    d=ActiveLivenessDetector(model_path='not-needed-for-telemetry-tests')
    s=challenge(kind)
    for _ in range(10):
        d._evaluate_challenge(s,values(pitch=pitch))
    assert not s.is_completed and s.baseline_frames_recorded==0
    for _ in range(4):
        d._evaluate_challenge(s,values())
    for _ in range(3):
        d._evaluate_challenge(s,values(pitch=pitch))
    assert s.stage=='PITCH_MOVED' and not s.is_completed
    d._evaluate_challenge(s,values())
    assert s.is_completed


def test_landmark_loss_clears_blink_progress():
    d=ActiveLivenessDetector(model_path='not-needed-for-telemetry-tests')
    s=challenge(ChallengeType.BLINK)
    s.stage='EYES_CLOSED'
    s.baseline_frames_recorded=4
    d._evaluate_challenge(s,values(landmarks_detected=False))
    d._evaluate_challenge(s,values())
    assert not s.is_completed and s.baseline_frames_recorded==1


def test_preparation_time_cannot_record_action_or_consume_action_deadline(monkeypatch):
    d = ActiveLivenessDetector(model_path="not-needed-for-telemetry-tests")
    s = challenge(ChallengeType.BLINK)
    s.start_time = 100.0
    s.preparation_seconds = 2.0
    monkeypatch.setattr("src.core.active_liveness.time.time", lambda: 101.0)
    d._evaluate_challenge(s, values())
    assert s.baseline_frames_recorded == 0 and not s.action_detected
    # Twelve total seconds means ten action seconds after preparation.
    monkeypatch.setattr("src.core.active_liveness.time.time", lambda: 111.5)
    d._evaluate_challenge(s, values())
    assert s.is_active
    monkeypatch.setattr("src.core.active_liveness.time.time", lambda: 112.1)
    d._evaluate_challenge(s, values())
    assert not s.is_active and not s.is_completed
