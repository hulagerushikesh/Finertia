"""Single-ticker backtests."""

import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from firebase_admin import firestore

import result_cache
from analytics import annual_returns, monthly_returns, rolling_sharpe
from api import core
from api.core import (
    backtest_limiter,
    enforce_quota,
    inject_user,
    record_run,
)
from api.simulation import load_prices, simulate
from bootstrap import bootstrap_metrics, stable_seed
from costs import cost_sensitivity
from metrics import compute_metrics
from regimes import regime_breakdown
from schemas import BacktestRequest
from sharpe_test import sharpe_difference_test
from timing import step

router = APIRouter()


def _render(content) -> bytes:
    """JSON exactly as FastAPI's default response would render it."""
    return json.dumps(
        jsonable_encoder(content), ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":")
    ).encode("utf-8")


def _compute(req: BacktestRequest, df) -> tuple[dict, dict]:
    """(metrics, the response body's deterministic part) for one backtest.

    Everything here depends only on the request and the prices, which is what
    lets result_cache hold it. The per-request fields (runId, data_source,
    duration_ms) are added by the route.
    """
    close, returns, engine_out, benchmark, _ = simulate(req, df)

    net_return = engine_out["net_return"].fillna(0)
    equity_curve = engine_out["equity_curve"].fillna(1)
    drawdown = engine_out["drawdown"].fillna(0)
    position = engine_out["position"]

    # 5. Metrics
    metrics = compute_metrics(net_return, equity_curve, drawdown, position)

    # 5b. Uncertainty around those metrics.
    #
    # Deliberately on every plan, like validation. A grid sweep plus hundreds
    # of permutations genuinely costs hundreds of backtests; this is one
    # resample of a series already in memory. Leaving it out would show the
    # reader most likely to read a Sharpe of 1.2 as a fact about the strategy
    # a naked point estimate, which is the exact failure the module exists to
    # prevent.
    #
    # The seed is derived from the run's own inputs so the interval is stable:
    # re-running the same backtest returns the same band rather than a slightly
    # different one each time, which would teach the user the number is arbitrary.
    confidence_intervals = bootstrap_metrics(
        net_return,
        seed=stable_seed(
            req.ticker.upper(),
            req.start,
            req.end,
            req.strategy,
            sorted(req.strategy_params().items()),
            sorted(req.risk_params().items()),
            req.transaction_cost,
        ),
    )

    # 6. Build response arrays
    dates = [d.strftime("%Y-%m-%d") for d in close.index]
    benchmark_vals = benchmark.fillna(1).tolist()
    equity_vals = equity_curve.tolist()
    drawdown_vals = drawdown.tolist()
    position_vals = position.tolist()
    net_return_vals = net_return.tolist()

    equity_curve_data = [
        {"date": d, "strategy": round(s, 6), "benchmark": round(b, 6)}
        for d, s, b in zip(dates, equity_vals, benchmark_vals)
    ]

    drawdown_data = [
        {"date": d, "value": round(v, 6)}
        for d, v in zip(dates, drawdown_vals)
    ]

    # Trade entry rows only (position changed), capped at 500 most recent
    trade_rows = []
    for i, (d, pos, ret, eq) in enumerate(zip(dates, position_vals, net_return_vals, equity_vals)):
        if i == 0:
            continue
        if position_vals[i] != position_vals[i - 1]:
            trade_rows.append({
                "date": d,
                "position": int(pos),
                "daily_return": round(ret, 6),
                "equity": round(eq, 6),
            })
    trades = trade_rows[-500:]

    # Time-sliced views — small payloads next to the equity curve.
    benchmark_daily = close.pct_change().fillna(0)
    monthly = monthly_returns(net_return)
    annual = annual_returns(net_return, benchmark_daily)
    rolling = rolling_sharpe(net_return, window=60)
    # Where the return was earned, in the market's own terms: the strategy's
    # Sharpe on the calm, middling and turbulent thirds of the period.
    regimes = regime_breakdown(net_return, position, benchmark_daily)
    # The page prints the strategy's Sharpe beside buy-and-hold's. This is the
    # p-value that belongs between them — Ledoit-Wolf on the paired series, so
    # the shared bars work for the reader instead of against them. Same
    # reasoning as the confidence intervals above for not gating it: 50-90ms on
    # a series already in memory, and the reader most likely to read "1.2 vs
    # 0.6" as a settled fact is the one who most needs it.
    benchmark_test = sharpe_difference_test(
        net_return,
        benchmark_daily,
        seed=stable_seed(
            req.ticker.upper(), req.start, req.end, req.strategy, "sharpe-test"
        ),
    )

    # How far the cost assumption can be wrong before the edge is gone.
    #
    # This is the level question, and the level is the only part of the cost
    # model that moves the number on the page — see costs.py for the
    # measurement that ruled out shipping a vol-scaled model instead. Five
    # engine runs plus a bisection, ~5ms, so it is not gated either.
    cost_block = cost_sensitivity(position, returns, req.transaction_cost)

    signals_summary = {
        "long_days": int((position > 0).sum()),
        "short_days": int((position < 0).sum()),
        "flat_days": int((position == 0).sum()),
    }

    return metrics, {
        "metrics": metrics,
        "equity_curve": equity_curve_data,
        "drawdown": drawdown_data,
        "trades": trades,
        "monthly_returns": monthly,
        "annual_returns": annual,
        "rolling_sharpe": rolling,
        "regimes": regimes,
        "benchmark_test": benchmark_test,
        "cost_sensitivity": cost_block,
        "signals_summary": signals_summary,
        "confidence_intervals": confidence_intervals,
    }


@router.post("/backtest")
def run_backtest(req: BacktestRequest, authorization: Optional[str] = Header(None)):
    """Run a backtest for the selected strategy and persist results to Firestore."""
    user = inject_user(authorization, limit=(backtest_limiter, "backtests", 1))
    uid = user["uid"]
    email = user["email"]
    enforce_quota(user)

    start_time = time.time()

    df = load_prices(req)
    # "yfinance" | "cache" | "cache-stale" | "memory". Stale means Yahoo was
    # down and this is the last good copy — the UI says so. Per request, so
    # never part of the cached body.
    data_source = df.attrs.get("data_source", "yfinance")

    key = result_cache.request_key(req.model_dump(mode="json"), df["Close"])
    with step("result_cache"):
        cached = result_cache.backtests.get(key)
    if cached is None:
        metrics, body = _compute(req, df)
        rendered = _render(body)
        result_cache.backtests.put(key, rendered, {"metrics": metrics})
    else:
        rendered, extra = cached
        metrics = extra["metrics"]

    duration_ms = int((time.time() - start_time) * 1000)

    # 7. Persist to Firestore — every run, cached or not: it is the user's run
    # and it counts against the month.
    run_id = str(uuid.uuid4())
    db = core.get_db()
    run_doc = {
        "runId": run_id,
        "uid": uid,
        "email": email,
        "ticker": req.ticker.upper(),
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "params": {
            **req.strategy_params(),
            **req.risk_params(),
            "transaction_cost": req.transaction_cost,
        },
        "metrics": metrics,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "durationMs": duration_ms,
    }
    batch = db.batch()
    batch.set(db.collection("runs").document(run_id), run_doc)
    record_run(db, uid, user["profile"], batch=batch)
    with step("run_write"):
        batch.commit()

    # The cached body is a JSON object; the per-request fields go around it.
    head = _render({"runId": run_id})[:-1]
    tail = _render({"data_source": data_source, "duration_ms": duration_ms})[1:]
    return Response(content=head + b"," + rendered[1:-1] + b"," + tail, media_type="application/json")
