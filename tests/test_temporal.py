import pytest
import numpy as np
from src.core.temporal_buffer import TemporalLivenessBuffer, TemporalAnalysisResult


def test_temporal_buffer_stable_live_sequence():
    buf = TemporalLivenessBuffer(window_size=15)
    
    # Feed 15 stable live frames with natural subtle movement
    for i in range(15):
        buf.add_frame(
            timestamp=1000.0 + (i * 33.3),
            liveness_score=0.92,
            is_live=True,
            attack_detected=False,
            face_center=(175.0 + (i % 3) * 1.5, 175.0 + (i % 2) * 1.2)
        )
    
    analysis = buf.analyze()
    assert analysis.frame_count == 15
    assert analysis.rolling_liveness_score >= 0.90
    assert analysis.temporal_stability >= 0.85
    assert analysis.micro_motion_detected is True


def test_temporal_buffer_static_photo_zero_motion():
    buf = TemporalLivenessBuffer(window_size=15, min_motion_threshold=0.35)
    
    # Feed 15 completely stationary frames with zero motion
    for i in range(15):
        buf.add_frame(
            timestamp=1000.0 + (i * 33.3),
            liveness_score=0.75,
            is_live=True,
            attack_detected=False,
            face_center=(175.0, 175.0)  # Exactly static
        )
    
    analysis = buf.analyze()
    assert analysis.frame_count == 15
    assert analysis.micro_motion_score == 0.0
    assert analysis.micro_motion_detected is False


def test_temporal_buffer_unstable_scores():
    buf = TemporalLivenessBuffer(window_size=10)
    
    # Alternating wild scores (e.g. sensor flicker or glitch)
    for i in range(10):
        score = 0.95 if i % 2 == 0 else 0.15
        buf.add_frame(
            timestamp=1000.0 + (i * 33.3),
            liveness_score=score,
            is_live=(score > 0.5),
            attack_detected=(score < 0.4),
            face_center=(175.0, 175.0)
        )
        
    analysis = buf.analyze()
    assert analysis.liveness_variance > 0.10
    # Stability penalty applied
    assert analysis.temporal_stability < 0.60


def test_temporal_buffer_consecutive_attack_counts():
    buf = TemporalLivenessBuffer(window_size=10)
    
    # 5 live frames followed by 3 attack frames
    for i in range(5):
        buf.add_frame(
            timestamp=1000.0 + (i * 33.3),
            liveness_score=0.90,
            is_live=True,
            attack_detected=False,
            face_center=(175.0, 175.0)
        )
        
    for i in range(3):
        buf.add_frame(
            timestamp=1200.0 + (i * 33.3),
            liveness_score=0.30,
            is_live=False,
            attack_detected=True,
            face_center=(175.0, 175.0)
        )
        
    analysis = buf.analyze()
    assert analysis.consecutive_attack_frames == 3
    assert analysis.consecutive_live_frames == 0
