"""POST /scan: one strategy across a tracked index (scan.py, planning/DATA.md)."""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from api import core
from api.core import enforce_quota, inject_user, record_run, scan_limiter
from data import PARTIAL_YEAR_TTL, NotCachedError, _MemoryCache, cached_ohlcv_many
from scan import scan_one, summarise
from schemas import ScanRequest
from timing import step
import universes

router = APIRouter()

# The indexes a scan may cover — every tracked list.
SCANNABLE = ("nifty50", "niftynext50", "nasdaq100", "sp500")

# Closes only, keyed (ticker, start, end): ten years of one stock is ~20 kB,
# so three S&P 500 scans' worth fits in ~30 MB. Separate from data.py's L1 so
# a scan never evicts the frames backtests are using. Six hours, like L1: the
# nightly load is the only thing that changes these prices.
_closes = _MemoryCache(max_entries=1600, ttl_seconds=PARTIAL_YEAR_TTL.total_seconds())


@router.post("/scan")
def run_scan(req: ScanRequest, authorization: Optional[str] = Header(None)):
    """The strategy on every stock in the index, with luck-corrected counts.

    Counts as one run against the monthly allowance, like one backtest. Not
    saved to history. Prices come from the nightly store only — a scan never
    calls Yahoo; a stock missing from the store is listed as skipped.
    """
    user = inject_user(authorization, limit=(scan_limiter, "scans", 1))
    enforce_quota(user)
    started = time.time()

    universe = universes.load(req.universe)
    tickers = universe["tickers"]

    # Closes already in this instance's scan cache; the rest in one batched
    # read from the store.
    frames, missing = {}, []
    for t in tickers:
        hit = _closes.get((t, req.start, req.end))
        if hit is not None:
            frames[t] = hit
        else:
            missing.append(t)
    if missing:
        for t, df in cached_ohlcv_many(missing, req.start, req.end).items():
            if isinstance(df, NotCachedError):
                frames[t] = df
                continue
            closes = df[["Close"]].copy()
            closes.attrs = dict(df.attrs)
            _closes.put((t, req.start, req.end), closes)
            frames[t] = closes
    frames = [frames[t] for t in tickers]

    rows = []
    with step("scan_compute"):
        for t, df in zip(tickers, frames):
            if isinstance(df, NotCachedError):
                rows.append({"ticker": t, "status": "skipped", "reason": str(df)})
            else:
                rows.append(scan_one(req, t, df))
    summary = summarise(rows)
    if summary["ran"] == 0:
        raise HTTPException(status_code=503, detail="No stored prices for this index and range yet.")

    db = core.get_db()
    batch = db.batch()
    record_run(db, user["uid"], user["profile"], batch=batch)
    batch.commit()

    return {
        "universe": req.universe,
        "universe_title": universe["title"],
        "universe_as_of": universe["as_of"],
        "strategy": req.strategy,
        "start": req.start,
        "end": req.end,
        "summary": summary,
        "rows": rows,
        "duration_ms": int((time.time() - started) * 1000),
    }
