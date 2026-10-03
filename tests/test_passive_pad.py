import pytest
import numpy as np
import cv2
from src.core.passive_pad import PassivePADDetector, PADVerdict
from src.core.config import PADMode


def test_passive_pad_on_synthetic_face():
    detector = PassivePADDetector()
    assert detector.operational_mode in ("MODEL", "HEURISTIC")
    
    # Create natural face-like patch
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    cv2.circle(frame, (320, 240), 90, (180, 200, 220), -1)
    
    face_box = (230, 150, 180, 180)
    result = detector.evaluate_passive_liveness(frame, face_box)
    
    assert result is not None
    assert 0.0 <= result.liveness_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.mode_used in ("MODEL", "HEURISTIC")
    assert result.verdict in (PADVerdict.BONA_FIDE_LIVE, PADVerdict.UNCERTAIN, PADVerdict.PRESENTATION_ATTACK)
    assert "frequency_score" in result.details or "model_type" in result.details


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
    assert result.verdict == PADVerdict.PRESENTATION_ATTACK
    assert result.liveness_score < 0.60


def test_passive_pad_print_photo_flat_gamut():
    detector = PassivePADDetector()
    
    # Create flat monochrome print with no chrominance variation
    frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    cv2.circle(frame, (320, 240), 90, (100, 100, 100), -1)
    
    face_box = (230, 150, 180, 180)
    result = detector.evaluate_passive_liveness(frame, face_box)
    
    assert result.attack_detected is True
    assert result.attack_type == "PRINT_PHOTO"
    assert result.verdict == PADVerdict.PRESENTATION_ATTACK


def test_passive_pad_invalid_crop():
    detector = PassivePADDetector()
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Invalid zero size face box
    face_box = (0, 0, 10, 10)
    result = detector.evaluate_passive_liveness(frame, face_box)
    
    assert result.verdict == PADVerdict.PROCESSING_ERROR
    assert result.is_live is False
    assert result.liveness_score == 0.0


def test_passive_pad_operational_mode():
    h_detector = PassivePADDetector(mode=PADMode.HEURISTIC_ONLY)
    assert h_detector.operational_mode == "HEURISTIC"
    
    o_detector = PassivePADDetector(mode=PADMode.ONNX_ONLY, onnx_model_path="non_existent_model.onnx")
    # Non existent model returns MODEL mode property, but falls back gracefully during evaluation
    assert o_detector.operational_mode == "MODEL"
