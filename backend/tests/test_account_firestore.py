"""account.py against the Firestore emulator: export finds exactly the
user's documents, deletion leaves none behind and touches nobody else's.

Skipped unless FIRESTORE_EMULATOR_HOST is set; CI runs it inside
`firebase emulators:exec` in the E2E job.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="needs the Firestore emulator"
)

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore

    return firestore.Client(project=f"demo-{uuid.uuid4().hex[:10]}", credentials=AnonymousCredentials())


def seed(db, uid, runs=2):
    db.collection("users").document(uid).set({"uid": uid, "email": f"{uid}@x.com", "plan": "free"})
    for i in range(runs):
        db.collection("runs").document(f"{uid}-run-{i}").set(
            {"uid": uid, "ticker": "AAPL", "createdAt": NOW - timedelta(days=i)}
        )
    for name in ("backtest", "validate"):
        for window in (100, 101):
            db.collection("ratelimits").document(f"{name}:{uid}:{window}").set({"n": 1})


def ids(db, collection):
    return sorted(s.id for s in db.collection(collection).stream())


def test_export_holds_the_profile_and_only_the_users_runs(db):
    from account import export_account

    seed(db, "alice", runs=3)
    seed(db, "bob", runs=2)
    out = export_account(db, "alice", "alice@x.com", now=NOW)

    assert out["account"] == {"uid": "alice", "email": "alice@x.com"}
    assert out["profile"]["email"] == "alice@x.com"
    assert [r["id"] for r in out["runs"]] == ["alice-run-0", "alice-run-1", "alice-run-2"]  # newest first
    assert out["exported_at"] == "2026-10-14T12:00:00+00:00"


def test_export_of_an_account_with_no_profile_yet(db):
    from account import export_account

    out = export_account(db, "new", "new@x.com", now=NOW)
    assert out["profile"] is None and out["runs"] == []


def test_delete_leaves_nothing_of_the_user_and_everything_of_others(db):
    from account import delete_account

    seed(db, "alice", runs=3)
    seed(db, "bob", runs=2)
    # A uid that alice's is a prefix of: the counter range must stop at the colon.
    seed(db, "alice2", runs=1)
    gone = []

    counts = delete_account(db, "alice", gone.append)

    assert counts == {"runs": 3, "rate_limit_counters": 4}
    assert gone == ["alice"]
    assert ids(db, "users") == ["alice2", "bob"]
    assert ids(db, "runs") == ["alice2-run-0", "bob-run-0", "bob-run-1"]
    assert all(not i.split(":")[1] == "alice" for i in ids(db, "ratelimits"))
    assert len(ids(db, "ratelimits")) == 8


def test_delete_pages_through_more_runs_than_one_batch(db):
    from account import _BATCH, delete_account

    seed(db, "heavy", runs=_BATCH + 25)
    counts = delete_account(db, "heavy", lambda uid: None)
    assert counts["runs"] == _BATCH + 25
    assert ids(db, "runs") == []


def test_a_failed_deletion_can_be_finished_by_running_it_again(db):
    """The Auth account goes last, so a failure there leaves a user who can
    still sign in and retry, and the retry completes."""
    from account import delete_account

    seed(db, "carol", runs=2)

    def auth_down(uid):
        raise RuntimeError("auth unavailable")

    with pytest.raises(RuntimeError):
        delete_account(db, "carol", auth_down)
    # The data was already gone when Auth failed: the account is last.
    assert ids(db, "users") == [] and ids(db, "runs") == []
    gone = []
    assert delete_account(db, "carol", gone.append) == {"runs": 0, "rate_limit_counters": 0}
    assert gone == ["carol"]
    assert ids(db, "users") == [] and ids(db, "runs") == []
