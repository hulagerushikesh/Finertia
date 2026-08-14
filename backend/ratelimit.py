"""In-memory sliding-window rate limiter.

Hand-written rather than pulled from slowapi for the same reason the backtest
engine is: it stays readable, and it stays testable without a running server.
Time is injected as an argument so the tests can advance the clock instead of
sleeping.

Scope: the counters live in this process. On Cloud Run with N instances the
effective ceiling is N x limit, which is fine for the job this does — stopping
one client from hammering an expensive endpoint. It is not a billing quota; the
per-user run limits in S6 will be enforced in Firestore, which is shared state.
"""

import time
from collections import deque
from threading import Lock


class RateLimiter:
    """Allow `limit` events per `window_seconds` for each key.

    Sliding window rather than fixed buckets: a fixed bucket lets a caller fire
    `limit` requests at 11:59:59 and `limit` more at 12:00:00, which is double
    the intended rate at exactly the moment it matters.
    """

    def __init__(self, limit: int, window_seconds: float):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = {}
        self._lock = Lock()

    def check(self, key: str, now: float | None = None) -> dict:
        """Record an attempt and report whether it is allowed.

        Returns {allowed, remaining, retry_after}. A rejected attempt is NOT
        recorded — otherwise a client that keeps retrying would keep pushing its
        own window forward and stay locked out indefinitely.
        """
        now = time.time() if now is None else now
        cutoff = now - self.window

        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= self.limit:
                # The window frees a slot when the oldest hit ages out.
                retry_after = max(0.0, hits[0] + self.window - now)
                return {
                    "allowed": False,
                    "remaining": 0,
                    "retry_after": retry_after,
                }

            hits.append(now)
            return {
                "allowed": True,
                "remaining": self.limit - len(hits),
                "retry_after": 0.0,
            }

    def reset(self, key: str) -> None:
        """Drop a key's history — used by tests and by admin unblocking."""
        with self._lock:
            self._hits.pop(key, None)

    def prune(self, now: float | None = None) -> int:
        """Drop keys whose entire window has expired; returns how many went.

        Without this the dict grows one entry per distinct caller forever, which
        on a long-lived instance is a slow memory leak.
        """
        now = time.time() if now is None else now
        cutoff = now - self.window
        with self._lock:
            dead = [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
            for k in dead:
                del self._hits[k]
            return len(dead)

    @property
    def tracked_keys(self) -> int:
        """How many keys currently hold history — exposed for the health check."""
        with self._lock:
            return len(self._hits)
