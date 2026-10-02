"""
Face Detection and Image Quality Assessment
Conforms to ISO/IEC 19794-5 face biometric quality requirements:
- Single face enforcement
- Lighting/illumination adequacy
- Sharpness / blur detection (Laplacian variance)
- Face positioning (bounding box centering and size ratio)
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import cv2
import numpy as np


@dataclass
class QualityMetrics:
    is_acceptable: bool
    face_count: int
    sharpness_score: float  # Laplacian variance (higher = sharper)
    is_blurry: bool
    brightness_score: float  # Mean luminance (0-255)
    is_poorly_lit: bool
    face_size_ratio: float  # Face area / frame area
    is_centered: bool
    error_message: Optional[str] = None


@dataclass
class DetectedFace:
    x: int
    y: int
    w: int
    h: int
    confidence: float
    landmarks: Optional[np.ndarray] = None


class FaceQualityAssessor:
    def __init__(self,
                 min_sharpness: float = 30.0,
                 min_brightness: float = 48.0,
                 max_brightness: float = 215.0,
                 min_face_ratio: float = 0.025,
                 max_face_ratio: float = 0.90):
        self.min_sharpness = min_sharpness
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_face_ratio = min_face_ratio
        self.max_face_ratio = max_face_ratio
        
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_faces(self, frame: np.ndarray, known_box: Optional[Tuple[int, int, int, int]] = None) -> List[DetectedFace]:
        if known_box is not None:
            kx, ky, kw, kh = known_box
            if kw > 30 and kh > 30:
                return [DetectedFace(x=kx, y=ky, w=kw, h=kh, confidence=0.98)]

        # Fast downscaled Haar detection for 30+ FPS
        h, w = frame.shape[:2]
        scale = 0.5
        small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        
        boxes = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=4,
            minSize=(30, 30)
        )
        
        faces = []
        for (x, y, bw, bh) in boxes:
            faces.append(DetectedFace(
                x=int(x / scale),
                y=int(y / scale),
                w=int(bw / scale),
                h=int(bh / scale),
                confidence=0.95
            ))
        return faces

    def assess_quality(self, frame: np.ndarray, faces: List[DetectedFace]) -> QualityMetrics:
        h, w = frame.shape[:2]
        total_area = h * w
        
        # 1. Face Count Check
        if len(faces) == 0:
            return QualityMetrics(
                is_acceptable=False,
                face_count=0,
                sharpness_score=0.0,
                is_blurry=False,
                brightness_score=0.0,
                is_poorly_lit=False,
                face_size_ratio=0.0,
                is_centered=False,
                error_message="Face not detected. Please look directly at the camera."
            )
        
        if len(faces) > 1:
            return QualityMetrics(
                is_acceptable=False,
                face_count=len(faces),
                sharpness_score=0.0,
                is_blurry=False,
                brightness_score=0.0,
                is_poorly_lit=False,
                face_size_ratio=0.0,
                is_centered=False,
                error_message="Multiple faces detected. Only one person should be in frame."
            )
        
        # Single face evaluation
        face = faces[0]
        face_area = face.w * face.h
        size_ratio = face_area / float(total_area)
        
        # Crop face region
        x1 = max(0, face.x)
        y1 = max(0, face.y)
        x2 = min(w, face.x + face.w)
        y2 = min(h, face.y + face.h)
        face_roi = frame[y1:y2, x1:x2]
        
        if face_roi.size == 0:
            return QualityMetrics(
                is_acceptable=False,
                face_count=1,
                sharpness_score=0.0,
                is_blurry=True,
                brightness_score=0.0,
                is_poorly_lit=True,
                face_size_ratio=size_ratio,
                is_centered=False,
                error_message="Face crop invalid."
            )
        
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 2. Sharpness / Blur check
        sharpness = float(cv2.Laplacian(gray_roi, cv2.CV_64F).var())
        is_blurry = sharpness < self.min_sharpness
        
        # 3. Brightness / Illumination check (ISO/IEC 19794-5 Section 7.2)
        brightness = float(np.mean(gray_roi))
        is_too_dark = brightness < self.min_brightness
        is_too_bright = brightness > self.max_brightness
        
        # Check lateral shadow / uneven lighting
        h_roi, w_roi = gray_roi.shape
        w_half = max(1, w_roi // 2)
        left_half = gray_roi[:, :w_half]
        right_half = gray_roi[:, w_half:]
        mean_left = float(np.mean(left_half))
        mean_right = float(np.mean(right_half))
        shadow_delta = abs(mean_left - mean_right)
        is_uneven = (shadow_delta > 40.0) and ((shadow_delta / max(mean_left, mean_right, 1.0)) > 0.35)
        
        # Check dynamic range / deep crushed shadows (e.g. > 20% of face is pitch black < 25)
        crushed_ratio = float(np.sum(gray_roi < 25)) / float(gray_roi.size)
        is_deep_shadow = crushed_ratio > 0.22

        is_poorly_lit = is_too_dark or is_too_bright or is_uneven or is_deep_shadow
        
        # 4. Centering check
        face_center_x = face.x + face.w / 2.0
        face_center_y = face.y + face.h / 2.0
        frame_center_x = w / 2.0
        frame_center_y = h / 2.0
        
        offset_x = abs(face_center_x - frame_center_x) / (w / 2.0)
        offset_y = abs(face_center_y - frame_center_y) / (h / 2.0)
        is_centered = (offset_x < 0.65) and (offset_y < 0.65)
        
        # Overall quality check with specific guidance
        error_msg = None
        if size_ratio < self.min_face_ratio:
            error_msg = "Face is too far. Please move closer to the camera."
        elif size_ratio > self.max_face_ratio:
            error_msg = "Face is too close. Please step back slightly."
        elif is_too_dark or is_deep_shadow:
            error_msg = "Environment too dark. Please face a light source or turn on a light."
        elif is_too_bright:
            error_msg = "Lighting too harsh / glare on face. Avoid strong direct glare."
        elif is_uneven:
            error_msg = "Uneven lighting / shadows on face. Please face the light directly."
        elif is_blurry:
            error_msg = "Image is blurry. Please hold still."
        elif not is_centered:
            error_msg = "Please position your face inside the central guide oval."
            
        is_acceptable = (error_msg is None)
        
        return QualityMetrics(
            is_acceptable=is_acceptable,
            face_count=1,
            sharpness_score=sharpness,
            is_blurry=is_blurry,
            brightness_score=brightness,
            is_poorly_lit=is_poorly_lit,
            face_size_ratio=size_ratio,
            is_centered=is_centered,
            error_message=error_msg
        )
