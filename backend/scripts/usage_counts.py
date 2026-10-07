"""Count sign-ups and runs in production Firestore. Read-only.

M10 phase 3 needs one usage number at the start and end of the outside-user
round; this is it. Nothing here writes. It prints counts only, never an email,
so the output can be pasted into planning/feedback.md as is.

    cd backend && .venv/bin/python scripts/usage_counts.py --since 2026-10-07 \\
        --exclude you@example.com --exclude throwaway@example.com

--exclude drops the author's own accounts (and smoke-test throwaways) from
every count, matched case-insensitively on the user document's email. Needs
FIREBASE_SERVICE_ACCOUNT_JSON, as the API does (backend/.env is read if present).
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_env():
    env = ROOT / ".env"
    if "FIREBASE_SERVICE_ACCOUNT_JSON" in os.environ or not env.exists():
        return
    from dotenv import load_dotenv

    load_dotenv(env)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", required=True, help="YYYY-MM-DD; also count what happened on or after this date")
    ap.add_argument("--exclude", action="append", default=[], help="an email to leave out (repeatable)")
    args = ap.parse_args()
    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    excluded = {e.strip().lower() for e in args.exclude}

    _load_env()
    from firebase_admin_init import get_db

    db = get_db()

    users = [d.to_dict() for d in db.collection("users").stream()]
    skip_uids = {u.get("uid") for u in users if (u.get("email") or "").lower() in excluded}
    users = [u for u in users if u.get("uid") not in skip_uids]
    new_users = [u for u in users if u.get("createdAt") and u["createdAt"] >= since]

    runs = [
        d.to_dict()
        for d in db.collection("runs").select(["uid", "createdAt"]).stream()
    ]
    runs = [r for r in runs if r.get("uid") not in skip_uids]
    recent = [r for r in runs if r.get("createdAt") and r["createdAt"] >= since]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Usage as of {now} (excluding {len(skip_uids)} account(s))")
    print()
    print("| | All time | Since " + args.since + " |")
    print("|---|---|---|")
    print(f"| Sign-ups | {len(users)} | {len(new_users)} |")
    print(f"| Saved backtest runs | {len(runs)} | {len(recent)} |")
    print(f"| Users with a saved run | {len({r['uid'] for r in runs})} | {len({r['uid'] for r in recent})} |")
    print(f"| Backtest + portfolio runs (`totalRuns` sum) | {sum(u.get('totalRuns') or 0 for u in users)} | — |")
    pro = [u for u in users if u.get("plan") == "pro"]
    comp = sum(1 for u in pro if u.get("planSource") == "admin")
    print(f"| Pro accounts (paid / comped by admin) | {len(pro) - comp} / {comp} | — |")


if __name__ == "__main__":
    main()
