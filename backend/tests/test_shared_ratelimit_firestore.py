"""The shared limiter against the real Firestore emulator.

Skipped unless FIRESTORE_EMULATOR_HOST is set. CI runs it inside
`firebase emulators:exec` in the E2E job. Two FirestoreCounterStores with two
separate clients are two Cloud Run instances.
"""

import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="needs the Firestore emulator"
)


def instance(limit):
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore

    from ratelimit import FirestoreCounterStore, SharedRateLimiter

    client = firestore.Client(project="demo-finertia", credentials=AnonymousCredentials())
    store = FirestoreCounterStore(lambda: client)
    return SharedRateLimiter("emu", limit, 60, store_factory=lambda: store)


def test_limit_holds_across_two_instances_on_firestore():
    a, b = instance(4), instance(4)
    key = uuid.uuid4().hex
    now = 2_000_040.0
    assert [lim.check(key, now=now)["allowed"] for lim in (a, b, a, b)] == [True] * 4
    assert not b.check(key, now=now)["allowed"]
    assert not a.check(key, now=now)["allowed"]


def test_a_rejection_is_undone_on_firestore():
    a, b = instance(2), instance(2)
    key = uuid.uuid4().hex
    now = 2_000_040.0  # the start of a window
    assert a.check(key, now=now)["allowed"]
    assert a.check(key, now=now)["allowed"]
    for _ in range(5):
        assert not b.check(key, now=now)["allowed"]
    # 50 s into the next window the previous one weighs 1/6: 2 real hits leave
    # room for one more; 7 (had the rejections counted) would not.
    assert a.check(key, now=now + 110)["allowed"]


def test_a_cost_is_taken_and_handed_back_whole_on_firestore():
    a, b = instance(5), instance(5)
    key = uuid.uuid4().hex
    now = 2_000_040.0
    assert a.check(key, now=now, cost=3)["allowed"]
    assert not b.check(key, now=now, cost=3)["allowed"]
    # The refused 3 were undone: exactly 2 singles still fit.
    assert b.check(key, now=now)["allowed"]
    assert a.check(key, now=now)["allowed"]
    assert not a.check(key, now=now)["allowed"]
