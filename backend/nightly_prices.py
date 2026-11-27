"""The nightly price load: keep every tracked ticker fresh in L2.

    python -m nightly_prices                 # every universe, written to L2
    python -m nightly_prices --universe nifty50 --limit 5 --dry-run

Runs once a day after the US close (a Cloud Run job; see planning/DATA.md).
For each ticker in the tracked universe (universes/) it downloads the whole
history it keeps, checks it, and rewrites the ticker's L2 docs under one new
batch id — the same rule data.py follows, so a request never stitches two
downloads together. A ticker whose download fails or fails a check keeps
yesterday's copy; nothing half-checked is written.

Gentle on the provider by design: one ticker at a time, a pause between
them, a short backoff on errors, and nothing re-fetched on request for a
tracked ticker while NIGHTLY_PRICES=on (data.TRACKED_TTL). Overall that is
one download per tracked ticker per day, however many people use the site.

Each run ends with one summary: written, failed, the warnings worth a look.
It is printed as a JSON log line and, when L2 is Firestore, saved as
`price_loads/<date>` so the admin page and the release check can read it.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import data
import universes
from price_store import PriceStore

log = logging.getLogger("finertia.nightly")

# The first year kept. The workspace's longest preset is ten years and the
# studies start in 2011; 2005 leaves room for both without tripling the load.
SINCE = 2005
PACE_SECONDS = 1.0
RETRIES = 2
BACKOFF_SECONDS = 5.0

# Checks. A daily move this large on an adjusted close is far more often a
# missed split or a bad print than a real day; it is flagged, not dropped.
JUMP = 0.5
# A run of missing weekdays longer than this is more than a holiday.
GAP_WEEKDAYS = 7
# A last bar older than this many weekdays means the symbol stopped trading
# (delisted, renamed) or the provider stopped updating it.
STALE_WEEKDAYS = 5


@dataclass
class Checked:
    """The verdict on one download. `errors` block the write; `warnings` do not."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check(ticker: str, df: pd.DataFrame, *, today: pd.Timestamp) -> Checked:
    """Sanity checks on one ticker's download, before anything is written."""
    out = Checked()
    if df.empty:
        out.errors.append("no bars")
        return out
    close = df["Close"]
    if close.isna().any():
        out.errors.append(f"{int(close.isna().sum())} missing closes")
    if (close.dropna() <= 0).any():
        out.errors.append("a close at or below zero")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        out.errors.append("dates out of order or repeated")
    if out.errors:
        return out

    moves = close.pct_change().abs()
    jumps = moves[moves > JUMP]
    if len(jumps):
        days = ", ".join(d.strftime("%Y-%m-%d") for d in jumps.index[:3])
        out.warnings.append(f"{len(jumps)} daily moves over {JUMP:.0%} ({days})")

    gaps = np.busday_count(df.index[:-1].values.astype("datetime64[D]"), df.index[1:].values.astype("datetime64[D]"))
    long_gaps = int((gaps > GAP_WEEKDAYS).sum())
    if long_gaps:
        out.warnings.append(f"{long_gaps} gaps longer than {GAP_WEEKDAYS} weekdays")

    behind = int(np.busday_count(df.index[-1].date(), today.date()))
    if behind > STALE_WEEKDAYS:
        out.warnings.append(f"last bar {df.index[-1].date()}, {behind} weekdays ago")
    return out


def load_one(store: PriceStore, ticker: str, *, now, dry_run: bool = False, sleep=time.sleep) -> dict:
    """Download, check and (unless dry) write one ticker. Never raises."""
    span_lo = SINCE
    try:
        known = store.years_for(ticker)
    except Exception as exc:  # noqa: BLE001 — a store hiccup skips the ticker, not the run
        return {"ticker": ticker, "status": "failed", "reason": f"store read: {exc}"}
    # Keep every year already cached in the same batch (data.py's rule).
    lo = min([span_lo, *known])
    hi = now.year

    df, last_exc = None, None
    for attempt in range(RETRIES + 1):
        try:
            df = data._download(ticker, f"{lo}-01-01", f"{hi + 1}-01-01")
            break
        except Exception as exc:  # noqa: BLE001 — transport-shaped
            last_exc = exc
            if attempt < RETRIES:
                sleep(BACKOFF_SECONDS * (attempt + 1))
    if df is None:
        return {"ticker": ticker, "status": "failed", "reason": f"download: {last_exc}"}

    verdict = check(ticker, df, today=pd.Timestamp(now.date()))
    if verdict.errors:
        return {"ticker": ticker, "status": "failed", "reason": "; ".join(verdict.errors)}

    docs = data.docs_for(ticker, df, lo, hi, now=now)
    if not dry_run:
        try:
            store.put_many(docs)
        except Exception as exc:  # noqa: BLE001
            return {"ticker": ticker, "status": "failed", "reason": f"store write: {exc}"}
    out = {"ticker": ticker, "status": "written" if not dry_run else "checked", "bars": len(df), "years": len(docs)}
    if verdict.warnings:
        out["warnings"] = verdict.warnings
    return out


def run(tickers: list[str], store: PriceStore, *, now=None, dry_run: bool = False,
        pace: float = PACE_SECONDS, sleep=time.sleep) -> dict:
    """The whole load. Returns the summary; one ticker's failure never stops it."""
    now = now or data._now()
    started = time.monotonic()
    results = []
    for i, t in enumerate(tickers):
        if i:
            sleep(pace)
        results.append(load_one(store, t, now=now, dry_run=dry_run, sleep=sleep))

    failed = [r for r in results if r["status"] == "failed"]
    warned = [r for r in results if r.get("warnings")]
    return {
        "date": now.date().isoformat(),
        "started_at": now.isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "tickers": len(tickers),
        "written": sum(r["status"] in ("written", "checked") for r in results),
        "failed": len(failed),
        "warned": len(warned),
        "failures": [{"ticker": r["ticker"], "reason": r["reason"]} for r in failed],
        "warnings": [{"ticker": r["ticker"], "warnings": r["warnings"]} for r in warned],
        "duration_s": round(time.monotonic() - started, 1),
    }


def save_summary(summary: dict) -> None:
    """`price_loads/<date>`, when there is a Firestore to save it in."""
    from firebase_admin_init import get_db  # noqa: PLC0415 — only in production

    get_db().collection("price_loads").document(summary["date"]).set(summary)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--universe", action="append", choices=universes.NAMES,
                    help="limit to one universe (repeatable); default all")
    ap.add_argument("--limit", type=int, help="first N tickers only (a smoke run)")
    ap.add_argument("--dry-run", action="store_true", help="download and check, write nothing")
    ap.add_argument("--pace", type=float, default=PACE_SECONDS, help="seconds between tickers")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tickers = universes.tickers(*(args.universe or ()))
    if args.limit:
        tickers = tickers[: args.limit]

    store = data._get_store()
    summary = run(tickers, store, dry_run=args.dry_run, pace=args.pace)
    print(json.dumps({"message": "nightly_prices", **summary}))
    if not args.dry_run and type(store).__name__ == "FirestorePriceStore":
        save_summary(summary)
    # Exit non-zero only when most of the load failed — that is an outage,
    # and the job's own retry and alerting should see it. A few bad symbols
    # are routine and live in the summary.
    return 1 if summary["failed"] > summary["tickers"] / 2 else 0


if __name__ == "__main__":
    sys.exit(main())
