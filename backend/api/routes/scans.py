"""POST /scan: one strategy across a tracked index (scan.py, planning/DATA.md)."""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from api import core
from api.core import enforce_quota, in_parallel, inject_user, record_run, scan_limiter
from data import NotCachedError, cached_ohlcv
from scan import scan_one, summarise
from schemas import ScanRequest
from timing import step
import universes

router = APIRouter()

# The indexes a scan may cover. The S&P 500 waits until scans of a hundred
# are measured in production (planning/DATA.md, index scan).
SCANNABLE = ("nifty50", "niftynext50", "nasdaq100")

# Prices are read sixteen at a time (the shared I/O pool's size).
READ_CHUNK = 16


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

    def read(t):
        try:
            return cached_ohlcv(t, req.start, req.end)
        except NotCachedError as exc:
            return exc

    frames = []
    for i in range(0, len(tickers), READ_CHUNK):
        chunk = tickers[i : i + READ_CHUNK]
        frames.extend(in_parallel(*[lambda t=t: read(t) for t in chunk]))

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
