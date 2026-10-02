"""
Dynamic Challenge Manager
Handles random, unpredictable challenge selection, state progression,
countdown timers, retry limits, and failure handling.
"""

import random
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

    def reset(self):
        """Reset manager for a new resident/operator session."""
        self.current_retry = 0
        self.completed_challenges.clear()
        self.active_challenge_state = None
        self._last_challenge = None

    def can_retry(self) -> bool:
        return self.current_retry < self.policy.max_retries

    def increment_retry(self):
        self.current_retry += 1
        self.active_challenge_state = None

    def is_all_challenges_satisfied(self) -> bool:
        return len(self.completed_challenges) >= self.policy.min_challenges

    def get_remaining_challenge_count(self) -> int:
        return max(0, self.policy.min_challenges - len(self.completed_challenges))

    def generate_next_challenge(self) -> ChallengeState:
        """
        Dynamically and unpredictably selects the next facial challenge from the pool,
        avoiding repeating the immediately preceding challenge.
        """
        available = [c for c in self.allowed_challenges if c != self._last_challenge]
        if not available:
            available = self.allowed_challenges

        selected = random.choice(available)
        self._last_challenge = selected

        prompts = {
            ChallengeType.BLINK: "Please blink naturally",
            ChallengeType.SMILE: "Please smile",
            ChallengeType.TURN_LEFT: "Please turn your head to the left",
            ChallengeType.TURN_RIGHT: "Please turn your head to the right",
            ChallengeType.LOOK_UP: "Please look slightly up",
            ChallengeType.LOOK_DOWN: "Please look slightly down"
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

    def record_challenge_success(self):
        if self.active_challenge_state and self.active_challenge_state.is_completed:
            self.completed_challenges.append(self.active_challenge_state.challenge)
            self.active_challenge_state = None
