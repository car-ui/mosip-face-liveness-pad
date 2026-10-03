"""
Dynamic Challenge Manager
Handles cryptographically unpredictable challenge selection, multi-challenge progression,
timeout countdowns, retry policies, and session state.
"""

import secrets
import time
from typing import List, Optional
from .config import ChallengeType, WorkflowPolicy
from .active_liveness import ChallengeState


class ChallengeManager:
    def __init__(self, policy: WorkflowPolicy, allowed_challenges: Optional[List[ChallengeType]] = None):
        self.policy = policy
        self.allowed_challenges = allowed_challenges or [
            ChallengeType.BLINK,
            ChallengeType.SMILE,
            ChallengeType.TURN_LEFT,
            ChallengeType.TURN_RIGHT
        ]
        
        self.current_retry = 0
        self.completed_challenges: List[ChallengeType] = []
        self.active_challenge_state: Optional[ChallengeState] = None
        self._last_challenge: Optional[ChallengeType] = None
        self._rng = secrets.SystemRandom()

    def reset(self) -> None:
        """Reset challenge manager for a new resident/operator session."""
        self.current_retry = 0
        self.completed_challenges.clear()
        self.active_challenge_state = None
        self._last_challenge = None

    def can_retry(self) -> bool:
        """Checks if retries are remaining within policy limits."""
        return self.current_retry < self.policy.max_retries

    def increment_retry(self) -> None:
        """Records an attempt failure and invalidates active challenge."""
        self.current_retry += 1
        self.active_challenge_state = None

    def is_all_challenges_satisfied(self) -> bool:
        """Checks whether the session has satisfied the required challenge count."""
        return len(self.completed_challenges) >= self.policy.min_challenges

    def get_remaining_challenge_count(self) -> int:
        """Returns number of challenges remaining to satisfy policy."""
        return max(0, self.policy.min_challenges - len(self.completed_challenges))

    def generate_next_challenge(self) -> ChallengeState:
        """
        Dynamically and unpredictably selects the next facial challenge from the pool
        using a secure random generator, preventing immediate repetition.
        """
        available = [c for c in self.allowed_challenges if c != self._last_challenge]
        if not available:
            available = self.allowed_challenges

        selected = self._rng.choice(available)
        self._last_challenge = selected

        prompts = {
            ChallengeType.BLINK: "Please blink naturally",
            ChallengeType.SMILE: "Please smile naturally",
            ChallengeType.TURN_LEFT: "Please turn your head to your LEFT and return to center",
            ChallengeType.TURN_RIGHT: "Please turn your head to your RIGHT and return to center",
            ChallengeType.LOOK_UP: "Please look slightly up and return to center",
            ChallengeType.LOOK_DOWN: "Please look slightly down and return to center"
        }

        self.active_challenge_state = ChallengeState(
            challenge=selected,
            is_active=True,
            start_time=time.time(),
            timeout_seconds=self.policy.challenge_timeout_seconds,
            is_completed=False,
            progress=0.0,
            action_detected=False,
            feedback_message=prompts.get(selected, "Please follow the on-screen instruction")
        )
        return self.active_challenge_state

    def record_challenge_success(self) -> None:
        """Records successful completion of the active challenge."""
        if self.active_challenge_state and self.active_challenge_state.is_completed:
            self.completed_challenges.append(self.active_challenge_state.challenge)
            self.active_challenge_state = None
