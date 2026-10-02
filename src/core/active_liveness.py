"""
Active Liveness Detection Engine
Uses MediaPipe FaceLandmarker with 52 Blendshapes & 3D Landmark Geometry:
- Real-time Blink Detection via Google AI blendshapes ('eyeBlinkLeft', 'eyeBlinkRight')
- Real-time Smile Detection via Google AI blendshapes ('mouthSmileLeft', 'mouthSmileRight')
- 3D Head Pose Estimation (Yaw/Pitch) via SolvePnP for Turn Left/Right/Up/Down

100% Offline, high performance (~30 FPS).
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List
import os
import cv2
import numpy as np
import time
from .config import ChallengeType


@dataclass
class ChallengeState:
    challenge: ChallengeType
    is_active: bool
    start_time: float
    timeout_seconds: float
    is_completed: bool
    progress: float  # 0.0 to 1.0
    action_detected: bool
    feedback_message: str
    baseline_value: Optional[float] = None
    baseline_frames_recorded: int = 0


class ActiveLivenessDetector:
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            # Default to assets/models/face_landmarker.task
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, "assets", "models", "face_landmarker.task")
            
        self.model_path = model_path
        self._landmarker = None
        self._setup_landmarker()

        self._blink_detected_closing = False
        self.model_points = np.array([
            (0.0, 0.0, 0.0),          # Nose tip
            (0.0, -330.0, -65.0),     # Chin
            (-225.0, 170.0, -135.0),  # Left eye corner
            (225.0, 170.0, -135.0),   # Right eye corner
            (-150.0, -150.0, -125.0), # Left mouth corner
            (150.0, -150.0, -125.0)   # Right mouth corner
        ], dtype=np.float64)

    def _setup_landmarker(self):
        if not os.path.exists(self.model_path):
            return

        try:
            from mediapipe.tasks.python import vision
            from mediapipe.tasks import python as mp_python
            
            base_options = mp_python.BaseOptions(model_asset_path=self.model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,
                num_faces=1
            )
            self._landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception:
            self._landmarker = None

    def calculate_ear(self, landmarks_2d: np.ndarray, eye_indices: List[int]) -> float:
        p1, p2, p3, p4, p5, p6 = [landmarks_2d[idx] for idx in eye_indices]
        v1 = np.linalg.norm(p2 - p6)
        v2 = np.linalg.norm(p3 - p5)
        h = np.linalg.norm(p1 - p4)
        if h < 1e-5:
            return 0.3
        return float((v1 + v2) / (2.0 * h))

    def estimate_head_pose(self, landmarks_2d: np.ndarray, img_w: int, img_h: int) -> Tuple[float, float, float]:
        """
        Direct facial landmark geometry:
        Landmark 1: Nose tip
        Landmark 33: Right eye outer corner (user's right, image-left)
        Landmark 263: Left eye outer corner (user's left, image-right)
        Landmark 10: Forehead top center
        Landmark 152: Chin
        """
        nose_x, nose_y = landmarks_2d[1]
        r_eye_x, r_eye_y = landmarks_2d[33]
        l_eye_x, l_eye_y = landmarks_2d[263]
        forehead_x, forehead_y = landmarks_2d[10]
        chin_x, chin_y = landmarks_2d[152]

        d_r = abs(nose_x - r_eye_x)
        d_l = abs(l_eye_x - nose_x)
        total_eye_span = d_r + d_l + 1e-5

        # Horizontal yaw:
        # Turning to user's LEFT: nose moves right in image -> d_r > d_l -> yaw > 0
        # Turning to user's RIGHT: nose moves left in image -> d_l > d_r -> yaw < 0
        turn_ratio = (d_r - d_l) / total_eye_span
        yaw = float(turn_ratio * 55.0)

        # Vertical pitch:
        d_up = abs(nose_y - forehead_y)
        d_down = abs(chin_y - nose_y)
        vert_ratio = (d_up - d_down) / (d_up + d_down + 1e-5)
        pitch = float(vert_ratio * 45.0)

        # Roll:
        eye_dx = l_eye_x - r_eye_x
        eye_dy = l_eye_y - r_eye_y
        roll = float(np.degrees(np.arctan2(eye_dy, eye_dx)))

        return yaw, pitch, roll

    def process_frame(self, bgr_frame: np.ndarray, challenge_state: Optional[ChallengeState] = None) -> Tuple[Dict[str, Any], Optional[ChallengeState]]:
        h, w = bgr_frame.shape[:2]
        telemetry = {
            "landmarks_detected": False,
            "blink_score": 0.0,
            "smile_score": 0.0,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "face_box": None,
            "landmarks_2d": None
        }

        if self._landmarker is None:
            self._setup_landmarker()

        if self._landmarker is not None:
            import mediapipe as mp
            rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = self._landmarker.detect(mp_image)

            if res.face_landmarks and len(res.face_landmarks) > 0:
                lms = res.face_landmarks[0]
                landmarks_2d = np.array([[lm.x * w, lm.y * h] for lm in lms], dtype=np.float64)
                
                # Compute bounding box from landmarks
                min_x = int(max(0, np.min(landmarks_2d[:, 0])))
                min_y = int(max(0, np.min(landmarks_2d[:, 1])))
                max_x = int(min(w, np.max(landmarks_2d[:, 0])))
                max_y = int(min(h, np.max(landmarks_2d[:, 1])))
                box_w = max_x - min_x
                box_h = max_y - min_y
                
                telemetry["landmarks_detected"] = True
                telemetry["landmarks_2d"] = landmarks_2d
                telemetry["face_box"] = (min_x, min_y, box_w, box_h)

                # Blendshapes
                if res.face_blendshapes and len(res.face_blendshapes) > 0:
                    shapes = {s.category_name: s.score for s in res.face_blendshapes[0]}
                    blink_l = shapes.get("eyeBlinkLeft", 0.0)
                    blink_r = shapes.get("eyeBlinkRight", 0.0)
                    smile_l = shapes.get("mouthSmileLeft", 0.0)
                    smile_r = shapes.get("mouthSmileRight", 0.0)

                    telemetry["blink_score"] = float((blink_l + blink_r) / 2.0)
                    telemetry["smile_score"] = float(max(smile_l, smile_r))

                # Robust landmark pose angles
                yaw, pitch, roll = self.estimate_head_pose(landmarks_2d, w, h)
                telemetry["yaw"] = yaw
                telemetry["pitch"] = pitch
                telemetry["roll"] = roll

        updated_challenge = challenge_state
        if challenge_state and challenge_state.is_active and not challenge_state.is_completed:
            updated_challenge = self._evaluate_challenge(challenge_state, telemetry)

        return telemetry, updated_challenge

    def _evaluate_challenge(self, state: ChallengeState, telemetry: Dict[str, Any]) -> ChallengeState:
        elapsed = time.time() - state.start_time
        
        if elapsed > state.timeout_seconds:
            state.is_active = False
            state.is_completed = False
            state.feedback_message = "Challenge timed out. Please try again."
            return state

        if not telemetry["landmarks_detected"]:
            state.feedback_message = "Face not clearly visible. Look at the camera."
            return state

        target = state.challenge

        # Collect baseline expression over the first 4 frames of this challenge
        if state.baseline_frames_recorded < 4:
            state.baseline_frames_recorded += 1
            if target == ChallengeType.SMILE:
                state.baseline_value = telemetry["smile_score"]
            elif target in (ChallengeType.TURN_LEFT, ChallengeType.TURN_RIGHT):
                state.baseline_value = telemetry["yaw"]
            elif target in (ChallengeType.LOOK_UP, ChallengeType.LOOK_DOWN):
                state.baseline_value = telemetry["pitch"]
            return state

        if target == ChallengeType.BLINK:
            blink_score = telemetry["blink_score"]
            yaw = telemetry["yaw"]
            if abs(yaw) > 14.0:
                state.feedback_message = "Please face the camera and blink"
            elif blink_score > 0.45:
                self._blink_detected_closing = True
                state.action_detected = True
                state.progress = 0.6
                state.feedback_message = "Blink detected, now open eyes..."
            elif self._blink_detected_closing and blink_score < 0.25:
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Blink verified! Hold still."
                self._blink_detected_closing = False
            else:
                state.feedback_message = "Please blink naturally"

        elif target == ChallengeType.SMILE:
            smile_score = telemetry["smile_score"]
            baseline = state.baseline_value if state.baseline_value is not None else 0.0
            smile_delta = smile_score - baseline
            yaw = telemetry["yaw"]
            if abs(yaw) > 12.0:
                state.feedback_message = "Please face the camera and smile"
                state.progress = 0.0
            # Must dynamically increase smile from baseline expression (static smiling photos fail this!)
            elif smile_delta > 0.16 and smile_score > 0.38:
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Smile verified! Hold still."
            else:
                state.progress = min(0.9, max(0.0, smile_delta / 0.16))
                state.feedback_message = "Please smile"

        elif target == ChallengeType.TURN_LEFT:
            yaw = telemetry["yaw"]
            baseline = state.baseline_value if state.baseline_value is not None else 0.0
            yaw_delta = yaw - baseline
            if yaw < -6.0:
                state.progress = 0.0
                state.feedback_message = "Wrong direction! Turn to your LEFT"
            # Must dynamically rotate head left from baseline
            elif yaw_delta > 11.0 and yaw > 12.0:
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Left turn verified! Return to center."
            else:
                state.progress = min(0.9, max(0.0, yaw_delta / 11.0))
                state.feedback_message = "Please turn your head to your LEFT"

        elif target == ChallengeType.TURN_RIGHT:
            yaw = telemetry["yaw"]
            baseline = state.baseline_value if state.baseline_value is not None else 0.0
            yaw_delta = yaw - baseline
            if yaw > 6.0:
                state.progress = 0.0
                state.feedback_message = "Wrong direction! Turn to your RIGHT"
            # Must dynamically rotate head right from baseline
            elif yaw_delta < -11.0 and yaw < -12.0:
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Right turn verified! Return to center."
            else:
                state.progress = min(0.9, max(0.0, abs(yaw_delta) / 11.0))
                state.feedback_message = "Please turn your head to your RIGHT"

        elif target == ChallengeType.LOOK_UP:
            pitch = telemetry["pitch"]
            if pitch < -10.0:
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Look up verified! Hold still."
            else:
                state.feedback_message = "Please look slightly up"

        elif target == ChallengeType.LOOK_DOWN:
            pitch = telemetry["pitch"]
            if pitch > 10.0:
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Look down verified! Hold still."
            else:
                state.feedback_message = "Please look slightly down"

        return state
