"""
Temporal Liveness Buffer & Consistency Analysis
Maintains a rolling temporal window across video frames to prevent single-frame anomalies
from improperly skewing biometric decisions.
Evaluates:
- Rolling weighted average of liveness scores
- Consecutive frame verification for action stability
- Micro-motion variance across landmarks (identifies perfectly rigid static 2D presentations)
"""

from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import numpy as np


@dataclass
class FrameTelemetryRecord:
    timestamp: float
    liveness_score: float
    is_live: bool
    attack_detected: bool
    ear: float
    smile_score: float
    yaw: float
    pitch: float
    face_center: Tuple[float, float]
    landmark_coords: Optional[np.ndarray] = None


@dataclass
class TemporalAnalysisResult:
    frame_count: int
    rolling_liveness_score: float
    min_liveness_score: float
    max_liveness_score: float
    liveness_variance: float
    consecutive_live_frames: int
    consecutive_attack_frames: int
    micro_motion_detected: bool
    micro_motion_score: float
    temporal_stability: float  # 0.0 to 1.0 (consistency across window)


class TemporalLivenessBuffer:
    def __init__(self, window_size: int = 15, min_motion_threshold: float = 0.35):
        """
        :param window_size: Number of frames in the rolling temporal window.
        :param min_motion_threshold: Minimum expected pixel jitter for live human micro-movement.
        """
        self.window_size = max(5, window_size)
        self.min_motion_threshold = min_motion_threshold
        self._buffer: deque[FrameTelemetryRecord] = deque(maxlen=self.window_size)
        self._consecutive_live: int = 0
        self._consecutive_attack: int = 0

    def clear(self) -> None:
        """Clears the temporal window for a new capture session."""
        self._buffer.clear()
        self._consecutive_live = 0
        self._consecutive_attack = 0

    def add_frame(self,
                  timestamp: float,
                  liveness_score: float,
                  is_live: bool,
                  attack_detected: bool,
                  ear: float = 0.3,
                  smile_score: float = 0.0,
                  yaw: float = 0.0,
                  pitch: float = 0.0,
                  face_center: Tuple[float, float] = (0.0, 0.0),
                  landmark_coords: Optional[np.ndarray] = None) -> None:
        """Appends a new frame record into the temporal rolling window."""
        record = FrameTelemetryRecord(
            timestamp=timestamp,
            liveness_score=float(np.clip(liveness_score, 0.0, 1.0)),
            is_live=is_live,
            attack_detected=attack_detected,
            ear=ear,
            smile_score=smile_score,
            yaw=yaw,
            pitch=pitch,
            face_center=face_center,
            landmark_coords=landmark_coords
        )
        self._buffer.append(record)

        if is_live and not attack_detected:
            self._consecutive_live += 1
            self._consecutive_attack = 0
        elif attack_detected:
            self._consecutive_attack += 1
            self._consecutive_live = 0
        else:
            self._consecutive_live = 0
            self._consecutive_attack = 0

    def analyze(self) -> TemporalAnalysisResult:
        """
        Computes temporal statistics and consistency across the active window.
        """
        if not self._buffer:
            return TemporalAnalysisResult(
                frame_count=0,
                rolling_liveness_score=0.0,
                min_liveness_score=0.0,
                max_liveness_score=0.0,
                liveness_variance=0.0,
                consecutive_live_frames=0,
                consecutive_attack_frames=0,
                micro_motion_detected=False,
                micro_motion_score=0.0,
                temporal_stability=0.0
            )

        scores = [r.liveness_score for r in self._buffer]
        n = len(scores)

        # Exponentially weighted rolling average giving higher weight to recent frames
        weights = np.exp(np.linspace(-1.0, 0.0, n))
        weights /= np.sum(weights)
        weighted_score = float(np.sum(np.array(scores) * weights))

        min_score = float(np.min(scores))
        max_score = float(np.max(scores))
        variance = float(np.var(scores))

        # Micro-motion analysis across face centers or landmarks
        # Live subjects naturally exhibit involuntary micro-saccades and physiological drift (~0.4 - 3.5px)
        # Static printed photos clamped on stands or paused screen replays have near-zero center variance
        centers = np.array([r.face_center for r in self._buffer])
        if len(centers) >= 5:
            motion_var = float(np.mean(np.var(centers, axis=0)))
            # Scale motion score to [0.0, 1.0]
            motion_score = float(np.clip(motion_var / 2.5, 0.0, 1.0))
            micro_motion_detected = motion_var >= self.min_motion_threshold
        else:
            motion_score = 0.5
            micro_motion_detected = True

        # Temporal stability: Low variance across high scores indicates reliable decision
        stability = float(np.clip(1.0 - (np.std(scores) * 2.0), 0.0, 1.0))

        return TemporalAnalysisResult(
            frame_count=n,
            rolling_liveness_score=round(weighted_score, 3),
            min_liveness_score=round(min_score, 3),
            max_liveness_score=round(max_score, 3),
            liveness_variance=round(variance, 4),
            consecutive_live_frames=self._consecutive_live,
            consecutive_attack_frames=self._consecutive_attack,
            micro_motion_detected=micro_motion_detected,
            micro_motion_score=round(motion_score, 3),
            temporal_stability=round(stability, 3)
        )

    def is_action_sustained(self, action_field: str, threshold: float, required_frames: int = 3) -> bool:
        """
        Verifies that a landmark metric (e.g. smile_score, ear) remained above/below
        the threshold for at least `required_frames` consecutive frames in the buffer.
        """
        if len(self._buffer) < required_frames:
            return False
            
        recent = list(self._buffer)[-required_frames:]
        for r in recent:
            val = getattr(r, action_field, 0.0)
            if val < threshold:
                return False
        return True
