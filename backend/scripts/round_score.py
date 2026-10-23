"""Read the tester round's "Returned" and "one more thing" columns from
production Firestore. Read-only.

The phase-4 rule (DECISIONS 8 Oct) scores each tester on five columns. Two of
them live in the `runs` collection rather than in anyone's memory of a call:

- **Returned**: a saved run on a later calendar day than the tester's first,
  within 7 days of it. (Async testers count from their first run; for a live
  session on a different day, read the per-day list by hand.)
- **More than asked**, the third part of "Engaged": a second ticker or a
  second rule on the first day.

"Finished unaided", "Opened Validation" and "Would pay" come from the
conversations and stay in feedback.md. Nothing here writes, and no email is
printed: each tester is shown by the first 6 characters of their uid, which
Admin → Users can match to a person.

    cd backend && .venv/bin/python scripts/round_score.py --since 2026-10-07 \\
        --exclude you@example.com --exclude throwaway@example.com

Needs FIREBASE_SERVICE_ACCOUNT_JSON, as the API does (backend/.env is read if
present).
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RETURN_WINDOW_DAYS = 7


def _names(run):
    """The tickers a run covered: one for a single run, the basket for a portfolio."""
    if run.get("tickers"):
        return tuple(run["tickers"])
    return (run["ticker"],) if run.get("ticker") else ()


def score(runs, tz):
    """Per-uid columns from a list of run dicts (uid, createdAt, ticker or
    tickers, strategy). Calendar days are read in `tz`, the testers' own."""
    by_uid = defaultdict(list)
    for r in runs:
        if r.get("uid") and r.get("createdAt"):
            by_uid[r["uid"]].append(r)

    rows = []
    for uid, rs in by_uid.items():
        rs.sort(key=lambda r: r["createdAt"])
        days = sorted({r["createdAt"].astimezone(tz).date() for r in rs})
        first = days[0]
        first_day = [r for r in rs if r["createdAt"].astimezone(tz).date() == first]
        tickers = {t for r in first_day for t in _names(r)}
        baskets = {_names(r) for r in first_day}
        rules = {r.get("strategy") for r in first_day if r.get("strategy")}
        later = [d for d in days[1:] if d <= first + timedelta(days=RETURN_WINDOW_DAYS)]
        rows.append({
            "uid": uid,
            "first_day": first,
            "runs": len(rs),
            "runs_first_day": len(first_day),
            "more_than_asked": len(tickers) > 1 or len(baskets) > 1 or len(rules) > 1,
            "returned": bool(later),
            "days": days,
        })
    rows.sort(key=lambda row: (row["first_day"], row["uid"]))
    return rows


def _load_env():
    env = ROOT / ".env"
    if "FIREBASE_SERVICE_ACCOUNT_JSON" in os.environ or not env.exists():
        return
    from dotenv import load_dotenv

    load_dotenv(env)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", required=True, help="YYYY-MM-DD; testers whose first run is on or after this date")
    ap.add_argument("--exclude", action="append", default=[], help="an email to leave out (repeatable)")
    ap.add_argument("--tz", default="Asia/Kolkata", help="time zone for calendar days (default Asia/Kolkata)")
    args = ap.parse_args()
    tz = ZoneInfo(args.tz)
    since = datetime.strptime(args.since, "%Y-%m-%d").date()
    excluded = {e.strip().lower() for e in args.exclude}

    _load_env()
    from firebase_admin_init import get_db

    db = get_db()

    skip_uids = {
        d.to_dict().get("uid")
        for d in db.collection("users").select(["uid", "email"]).stream()
        if (d.to_dict().get("email") or "").lower() in excluded
    }
    runs = [
        d.to_dict()
        for d in db.collection("runs").select(["uid", "createdAt", "ticker", "tickers", "strategy"]).stream()
    ]
    rows = [r for r in score([r for r in runs if r.get("uid") not in skip_uids], tz) if r["first_day"] >= since]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Round score as of {now}, days in {args.tz} (excluding {len(skip_uids)} account(s))")
    print()
    print("| Tester | First run | Runs (first day / all) | More than asked | Returned | Days with a run |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        print(
            f"| `{row['uid'][:6]}` | {row['first_day']} | {row['runs_first_day']} / {row['runs']} "
            f"| {'yes' if row['more_than_asked'] else 'no'} | {'yes' if row['returned'] else 'no'} "
            f"| {', '.join(d.strftime('%d %b') for d in row['days'])} |"
        )
    print()
    print(f"Returned: {sum(r['returned'] for r in rows)} / {len(rows)}. "
          "Engaged also needs \"finished unaided\" and \"opened Validation\" from feedback.md.")


if __name__ == "__main__":
    main()
