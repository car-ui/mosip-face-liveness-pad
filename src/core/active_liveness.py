"""
Active Liveness Detection Engine
Uses MediaPipe FaceLandmarker with 52 Blendshapes & Facial Landmark Geometry:
- Real-time Blink Detection via temporal EAR state machine (OPEN -> CLOSED -> OPEN)
- Real-time Smile Detection via dynamic relative baseline delta sustained across N frames
- Facial-Landmark Geometric Head-Pose Estimation via temporal transitions (CENTER -> TURN -> CENTER)

100% Offline, high performance (~30 FPS on CPU).
"""

from dataclasses import dataclass, field
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
    stage: str = "INIT"  # Temporal stage: e.g. "INIT", "STAGE_1", "STAGE_2", "VERIFIED"
    baseline_value: Optional[float] = None
    baseline_frames_recorded: int = 0
    consecutive_action_frames: int = 0

    @property
    def challenge_type(self) -> ChallengeType:
        return self.challenge


class ActiveLivenessDetector:
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, "assets", "models", "face_landmarker.task")
            
        self.model_path = model_path
        self._landmarker = None
        self._setup_landmarker()

    def _setup_landmarker(self) -> None:
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
        """Calculates Eye Aspect Ratio (EAR) from 6 2D eye landmark points."""
        p1, p2, p3, p4, p5, p6 = [landmarks_2d[idx] for idx in eye_indices]
        v1 = np.linalg.norm(p2 - p6)
        v2 = np.linalg.norm(p3 - p5)
        h = np.linalg.norm(p1 - p4)
        if h < 1e-5:
            return 0.30
        return float((v1 + v2) / (2.0 * h))

    def estimate_head_pose(self, landmarks_2d: np.ndarray, img_w: int, img_h: int) -> Tuple[float, float, float]:
        """
        Direct facial landmark symmetry & geometry:
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

    def process_frame(self,
                      bgr_frame: np.ndarray,
                      challenge_state: Optional[ChallengeState] = None) -> Tuple[Dict[str, Any], Optional[ChallengeState]]:
        h, w = bgr_frame.shape[:2]
        telemetry = {
            "landmarks_detected": False,
            "blink_score": 0.0,
            "ear": 0.30,
            "smile_score": 0.0,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "face_box": None,
            "face_center": (w / 2.0, h / 2.0),
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
                raw_landmarks = res.face_landmarks[0]
                landmarks_2d = np.array([(lm.x * w, lm.y * h) for lm in raw_landmarks], dtype=np.float64)

                # Bounding box
                min_x = int(np.min(landmarks_2d[:, 0]))
                max_x = int(np.max(landmarks_2d[:, 0]))
                min_y = int(np.min(landmarks_2d[:, 1]))
                max_y = int(np.max(landmarks_2d[:, 1]))
                box_w = max(1, max_x - min_x)
                box_h = max(1, max_y - min_y)

                # Head pose
                yaw, pitch, roll = self.estimate_head_pose(landmarks_2d, w, h)

                # Extract blendshapes
                blink_score = 0.0
                smile_score = 0.0
                if res.face_blendshapes and len(res.face_blendshapes) > 0:
                    blendshape_map = {b.category_name: b.score for b in res.face_blendshapes[0]}
                    blink_l = blendshape_map.get("eyeBlinkLeft", 0.0)
                    blink_r = blendshape_map.get("eyeBlinkRight", 0.0)
                    blink_score = float((blink_l + blink_r) / 2.0)

                    smile_l = blendshape_map.get("mouthSmileLeft", 0.0)
                    smile_r = blendshape_map.get("mouthSmileRight", 0.0)
                    smile_score = float((smile_l + smile_r) / 2.0)

                # Calculate geometric EAR (Left eye: 33, 160, 158, 133, 153, 144)
                ear_l = self.calculate_ear(landmarks_2d, [33, 160, 158, 133, 153, 144])
                ear_r = self.calculate_ear(landmarks_2d, [362, 385, 387, 263, 373, 380])
                avg_ear = float((ear_l + ear_r) / 2.0)

                telemetry.update({
                    "landmarks_detected": True,
                    "blink_score": round(blink_score, 3),
                    "ear": round(avg_ear, 3),
                    "smile_score": round(smile_score, 3),
                    "yaw": round(yaw, 1),
                    "pitch": round(pitch, 1),
                    "roll": round(roll, 1),
                    "face_box": (min_x, min_y, box_w, box_h),
                    "face_center": ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0),
                    "landmarks_2d": landmarks_2d
                })

        updated_challenge = None
        if challenge_state is not None:
            updated_challenge = self._evaluate_challenge(challenge_state, telemetry)

        return telemetry, updated_challenge

    def _evaluate_challenge(self, state: ChallengeState, telemetry: Dict[str, Any]) -> ChallengeState:
        if not state.is_active:
            return state

        elapsed = time.time() - state.start_time
        
        # Timeout enforcement
        if elapsed > state.timeout_seconds:
            state.is_active = False
            state.is_completed = False
            state.feedback_message = "Challenge timed out. Please try again."
            return state

        if not telemetry["landmarks_detected"]:
            state.feedback_message = "Face not clearly visible. Look at the camera."
            return state

        target = state.challenge

        # Record initial baseline expression across first 4 frames
        if state.baseline_frames_recorded < 4:
            state.baseline_frames_recorded += 1
            if target == ChallengeType.SMILE:
                state.baseline_value = telemetry["smile_score"]
            elif target in (ChallengeType.TURN_LEFT, ChallengeType.TURN_RIGHT):
                state.baseline_value = telemetry["yaw"]
            elif target in (ChallengeType.LOOK_UP, ChallengeType.LOOK_DOWN):
                state.baseline_value = telemetry["pitch"]
            elif target == ChallengeType.BLINK:
                state.baseline_value = telemetry["ear"]
            state.stage = "RECORDING_BASELINE"
            return state

        # 1. BLINK: True Temporal EAR State Machine (OPEN -> CLOSED -> OPEN)
        if target == ChallengeType.BLINK:
            ear = telemetry["ear"]
            blink_score = telemetry["blink_score"]
            yaw = telemetry["yaw"]

            if abs(yaw) > 15.0:
                state.feedback_message = "Please face the camera directly to blink"
                return state

            # Stage 0: Initial open state
            if state.stage in ("INIT", "RECORDING_BASELINE"):
                state.stage = "WAITING_CLOSING"
                state.progress = 0.2
                state.feedback_message = "Please blink naturally"

            # Stage 1: Detect eyes closing (EAR drops or blendshape rises)
            elif state.stage == "WAITING_CLOSING":
                if ear < 0.22 or blink_score > 0.45:
                    state.stage = "EYES_CLOSED"
                    state.action_detected = True
                    state.progress = 0.6
                    state.feedback_message = "Eyes closed, now open eyes..."
                else:
                    state.feedback_message = "Please blink naturally"

            # Stage 2: Detect eyes reopening (EAR rises back to normal open range)
            elif state.stage == "EYES_CLOSED":
                if ear > 0.27 and blink_score < 0.25:
                    state.stage = "VERIFIED"
                    state.is_completed = True
                    state.progress = 1.0
                    state.feedback_message = "Blink verified! Hold still."
                else:
                    state.progress = 0.7
                    state.feedback_message = "Now open your eyes..."

        # 2. SMILE: Baseline-Neutral Relative Delta with Temporal Hold
        elif target == ChallengeType.SMILE:
            smile_score = telemetry["smile_score"]
            baseline = state.baseline_value if state.baseline_value is not None else 0.0
            smile_delta = smile_score - baseline
            yaw = telemetry["yaw"]

            if abs(yaw) > 14.0:
                state.feedback_message = "Please face the camera and smile"
                state.consecutive_action_frames = 0
                state.progress = 0.0
                return state

            # Require dynamic transition from initial baseline (blocks static photos already smiling!)
            if smile_delta > 0.15 and smile_score > 0.35:
                state.consecutive_action_frames += 1
                state.action_detected = True
                state.progress = min(0.95, 0.5 + (state.consecutive_action_frames * 0.18))
                
                # Must sustain smile for at least 3 consecutive frames
                if state.consecutive_action_frames >= 3:
                    state.stage = "VERIFIED"
                    state.is_completed = True
                    state.progress = 1.0
                    state.feedback_message = "Smile verified! Hold still."
                else:
                    state.feedback_message = "Holding smile..."
            else:
                state.consecutive_action_frames = 0
                state.progress = min(0.45, max(0.0, smile_delta / 0.15 * 0.45))
                state.feedback_message = "Please smile naturally"

        # 3. TURN LEFT: Temporal State Machine (CENTER -> LEFT -> CENTER)
        elif target == ChallengeType.TURN_LEFT:
            yaw = telemetry["yaw"]
            baseline = state.baseline_value if state.baseline_value is not None else 0.0
            yaw_delta = yaw - baseline

            # Guard against wrong direction turn
            if yaw < -6.0:
                state.progress = 0.0
                state.consecutive_action_frames = 0
                state.feedback_message = "Wrong direction! Turn to your LEFT"
                return state

            # Stage 1: Waiting for left turn rotation (yaw_delta > 13.0)
            if state.stage in ("INIT", "RECORDING_BASELINE", "WAITING_TURN"):
                state.stage = "WAITING_TURN"
                if yaw_delta > 12.0 and yaw > 12.0:
                    state.stage = "TURNED_LEFT"
                    state.action_detected = True
                    state.progress = 0.6
                    state.feedback_message = "Turn detected! Now return to center..."
                else:
                    state.progress = min(0.5, max(0.0, yaw_delta / 12.0 * 0.5))
                    state.feedback_message = "Please turn your head to your LEFT"

            # Stage 2: Return to center position (|yaw| < 7.0)
            elif state.stage == "TURNED_LEFT":
                if abs(yaw) < 7.5:
                    state.stage = "VERIFIED"
                    state.is_completed = True
                    state.progress = 1.0
                    state.feedback_message = "Left turn verified! Hold still."
                else:
                    state.progress = 0.8
                    state.feedback_message = "Now return your head to CENTER..."

        # 4. TURN RIGHT: Temporal State Machine (CENTER -> RIGHT -> CENTER)
        elif target == ChallengeType.TURN_RIGHT:
            yaw = telemetry["yaw"]
            baseline = state.baseline_value if state.baseline_value is not None else 0.0
            yaw_delta = yaw - baseline

            # Guard against wrong direction turn
            if yaw > 6.0:
                state.progress = 0.0
                state.consecutive_action_frames = 0
                state.feedback_message = "Wrong direction! Turn to your RIGHT"
                return state

            # Stage 1: Waiting for right turn rotation (yaw_delta < -12.0)
            if state.stage in ("INIT", "RECORDING_BASELINE", "WAITING_TURN"):
                state.stage = "WAITING_TURN"
                if yaw_delta < -12.0 and yaw < -12.0:
                    state.stage = "TURNED_RIGHT"
                    state.action_detected = True
                    state.progress = 0.6
                    state.feedback_message = "Turn detected! Now return to center..."
                else:
                    state.progress = min(0.5, max(0.0, abs(yaw_delta) / 12.0 * 0.5))
                    state.feedback_message = "Please turn your head to your RIGHT"

            # Stage 2: Return to center position (|yaw| < 7.0)
            elif state.stage == "TURNED_RIGHT":
                if abs(yaw) < 7.5:
                    state.stage = "VERIFIED"
                    state.is_completed = True
                    state.progress = 1.0
                    state.feedback_message = "Right turn verified! Hold still."
                else:
                    state.progress = 0.8
                    state.feedback_message = "Now return your head to CENTER..."

        # 5. LOOK UP: Pitch adjustment
        elif target == ChallengeType.LOOK_UP:
            pitch = telemetry["pitch"]
            if pitch < -10.0:
                state.stage = "VERIFIED"
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Look up verified! Hold still."
            else:
                state.feedback_message = "Please look slightly up"

        # 6. LOOK DOWN: Pitch adjustment
        elif target == ChallengeType.LOOK_DOWN:
            pitch = telemetry["pitch"]
            if pitch > 10.0:
                state.stage = "VERIFIED"
                state.action_detected = True
                state.is_completed = True
                state.progress = 1.0
                state.feedback_message = "Look down verified! Hold still."
            else:
                state.feedback_message = "Please look slightly down"

        return state
