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
    dark_frame = np.full((480, 640, 3), 15, dtype=np.uint8)
    faces = [DetectedFace(x=200, y=140, w=200, h=200, confidence=0.95)]
    quality = assessor.assess_quality(dark_frame, faces)
    
    assert quality.is_poorly_lit is True
    assert quality.is_acceptable is False
    assert "dark" in quality.error_message.lower()


def test_face_detector_overexposed_lighting():
    assessor = FaceQualityAssessor(min_sharpness=10.0, max_brightness=215.0)
    bright_frame = np.full((480, 640, 3), 235, dtype=np.uint8)
    faces = [DetectedFace(x=200, y=140, w=200, h=200, confidence=0.95)]
    quality = assessor.assess_quality(bright_frame, faces)

    assert quality.is_poorly_lit is True
    assert quality.is_acceptable is False
    assert "bright" in quality.error_message.lower() or "glare" in quality.error_message.lower()


def test_face_detector_uneven_lateral_shadows():
    assessor = FaceQualityAssessor(min_sharpness=10.0, min_brightness=40.0, max_brightness=220.0)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    frame[140:340, 200:300] = 30
    frame[140:340, 300:400] = 180
    faces = [DetectedFace(x=200, y=140, w=200, h=200, confidence=0.95)]
    quality = assessor.assess_quality(frame, faces)

    assert quality.is_poorly_lit is True
    assert quality.is_acceptable is False
    assert "shadow" in quality.error_message.lower() or "uneven" in quality.error_message.lower()


def test_face_detector_face_too_small():
    assessor = FaceQualityAssessor(min_face_ratio=0.10)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Face size 40x40 = 1600 px (1600 / 307200 = 0.0052, far below 0.10)
    faces = [DetectedFace(x=300, y=220, w=40, h=40, confidence=0.95)]
    quality = assessor.assess_quality(frame, faces)

    assert quality.is_acceptable is False
    assert "closer" in quality.error_message.lower() or "far" in quality.error_message.lower()


def test_face_detector_face_too_large():
    assessor = FaceQualityAssessor(max_face_ratio=0.70)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Face size 480x600 = 288000 px (>90% of frame)
    faces = [DetectedFace(x=20, y=0, w=600, h=480, confidence=0.95)]
    quality = assessor.assess_quality(frame, faces)

    assert quality.is_acceptable is False
    assert "close" in quality.error_message.lower() or "step back" in quality.error_message.lower()


def test_face_detector_uncentered_face():
    assessor = FaceQualityAssessor(min_sharpness=0.0)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Face pushed to extreme corner (x=10, y=10)
    faces = [DetectedFace(x=10, y=10, w=100, h=100, confidence=0.95)]
    quality = assessor.assess_quality(frame, faces)

    assert quality.is_acceptable is False
    assert "central" in quality.error_message.lower() or "position" in quality.error_message.lower()
