"""Overlaying stored runs."""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from api import core
from api.core import (
    backtest_limiter,
    inject_user,
)
from data import DataUnavailableError
from engine import apply_positions, compute_returns
from risk import apply_stops, size_positions
from schemas import (
    COST_KEYS,
    RISK_KEYS,
    CompareRequest,
)
from strategies import build_positions
from timing import step

router = APIRouter()


@router.post("/compare")
def compare_runs(req: CompareRequest, authorization: Optional[str] = Header(None)):
    """Recompute several stored runs so their equity curves can be overlaid.

    Equity curves are deliberately not persisted — they are a few thousand floats
    per run and derivable from the config, so Firestore stores the config and we
    rebuild the curve here. That keeps documents small and means a fix to the
    engine retroactively corrects every historical chart.
    """
    # Each id costs a data fetch plus a full recompute, so this shares the
    # backtest budget rather than getting a free pass.
    user = inject_user(authorization, limit=(backtest_limiter, "comparisons", 1))
    uid = user["uid"]

    start_time = time.time()
    db = core.get_db()

    # Every run in one round trip rather than one each.
    with step("run_read"):
        fetched = {
            doc.id: doc
            for doc in db.get_all([db.collection("runs").document(r) for r in req.run_ids])
        }

    series = []
    for run_id in req.run_ids:
        doc = fetched.get(run_id)
        if doc is None or not doc.exists:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        d = doc.to_dict()
        if d.get("uid") != uid and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        # The overlay recomputes one ticker's curve; a basket would need the
        # whole portfolio path, so it is refused by name rather than failing
        # on the missing `ticker`.
        if d.get("kind") == "portfolio":
            raise HTTPException(
                status_code=400,
                detail="Compare works on single-ticker runs; a portfolio run cannot be overlaid yet.",
            )

        strategy = d.get("strategy", "momentum")
        stored = d.get("params", {}) or {}
        # The run document keeps signal parameters, risk overlays, and the cost
        # in one flat map. They have to be separated again here, or the overlays
        # would be handed to the signal builder and silently never applied —
        # which would draw a curve that does not match the run it came from.
        cost = stored.get("transaction_cost", 0.001)
        risk = {k: stored.get(k) for k in RISK_KEYS if k in stored}
        params = {
            k: v for k, v in stored.items()
            if k != "transaction_cost" and k not in RISK_KEYS and k not in COST_KEYS
        }

        try:
            close = core.fetch_ohlcv(d["ticker"], d["start"], d["end"])["Close"]
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not reload data for {d.get('ticker')}: {exc}",
            ) from exc
        except DataUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        returns = compute_returns(close)
        positions = build_positions(close, strategy, params)
        # Runs created before the risk overlays existed have no such keys; the
        # defaults reproduce the original always-in, unstopped behaviour.
        positions = apply_stops(
            positions, returns, risk.get("stop_loss"), risk.get("take_profit")
        )
        positions = size_positions(
            positions,
            returns,
            sizing=risk.get("sizing", "fixed"),
            target_vol=risk.get("target_vol", 0.15),
            vol_window=risk.get("vol_window", 20),
            max_leverage=risk.get("max_leverage", 2.0),
        )
        out = apply_positions(positions, returns, cost)
        equity = out["equity_curve"].fillna(1)

        series.append({
            "runId": run_id,
            "ticker": d.get("ticker"),
            "strategy": strategy,
            "start": d.get("start"),
            "end": d.get("end"),
            "params": params,
            "metrics": d.get("metrics", {}),
            "points": [
                {"date": dt.strftime("%Y-%m-%d"), "value": round(v, 6)}
                for dt, v in zip(close.index, equity.tolist())
            ],
        })

    # Runs can cover different tickers and different date ranges, so the only
    # honest shared axis is the date. Where a run has no bar for a date its key
    # is simply absent and the chart leaves a gap rather than inventing a value.
    all_dates = sorted({p["date"] for s in series for p in s["points"]})
    by_run = {s["runId"]: {p["date"]: p["value"] for p in s["points"]} for s in series}
    merged = []
    for date in all_dates:
        row = {"date": date}
        for s in series:
            value = by_run[s["runId"]].get(date)
            if value is not None:
                row[s["runId"]] = value
        merged.append(row)

    overlapping = sum(
        1 for row in merged if len(row) == len(series) + 1
    )

    return {
        "series": [{k: v for k, v in s.items() if k != "points"} for s in series],
        "chart": merged,
        # Two runs over disjoint periods produce a chart where the lines never
        # meet; the UI needs to be able to say so rather than imply comparison.
        "overlapping_days": overlapping,
        "duration_ms": int((time.time() - start_time) * 1000),
    }

