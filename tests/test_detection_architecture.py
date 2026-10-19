"""Detection architecture checks, distinct from physical PAD accuracy."""
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from src.core.face_detector import FaceQualityAssessor


def test_one_neural_detection_is_not_counted_again_from_landmark_outline():
    assessor = FaceQualityAssessor()
    # The two methods can draw very different rectangles around one head.
    row = np.array([[80, 50, 120, 140] + [0] * 10 + [.99]], np.float32)
    assessor.neural_detector = SimpleNamespace(setInputSize=lambda size: None,
                                               detect=lambda image: (None, row))
    faces = assessor.detect_faces(np.zeros((240, 320, 3), np.uint8),
                                  landmark_boxes=[(180, 90, 90, 100)])
    assert assessor.detector_backend == "yunet"
    assert len(faces) == 1


def test_primary_neural_detector_finds_two_separate_fixture_faces():
    image = cv2.imread(str(Path(__file__).parent / 'sample_images/astronaut.png'))
    image = cv2.resize(image, (320, 320))
    pair = np.concatenate([image, image], axis=1)
    assessor = FaceQualityAssessor()
    assert len(assessor.detect_faces(pair)) == 2


def test_landmark_outline_cannot_create_face_when_primary_detector_finds_none():
    assessor = FaceQualityAssessor()
    assessor.neural_detector = SimpleNamespace(setInputSize=lambda size: None,
                                               detect=lambda image: (None, None))
    assert assessor.detect_faces(np.zeros((240, 320, 3), np.uint8),
                                 landmark_boxes=[(80, 50, 120, 140)]) == []


def test_primary_detection_never_masks_two_independent_landmark_faces():
    assessor = FaceQualityAssessor()
    row = np.array([[80, 50, 120, 140] + [0] * 10 + [.99]], np.float32)
    assessor.neural_detector = SimpleNamespace(setInputSize=lambda size: None,
                                               detect=lambda image: (None, row))
    faces = assessor.detect_faces(np.zeros((240, 320, 3), np.uint8),
                                  landmark_boxes=[(80, 50, 100, 100), (180, 50, 100, 100)])
    assert len(faces) == 2
    assert not assessor.assess_quality(np.zeros((240, 320, 3), np.uint8), faces).is_acceptable
