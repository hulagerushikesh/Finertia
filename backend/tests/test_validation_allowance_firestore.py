"""validation_allowance.py against the Firestore emulator: the free
validation is taken once however many requests race for it, and a failed
run gives it back.

Skipped unless FIRESTORE_EMULATOR_HOST is set; CI runs it inside
`firebase emulators:exec` in the E2E job.
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="needs the Firestore emulator"
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
PROJECT = f"demo-{uuid.uuid4().hex[:10]}"


def client():
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore

    return firestore.Client(project=PROJECT, credentials=AnonymousCredentials())


def new_user(db, **fields):
    uid = uuid.uuid4().hex
    db.collection("users").document(uid).set({"uid": uid, "plan": "free", **fields})
    return uid


def profile(db, uid):
    return db.collection("users").document(uid).get().to_dict()


def test_the_first_validation_of_the_month_is_taken_and_counted():
    from validation_allowance import reserve

    db = client()
    uid = new_user(db)
    assert reserve(db, uid, 1, NOW) == {"period": "2026-11", "used": 1}
    p = profile(db, uid)
    assert (p["validationPeriod"], p["validationsThisPeriod"], p["totalValidations"]) == ("2026-11", 1, 1)
    assert reserve(db, uid, 1, NOW) is None


def test_eight_racing_requests_get_one_slot():
    """Eight instances, each with its own client, all read "0 used" at once.
    The transaction must let exactly one through."""
    from validation_allowance import reserve

    uid = new_user(client())
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: reserve(client(), uid, 1, NOW), range(8)))
    assert sum(r is not None for r in results) == 1
    assert profile(client(), uid)["validationsThisPeriod"] == 1


def test_last_month_s_counter_does_not_count():
    from validation_allowance import reserve

    db = client()
    uid = new_user(db, validationPeriod="2026-10", validationsThisPeriod=1, totalValidations=1)
    assert reserve(db, uid, 1, NOW) == {"period": "2026-11", "used": 1}
    p = profile(db, uid)
    assert (p["validationsThisPeriod"], p["totalValidations"]) == (1, 2)


def test_a_failed_run_gives_the_slot_back():
    from validation_allowance import release, reserve

    db = client()
    uid = new_user(db)
    taken = reserve(db, uid, 1, NOW)
    release(db, uid, taken["period"])
    p = profile(db, uid)
    assert (p["validationsThisPeriod"], p["totalValidations"]) == (0, 0)
    assert reserve(db, uid, 1, NOW) is not None


def test_a_give_back_after_the_month_turned_is_ignored():
    from validation_allowance import release, reserve

    db = client()
    uid = new_user(db)
    reserve(db, uid, 1, NOW)
    release(db, uid, "2026-10")
    assert profile(db, uid)["validationsThisPeriod"] == 1


def test_another_user_s_counter_is_untouched():
    from validation_allowance import reserve

    db = client()
    a, b = new_user(db), new_user(db)
    reserve(db, a, 1, NOW)
    assert "validationsThisPeriod" not in profile(db, b)
