"""A user's own data: export it, or delete the account and everything in it.

The DPDP Act 2023 gives a user the right to their data and to erasure; this
module is the server side of both (M12 sprint 1, item 5).

What belongs to a user, and where:
- `users/{uid}`: the profile (email, display name, plan, counters);
- `runs` with `uid == uid`: every saved backtest;
- `ratelimits` documents named `{limiter}:{uid}:{window}`: short-lived
  counters, keyed by uid, with nothing in them but a number;
- the Firebase Auth account itself (email, password hash).

Deletion runs in that order, account last, and every step is idempotent. If a
step fails part way, the user can still sign in and press the button again,
and the retry finishes the job. Deleting the account first would strand the
rest: data nobody could ask us to remove any more.

An ID token issued before the deletion still verifies until it expires
(an hour at most). It reaches nothing: the data is gone, and the client signs
out on success. Revocation checks on every request would cost an extra Auth
call each time, for an hour-long window that holds no data.

What is not deleted here, and why: Cloud Run request logs and Sentry events
carry the uid (never the email) and age out on their own retention (Cloud
Logging's default bucket keeps 30 days; Sentry keeps events for as long as
its plan does, 30 days on the free one). A deleted uid is never reused. The legal brief (item 4) lists
both.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.field_path import FieldPath

# Kept in step with the SharedRateLimiter names in main.py.
LIMITER_NAMES = ("backtest", "validate")

# Firestore allows 500 writes per batch; stay under it.
_BATCH = 400


def _runs(db, uid):
    return db.collection("runs").where(filter=FieldFilter("uid", "==", uid))


def export_account(db, uid: str, email: str, now: datetime | None = None) -> dict:
    """Everything stored about the user, as one JSON-ready dict."""
    now = now or datetime.now(timezone.utc)
    profile = db.collection("users").document(uid).get()
    runs = [{"id": snap.id, **(snap.to_dict() or {})} for snap in _runs(db, uid).stream()]
    runs.sort(key=lambda r: str(r.get("createdAt") or ""), reverse=True)
    return {
        "exported_at": now.isoformat(timespec="seconds"),
        "account": {"uid": uid, "email": email},
        "profile": profile.to_dict() if profile.exists else None,
        "runs": runs,
        "notes": (
            "Prices are not included: they are market data, not yours, and are "
            "re-fetched when a run is re-opened. Rate-limit counters are not "
            "included: they hold only a number and expire within minutes."
        ),
    }


def _delete_query(db, query) -> int:
    """Delete every document a query returns, a batch at a time."""
    deleted = 0
    while True:
        snaps = list(query.limit(_BATCH).stream())
        if not snaps:
            return deleted
        batch = db.batch()
        for snap in snaps:
            batch.delete(snap.reference)
        batch.commit()
        deleted += len(snaps)


def _counters(db, name: str, uid: str):
    """The limiter's documents for this uid: ids `{name}:{uid}:{window}`."""
    coll = db.collection("ratelimits")
    prefix = f"{name}:{uid.replace('/', '_')}:"
    return coll.where(filter=FieldFilter(FieldPath.document_id(), ">=", coll.document(prefix))).where(
        filter=FieldFilter(FieldPath.document_id(), "<", coll.document(prefix + ""))
    )


def delete_account(db, uid: str, delete_auth_user: Callable[[str], None]) -> dict:
    """Remove the user's data, then the account. Safe to run again."""
    runs = _delete_query(db, _runs(db, uid))
    counters = sum(_delete_query(db, _counters(db, name, uid)) for name in LIMITER_NAMES)
    db.collection("users").document(uid).delete()
    delete_auth_user(uid)
    return {"runs": runs, "rate_limit_counters": counters}
