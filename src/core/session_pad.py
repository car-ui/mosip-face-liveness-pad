"""Bounded video evidence collection. CLEAR means no current PAD veto, not live proof."""
from dataclasses import dataclass
from enum import Enum
import math

from .config import PADVerdict


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


class EvidenceState(str, Enum):
    COLLECTING = "COLLECTING"
    CLEAR = "CLEAR"
    REJECTED = "REJECTED"
    ERROR = "ERROR"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class EvidenceResult:
    state: EvidenceState
    attack_frames: int
    clear_frames: int
    reason: str


class SessionPADGate:
    def __init__(self, attack_frames=5, attack_seconds=.5, clear_frames=5,
                 clear_seconds=.25, max_gap_seconds=.75, max_wait_seconds=10):
        if (any(isinstance(v, bool) or not isinstance(v, int) for v in (attack_frames, clear_frames))
                or not all(_finite_number(v) for v in (attack_seconds, clear_seconds, max_gap_seconds, max_wait_seconds))
                or attack_frames < 1 or clear_frames < 1 or attack_seconds < 0 or clear_seconds < 0
                or max_gap_seconds <= 0 or max_wait_seconds <= 0):
            raise ValueError("Invalid PAD evidence policy")
        self.attack_frames_required = attack_frames
        self.attack_seconds = attack_seconds
        self.clear_frames_required = clear_frames
        self.clear_seconds = clear_seconds
        self.max_gap_seconds = max_gap_seconds
        self.max_wait_seconds = max_wait_seconds
        self.reset()

    def reset(self):
        self._last_time = None
        self._episode_start = None
        self._streak_start = None
        self._attack_frames = 0
        self._clear_frames = 0
        self._terminal = None

    def observe(self, verdict, now):
        if self._terminal is not None:
            return self._terminal
        if not _finite_number(now) or (self._last_time is not None and now < self._last_time):
            return self._result(EvidenceState.ERROR, "Invalid evidence clock")
        if self._episode_start is None:
            self._episode_start = now
        if self._last_time is not None and now - self._last_time > self.max_gap_seconds:
            self._attack_frames = self._clear_frames = 0
            self._streak_start = None
        self._last_time = now
        if verdict == PADVerdict.PROCESSING_ERROR:
            return self._result(EvidenceState.ERROR, "PAD engine unavailable")
        if now - self._episode_start >= self.max_wait_seconds:
            return self._result(EvidenceState.INCONCLUSIVE, "PAD observations did not settle")
        if verdict == PADVerdict.PRESENTATION_ATTACK:
            if self._attack_frames == 0:
                self._streak_start = now
            self._clear_frames = 0
            self._attack_frames += 1
            if (self._attack_frames >= self.attack_frames_required
                    and now - self._streak_start >= self.attack_seconds):
                return self._result(EvidenceState.REJECTED, "Sustained PAD rejection")
        elif verdict in (PADVerdict.BONA_FIDE_LIVE, PADVerdict.UNCERTAIN):
            if self._clear_frames == 0:
                self._streak_start = now
            self._attack_frames = 0
            self._clear_frames += 1
            if (self._clear_frames >= self.clear_frames_required
                    and now - self._streak_start >= self.clear_seconds):
                self._episode_start = None
                return self._result(EvidenceState.CLEAR, "Fresh non-attack observations")
        else:
            return self._result(EvidenceState.ERROR, "Unknown PAD verdict")
        return self._result(EvidenceState.COLLECTING, "Collecting fresh PAD observations")

    def _result(self, state, reason):
        result = EvidenceResult(state, self._attack_frames, self._clear_frames, reason)
        if state in (EvidenceState.REJECTED, EvidenceState.ERROR, EvidenceState.INCONCLUSIVE):
            self._terminal = result
        return result
