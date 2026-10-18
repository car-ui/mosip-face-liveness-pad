"""Aggregate counters retain no identifiers, frames, or individual scores."""
from collections import Counter
import threading


class OperationalMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._outcomes = Counter()
        self._total_seconds = self._challenge_seconds = 0.0
        self._challenge_sessions = self._retried_sessions = 0

    def record(self, outcome, seconds, retries=0, challenge_seconds=0.0):
        with self._lock:
            self._outcomes[outcome] += 1
            self._total_seconds += seconds
            self._retried_sessions += int(retries > 0)
            if challenge_seconds > 0:
                self._challenge_seconds += challenge_seconds
                self._challenge_sessions += 1

    def snapshot(self):
        with self._lock:
            count = sum(self._outcomes.values())
            return {"sessions": count, "outcomes": dict(self._outcomes),
                "averageCaptureSeconds": self._total_seconds / count if count else None,
                "averageChallengeSeconds": self._challenge_seconds / self._challenge_sessions if self._challenge_sessions else None,
                "retryRate": self._retried_sessions / count if count else None,
                "failureRate": (count - self._outcomes["SUCCESS"]) / count if count else None,
                "scope": "This process only, including simulator sessions. Not PAD accuracy."}
