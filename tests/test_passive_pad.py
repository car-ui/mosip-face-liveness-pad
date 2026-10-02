import pytest
import numpy as np
import cv2
from src.core.passive_pad import PassivePADDetector


def test_passive_pad_on_synthetic_face():
    detector = PassivePADDetector()
    
    # Create synthetic test frame
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Add face-like patch
    cv2.circle(frame, (320, 240), 90, (180, 200, 220), -1)
    
    face_box = (230, 150, 180, 180)
    result = detector.evaluate_passive_liveness(frame, face_box)
    
    assert result is not None
    assert 0.0 <= result.liveness_score <= 1.0
    assert "frequency_score" in result.details
    assert "chroma_score" in result.details


def test_passive_pad_screen_glare_attack():
    detector = PassivePADDetector()
    
    # Create test frame with extreme specular reflection (simulating screen glare)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    cv2.circle(frame, (320, 240), 90, (180, 200, 220), -1)
    # Inject large bright glare patch
    cv2.rectangle(frame, (280, 200), (360, 280), (255, 255, 255), -1)
    
    face_box = (230, 150, 180, 180)
    result = detector.evaluate_passive_liveness(frame, face_box)
    
    assert result.attack_detected is True
    assert result.attack_type == "SCREEN_REPLAY"
    assert result.liveness_score < 0.60
