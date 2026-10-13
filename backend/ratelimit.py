"""In-memory sliding-window rate limiter.

Hand-written rather than pulled from slowapi for the same reason the backtest
engine is: it stays readable, and it stays testable without a running server.
Time is injected as an argument so the tests can advance the clock instead of
sleeping.

Scope: `RateLimiter` keeps its counters in this process, so on Cloud Run with
N instances its ceiling is N x limit. That is fine for the per-IP limit, which
runs on every request and only stops one address hammering the API.
`SharedRateLimiter` keeps per-user counts in Firestore so the backtest and
validation limits hold across instances. Neither is a billing quota; the
monthly run quota lives on the user's profile.
"""

import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
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


# ---------------------------------------------------------------------------
# Shared across instances
# ---------------------------------------------------------------------------

log = logging.getLogger("finertia")


class MemoryCounterStore:
    """Counter store held in this process. Two limiters given the same store
    behave like two Cloud Run instances sharing Firestore, which is what the
    tests use it for."""

    def __init__(self):
        self._counts: dict[str, int] = {}
        self._lock = Lock()

    def hit(self, current: str, previous: str) -> tuple[int, int]:
        with self._lock:
            self._counts[current] = self._counts.get(current, 0) + 1
            return self._counts[current], self._counts.get(previous, 0)

    def undo(self, current: str) -> None:
        with self._lock:
            self._counts[current] = self._counts.get(current, 0) - 1


class FirestoreCounterStore:
    """Counters in the `ratelimits` collection, one document per key per window.

    A check is ONE round trip, which matters because the database (nam5) is on
    the other side of the world from the API (asia-south1): a transaction would
    be begin + read + commit. Instead a single atomic batch increments this
    window's counter by 1 and the previous window's by 0, and Firestore returns
    the value each transform produced — both counts, with no read.

    `expires_at` is there for a Firestore TTL policy to sweep old windows.
    Without one the documents simply stay; each is a few bytes.
    """

    COLLECTION = "ratelimits"

    def __init__(self, db_factory):
        self._db_factory = db_factory

    def _ref(self, doc_id: str):
        return self._db_factory().collection(self.COLLECTION).document(doc_id)

    def hit(self, current: str, previous: str) -> tuple[int, int]:
        from firebase_admin import firestore  # noqa: PLC0415

        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        batch = self._db_factory().batch()
        batch.set(self._ref(current), {"n": firestore.Increment(1), "expires_at": expires}, merge=True)
        batch.set(self._ref(previous), {"n": firestore.Increment(0), "expires_at": expires}, merge=True)
        cur, prev = batch.commit()
        return int(cur.transform_results[0].integer_value), int(prev.transform_results[0].integer_value)

    def undo(self, current: str) -> None:
        from firebase_admin import firestore  # noqa: PLC0415

        self._ref(current).set({"n": firestore.Increment(-1)}, merge=True)


class SharedRateLimiter(RateLimiter):
    """`limit` events per `window_seconds` per key, counted across every instance.

    The in-process limiter above caps a user at N x limit on N instances. This
    one keeps its counts in a shared store, using the sliding-window-counter
    estimate: the previous window's count, weighted by how much of it still
    overlaps the sliding window, plus the current window's count. That keeps the
    property the in-process one was written for — no double burst at a window
    boundary — at the cost of two integers per key instead of a list of hits.

    If the store fails, the check falls back to the in-process limiter it
    inherits from: a rate limiter that takes the API down with the database
    would be worse than one that is temporarily per-instance.
    """

    def __init__(self, name: str, limit: int, window_seconds: float, store_factory):
        super().__init__(limit, window_seconds)
        self.name = name
        self._store_factory = store_factory
        self._store = None
        self._store_resolved = False

    def _get_store(self):
        if not self._store_resolved:
            self._store = self._store_factory()
            self._store_resolved = True
        return self._store

    def check(self, key: str, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        store = self._get_store()
        if store is None:
            return super().check(key, now)

        bucket = int(now // self.window)
        into = (now - bucket * self.window) / self.window
        safe_key = key.replace("/", "_")
        current = f"{self.name}:{safe_key}:{bucket}"
        previous = f"{self.name}:{safe_key}:{bucket - 1}"

        try:
            cur, prev = store.hit(current, previous)
        except Exception:  # noqa: BLE001 — any store failure means fall back
            log.warning("shared rate limit unavailable, using in-process", exc_info=True,
                        extra={"limiter": self.name})
            return super().check(key, now)

        estimate = prev * (1 - into) + cur
        if estimate <= self.limit:
            return {"allowed": True, "remaining": max(0, int(self.limit - estimate)), "retry_after": 0.0}

        # Rejected attempts are not counted, as in the in-process limiter: a
        # client that keeps retrying must not keep pushing its own window out.
        try:
            store.undo(current)
        except Exception:  # noqa: BLE001
            log.warning("could not undo a rejected rate-limit hit", exc_info=True,
                        extra={"limiter": self.name})
        held = cur - 1
        if held < self.limit and prev > 0:
            # Wait for the previous window to slide far enough out.
            need = 1 - (self.limit - 1 - held) / prev
            retry = (need - into) * self.window
        else:
            # This window alone is full; it becomes the previous one next.
            need = 1 - (self.limit - 1) / held if held > 0 else 0
            retry = (1 - into) * self.window + max(0.0, need) * self.window
        return {"allowed": False, "remaining": 0, "retry_after": max(0.0, retry)}
