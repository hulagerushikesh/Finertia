"""Seed the local Firebase emulators for the end-to-end suite.

Run by e2e/scripts/start-backend.sh before the API starts:

    cd backend && python scripts/seed_e2e.py

It does three things, all against the emulators only (it refuses otherwise):

1. Creates the fixture users in e2e/fixtures/users.json in the Auth emulator,
   with a users/{uid} profile like the one RegisterPage writes. The admin's
   role is set here because the security rules forbid a client from setting
   its own role — the same reason prod's admin was set in the console.
2. Writes synthetic prices (AAPL, MSFT and the example tickers) into the `prices` collection, one complete
   document per year from one batch, so data.py serves them as cache and no
   run ever reaches Yahoo. Deterministic (seeded), so results are stable.
3. Is idempotent: re-running against a live emulator reuses existing users.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firebase_admin import auth, firestore  # noqa: E402

from firebase_admin_init import _get_app, emulator_mode  # noqa: E402
from price_store import COLLECTION, doc_id, frame_to_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
USERS = json.loads((ROOT / "e2e/fixtures/users.json").read_text())
# AAPL and MSFT for the suite's own runs, plus every ticker the onboarding
# examples use (frontend/src/data/sampleStrategies.json), so running an
# example end to end never reaches Yahoo either.
_SAMPLES = json.loads((ROOT / "frontend/src/data/sampleStrategies.json").read_text())["samples"]
TICKERS = sorted(
    {"AAPL", "MSFT"}
    | {s["params"]["ticker"] for s in _SAMPLES if "ticker" in s["params"]}
    | {t for s in _SAMPLES for t in s["params"].get("tickers", [])}
)
FIRST_YEAR = 2015


def synthetic_prices(ticker: str) -> pd.DataFrame:
    """Daily OHLCV from 2015 to today: a drifting random walk with enough
    trend and noise that every strategy trades."""
    rng = np.random.default_rng(sum(map(ord, ticker)))
    idx = pd.bdate_range(f"{FIRST_YEAR}-01-01", date.today())
    rets = rng.normal(0.0005, 0.016, len(idx))
    close = 100 * np.exp(np.cumsum(rets))
    spread = np.abs(rng.normal(0, 0.006, len(idx)))
    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.003, len(idx))),
            "High": close * (1 + spread),
            "Low": close * (1 - spread),
            "Close": close,
            "Volume": np.full(len(idx), 1_000_000.0),
        },
        index=idx,
    )


def seed_users(db) -> None:
    for key, u in USERS.items():
        try:
            rec = auth.get_user_by_email(u["email"])
        except auth.UserNotFoundError:
            rec = auth.create_user(email=u["email"], password=u["password"], email_verified=True)
        db.collection("users").document(rec.uid).set(
            {
                "uid": rec.uid,
                "email": u["email"],
                "displayName": key,
                "role": u["role"],
                "plan": "free",
                "createdAt": firestore.SERVER_TIMESTAMP,
                "lastLoginAt": firestore.SERVER_TIMESTAMP,
                "totalRuns": 0,
                "isActive": True,
            }
        )
        print(f"user {key}: {u['email']} ({u['role']})")


def seed_prices(db) -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    col = db.collection(COLLECTION)
    for ticker in TICKERS:
        frame = synthetic_prices(ticker)
        batch = db.batch()
        for year, chunk in frame.groupby(frame.index.year):
            doc = frame_to_doc(
                ticker, int(year), chunk, batch="e2e", complete=True, fetched_at=fetched_at
            )
            batch.set(col.document(doc_id(ticker, int(year))), doc)
        batch.commit()
        print(f"prices {ticker}: {len(frame)} bars, {FIRST_YEAR}-{date.today().year}")


def main() -> None:
    if not emulator_mode():
        sys.exit("refusing to seed: FIREBASE_AUTH_EMULATOR_HOST and FIRESTORE_EMULATOR_HOST must both be set")
    _get_app()
    db = firestore.client()
    seed_users(db)
    seed_prices(db)


if __name__ == "__main__":
    main()
