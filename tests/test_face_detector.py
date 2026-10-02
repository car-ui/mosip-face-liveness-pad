import pytest
import numpy as np
import cv2
from src.core.face_detector import FaceQualityAssessor, DetectedFace


def test_face_detector_no_face():
    assessor = FaceQualityAssessor()
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = assessor.detect_faces(blank_frame)
    quality = assessor.assess_quality(blank_frame, faces)
    
    assert quality.is_acceptable is False
    assert quality.face_count == 0
    assert "Face not detected" in quality.error_message


def test_face_detector_multiple_faces():
    assessor = FaceQualityAssessor()
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Simulate two detected faces
    faces = [
        DetectedFace(x=100, y=100, w=100, h=100, confidence=0.9),
        DetectedFace(x=350, y=100, w=100, h=100, confidence=0.9)
    ]
    quality = assessor.assess_quality(blank_frame, faces)
    
    assert quality.is_acceptable is False
    assert quality.face_count == 2
    assert "Multiple faces detected" in quality.error_message


def test_face_detector_lighting_and_blur():
    assessor = FaceQualityAssessor(min_sharpness=50.0, min_brightness=48.0)
    # Create dark frame
    dark_frame = np.full((480, 640, 3), 15, dtype=np.uint8)
    faces = [DetectedFace(x=200, y=140, w=200, h=200, confidence=0.95)]
    quality = assessor.assess_quality(dark_frame, faces)
    
    assert quality.is_poorly_lit is True
    assert quality.is_acceptable is False
    assert "dark" in quality.error_message.lower()


def test_face_detector_overexposed_lighting():
    assessor = FaceQualityAssessor(min_sharpness=10.0, max_brightness=215.0)
    # Create washed out bright frame
    bright_frame = np.full((480, 640, 3), 235, dtype=np.uint8)
    faces = [DetectedFace(x=200, y=140, w=200, h=200, confidence=0.95)]
    quality = assessor.assess_quality(bright_frame, faces)

    assert quality.is_poorly_lit is True
    assert quality.is_acceptable is False
    assert "bright" in quality.error_message.lower() or "glare" in quality.error_message.lower()


def test_face_detector_uneven_lateral_shadows():
    assessor = FaceQualityAssessor(min_sharpness=10.0, min_brightness=40.0, max_brightness=220.0)
    # Create frame where left side of face is very dark and right side is bright
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Face at x=200, y=140, w=200, h=200
    # Left half: x from 200 to 300, make it 30
    frame[140:340, 200:300] = 30
    # Right half: x from 300 to 400, make it 180
    frame[140:340, 300:400] = 180
    faces = [DetectedFace(x=200, y=140, w=200, h=200, confidence=0.95)]
    quality = assessor.assess_quality(frame, faces)

    assert quality.is_poorly_lit is True
    assert quality.is_acceptable is False
    assert "shadow" in quality.error_message.lower() or "uneven" in quality.error_message.lower()

