"""SharedRateLimiter: per-user limits that hold across Cloud Run instances.

Two limiters given one MemoryCounterStore stand in for two instances sharing
Firestore. test_shared_ratelimit_firestore.py runs the same check against the
Firestore emulator.
"""

import pytest

from ratelimit import MemoryCounterStore, SharedRateLimiter

T0 = 1_000_020.0  # the start of a 60 s window (1_000_020 / 60 = 16_667)


def pair(limit=5, store=None):
    store = store or MemoryCounterStore()
    a = SharedRateLimiter("bt", limit, 60, store_factory=lambda: store)
    b = SharedRateLimiter("bt", limit, 60, store_factory=lambda: store)
    return a, b


def test_limit_holds_across_two_instances():
    a, b = pair(limit=5)
    hits = [a, b, a, b, a]
    assert all(lim.check("u1", now=T0 + i)["allowed"] for i, lim in enumerate(hits))
    assert not b.check("u1", now=T0 + 5)["allowed"]
    assert not a.check("u1", now=T0 + 6)["allowed"]


def test_in_process_limiters_do_not_share(monkeypatch):
    """The problem this fixes: with no store, each instance counts alone."""
    a = SharedRateLimiter("bt", 5, 60, store_factory=lambda: None)
    b = SharedRateLimiter("bt", 5, 60, store_factory=lambda: None)
    for i in range(5):
        assert a.check("u1", now=T0 + i)["allowed"]
    assert b.check("u1", now=T0 + 5)["allowed"]


def test_keys_are_independent():
    a, b = pair(limit=1)
    assert a.check("u1", now=T0)["allowed"]
    assert b.check("u2", now=T0)["allowed"]
    assert not a.check("u1", now=T0 + 1)["allowed"]


def test_remaining_counts_down():
    a, _ = pair(limit=3)
    assert [a.check("u1", now=T0 + i)["remaining"] for i in range(3)] == [2, 1, 0]


def test_no_double_burst_at_the_window_boundary():
    """A fixed window would allow 5 at :59 and 5 more at :00."""
    a, _ = pair(limit=5)
    end = T0 + 59.5
    for i in range(5):
        assert a.check("u1", now=end + i * 0.01)["allowed"]
    assert not a.check("u1", now=end + 1.0)["allowed"]


def test_retry_after_is_when_a_slot_frees():
    a, _ = pair(limit=5)
    end = T0 + 59.5
    for i in range(5):
        a.check("u1", now=end)
    denied = a.check("u1", now=end + 1.0)
    retry = denied["retry_after"]
    assert 0 < retry < 60
    assert not a.check("u1", now=end + 1.0 + retry - 1)["allowed"]
    assert a.check("u1", now=end + 1.0 + retry + 0.01)["allowed"]


def test_rejected_attempts_are_not_counted():
    """A client retrying in a loop must not push its own window forward."""
    a, _ = pair(limit=2)
    a.check("u1", now=T0)
    a.check("u1", now=T0)
    for i in range(50):
        assert not a.check("u1", now=T0 + 1 + i * 0.1)["allowed"]
    # 50 s into the next window the previous one weighs 1/6: its 2 real hits
    # leave room for one more. Had the 50 rejections counted, it would not.
    assert a.check("u1", now=T0 + 110)["allowed"]


def test_full_current_window_waits_into_the_next():
    a, _ = pair(limit=2)
    start = T0
    a.check("u1", now=start + 1)
    a.check("u1", now=start + 1)
    denied = a.check("u1", now=start + 2)
    assert not denied["allowed"]
    assert denied["retry_after"] >= 58


class Broken:
    def hit(self, current, previous, n=1):
        raise RuntimeError("firestore down")

    def undo(self, current, n=1):
        raise RuntimeError("firestore down")


def test_store_failure_falls_back_to_in_process():
    lim = SharedRateLimiter("bt", 2, 60, store_factory=lambda: Broken())
    assert lim.check("u1", now=T0)["allowed"]
    assert lim.check("u1", now=T0 + 1)["allowed"]
    assert not lim.check("u1", now=T0 + 2)["allowed"]


def test_store_factory_runs_once():
    calls = []

    def factory():
        calls.append(1)
        return MemoryCounterStore()

    lim = SharedRateLimiter("bt", 5, 60, store_factory=factory)
    for i in range(3):
        lim.check("u1", now=T0 + i)
    assert calls == [1]


@pytest.mark.parametrize("key", ["a/b", "uid/../x"])
def test_slashes_in_keys_cannot_become_document_paths(key):
    seen = []

    class Spy(MemoryCounterStore):
        def hit(self, current, previous, n=1):
            seen.append(current)
            return super().hit(current, previous)

    lim = SharedRateLimiter("bt", 5, 60, store_factory=lambda: Spy())
    lim.check(key, now=T0)
    assert "/" not in seen[0]


def test_shared_cost_is_all_or_nothing_across_instances():
    from ratelimit import MemoryCounterStore

    store = MemoryCounterStore()
    a = SharedRateLimiter("pf", 5, 60, store_factory=lambda: store)
    b = SharedRateLimiter("pf", 5, 60, store_factory=lambda: store)
    assert a.check("u1", now=T0, cost=3)["allowed"]
    denied = b.check("u1", now=T0 + 1, cost=3)
    assert not denied["allowed"] and denied["retry_after"] > 0
    # The refused 3 were handed back, so 2 singles still fit.
    assert b.check("u1", now=T0 + 2)["allowed"]
    assert a.check("u1", now=T0 + 3)["allowed"]
    assert not a.check("u1", now=T0 + 4)["allowed"]
