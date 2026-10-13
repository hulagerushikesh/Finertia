"""The free plan's monthly validation, taken atomically.

A free validation is worth hundreds of backtests in CPU, and the counter is
the only thing between a free account and unlimited ones. Reading the profile,
checking the count and writing it back in three steps would let a user fire
five validations at once and have all five pass the check. So the check and
the increment happen in one Firestore transaction: of N concurrent requests,
only the ones that fit in the allowance get a slot.

The slot is taken before the work starts and handed back if the work does not
produce a result (bad ticker, data outage, a crash), so a failure on our side
or a typo does not cost the user their one validation of the month.

Fields on users/{uid}, all server-owned:
  validationPeriod       'YYYY-MM' the counter belongs to
  validationsThisPeriod  free validations taken in that period
  totalValidations       free validations ever taken, for conversion reporting
"""

from __future__ import annotations

from datetime import datetime

from google.cloud import firestore

from plans import current_period, validations_used


def reserve(db, uid: str, allowance: int, now: datetime | None = None) -> dict | None:
    """Take one free validation for `uid`. Returns {period, used}, `used`
    counting this one, or None if this period's allowance is used up."""
    period = current_period(now)
    ref = db.collection("users").document(uid)

    @firestore.transactional
    def take(tx):
        snap = ref.get(transaction=tx)
        used = validations_used(snap.to_dict() if snap.exists else None, now)
        if used >= allowance:
            return None
        tx.set(
            ref,
            {
                "validationPeriod": period,
                # Written as a value, not an Increment: a stale period or a
                # negative counter is replaced, as `runs_used` reads it.
                "validationsThisPeriod": used + 1,
                "totalValidations": firestore.Increment(1),
            },
            merge=True,
        )
        return {"period": period, "used": used + 1}

    return take(db.transaction())


def release(db, uid: str, period: str) -> None:
    """Give back a slot taken by `reserve` whose validation produced nothing.

    Only within the same period: a slot taken on the 31st and failed after
    midnight belongs to a month that is already over.
    """
    ref = db.collection("users").document(uid)

    @firestore.transactional
    def give_back(tx):
        snap = ref.get(transaction=tx)
        profile = snap.to_dict() if snap.exists else {}
        if profile.get("validationPeriod") != period:
            return
        used = max(0, int(profile.get("validationsThisPeriod", 0) or 0))
        if used == 0:
            return
        tx.update(ref, {
            "validationsThisPeriod": used - 1,
            "totalValidations": firestore.Increment(-1),
        })

    give_back(db.transaction())
