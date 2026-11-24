"""Basket backtests."""

import time
import uuid
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Header, HTTPException
from firebase_admin import firestore

from analytics import annual_returns, monthly_returns, rolling_sharpe
from api import core
from api.core import (
    backtest_limiter,
    enforce_quota,
    inject_user,
    record_run,
)
from api.simulation import fetch_aligned, portfolio_weights
from bootstrap import stable_seed
from costs import portfolio_cost_sensitivity
from engine import apply_positions, compute_returns
from metrics import compute_metrics
from portfolio import (
    combine,
    contribution_summary,
    diversification_ratio,
)
from risk import apply_stops, size_positions
from schemas import PortfolioRequest
from sharpe_test import sharpe_difference_test
from strategies import build_positions
from timing import step

router = APIRouter()


@router.post("/portfolio")
def run_portfolio(req: PortfolioRequest, authorization: Optional[str] = Header(None)):
    """Run one strategy across several tickers and combine the legs.

    Each leg is a complete backtest — its own signals, stops, sizing, and
    transaction costs — so the portfolio is an aggregation of honest single
    results rather than a separate model with its own assumptions.
    """
    # One request is N data fetches and N full backtests, so it costs a slot
    # per leg rather than a single one, taken all at once or not at all.
    user = inject_user(authorization, limit=(backtest_limiter, "portfolio legs", len(req.tickers)))
    uid = user["uid"]
    enforce_quota(user)

    allowed_size = core.max_portfolio_size(user["profile"])
    if len(req.tickers) > allowed_size:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Your plan allows portfolios of up to {allowed_size} holdings; "
                f"you selected {len(req.tickers)}. Upgrade to run larger baskets."
            ),
        )

    start_time = time.time()

    aligned, closes, data_source = fetch_aligned(req)

    # How much history the inner join actually cost, measured against the leg
    # with the longest record rather than against the requested start date.
    # Comparing to the request would flag every run whose start landed on a
    # weekend or a holiday, and a warning that fires constantly gets ignored.
    longest_ticker = max(closes, key=lambda t: len(closes[t]))
    dropped_bars = len(closes[longest_ticker]) - len(aligned)
    limiting_ticker = min(closes, key=lambda t: len(closes[t])) if dropped_bars else None

    # 3. Run each leg exactly as a single-ticker backtest would.
    leg_returns = {}
    leg_metrics = {}
    # Kept so the cost block can re-run the legs at other costs. The loop
    # below reuses one `positions` name per iteration, so without this the
    # only surviving position series is the last leg's.
    leg_positions = {}
    leg_asset_returns = {}
    for symbol in req.tickers:
        close = aligned[symbol]
        returns = compute_returns(close)

        positions = build_positions(close, req.strategy, req.strategy_params())
        positions = apply_stops(positions, returns, req.stop_loss, req.take_profit)
        positions = size_positions(
            positions,
            returns,
            sizing=req.sizing,
            target_vol=req.target_vol,
            vol_window=req.vol_window,
            max_leverage=req.max_leverage,
        )

        out = apply_positions(positions, returns, req.transaction_cost)
        leg_net = out["net_return"].fillna(0)
        leg_returns[symbol] = leg_net
        leg_positions[symbol] = out["position"]
        leg_asset_returns[symbol] = returns
        leg_metrics[symbol] = compute_metrics(
            leg_net,
            out["equity_curve"].fillna(1),
            out["drawdown"].fillna(0),
            out["position"],
        )

    legs_frame = pd.DataFrame(leg_returns)

    # 4. Weight and combine.
    weights = portfolio_weights(req, aligned)
    portfolio = combine(legs_frame, weights)

    net_return = portfolio["net_return"]
    equity = portfolio["equity_curve"]
    drawdown = portfolio["drawdown"]

    # 5. Portfolio metrics. compute_metrics counts trades from position changes;
    # a portfolio has no single position series, so it is handed the weighted
    # exposure — turnover of the book as a whole.
    exposure = portfolio["weights"].sum(axis=1)
    metrics = compute_metrics(net_return, equity, drawdown, exposure)

    contributions = contribution_summary(portfolio["contributions"])

    dates_out = [d.strftime("%Y-%m-%d") for d in legs_frame.index]

    # An equal-weight buy-and-hold of the same names — the honest benchmark for
    # a portfolio, rather than any single ticker.
    bench_daily = aligned.pct_change().fillna(0.0).mean(axis=1)
    bench_equity = (1 + bench_daily).cumprod()

    benchmark_test = sharpe_difference_test(
        net_return,
        bench_daily,
        seed=stable_seed(
            ",".join(req.tickers), req.start, req.end, req.strategy, "sharpe-test"
        ),
    )

    # Same question as a single-ticker run, on the book. Valid because the
    # book is affine in cost exactly as one leg is — nothing upstream of the
    # weighted sum reads the cost. costs.py carries the check.
    cost_block = portfolio_cost_sensitivity(
        leg_positions, leg_asset_returns, weights, req.transaction_cost
    )

    duration_ms = int((time.time() - start_time) * 1000)

    # It consumed the compute of N backtests, so it counts against quota
    # either way. With the switch on it is also kept as a run: `kind` and
    # `tickers` instead of `ticker`, so the admin top-tickers list (which
    # skips runs without one) is not handed "AAPL · MSFT" as a symbol, and
    # compare can tell it apart. Requested dates, as a single run stores.
    db = core.get_db()
    run_id = None
    if core.SAVE_PORTFOLIO_RUNS:
        run_id = str(uuid.uuid4())
        batch = db.batch()
        batch.set(db.collection("runs").document(run_id), {
            "runId": run_id,
            "uid": uid,
            "email": user["email"],
            "kind": "portfolio",
            "tickers": req.tickers,
            "start": req.start,
            "end": req.end,
            "strategy": req.strategy,
            "params": {
                **req.strategy_params(),
                **req.risk_params(),
                "transaction_cost": req.transaction_cost,
                "weighting": req.weighting,
                "weight_window": req.weight_window,
                "max_weight": req.max_weight,
            },
            "metrics": metrics,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "durationMs": duration_ms,
        })
        record_run(db, uid, user["profile"], batch=batch)
        with step("run_write"):
            batch.commit()
    else:
        record_run(db, uid, user["profile"])

    return {
        "runId": run_id,
        "tickers": req.tickers,
        "strategy": req.strategy,
        "weighting": req.weighting,
        "start": dates_out[0],
        "end": dates_out[-1],
        "aligned_bars": len(legs_frame),
        # The inner join can truncate the period; saying so beats leaving the
        # user to wonder why their 2015 start date became 2021. Zero means the
        # holdings shared their full history and there is nothing to report.
        "dropped_bars": int(dropped_bars),
        "limiting_ticker": limiting_ticker,
        "longest_ticker_bars": int(len(closes[longest_ticker])),
        "metrics": metrics,
        "diversification_ratio": diversification_ratio(legs_frame, weights, net_return),
        # Against an equal-weight hold of the same names, not any one ticker.
        "benchmark_test": benchmark_test,
        "cost_sensitivity": cost_block,
        "equity_curve": [
            {"date": d, "strategy": round(s, 6), "benchmark": round(b, 6)}
            for d, s, b in zip(dates_out, equity.tolist(), bench_equity.tolist())
        ],
        "drawdown": [
            {"date": d, "value": round(v, 6)} for d, v in zip(dates_out, drawdown.tolist())
        ],
        "legs": [
            {
                "ticker": symbol,
                "avg_weight": round(float(weights[symbol].mean()), 4),
                "contribution": round(contributions[symbol], 6),
                "metrics": leg_metrics[symbol],
            }
            for symbol in req.tickers
        ],
        "monthly_returns": monthly_returns(net_return),
        "annual_returns": annual_returns(net_return, bench_daily),
        "rolling_sharpe": rolling_sharpe(net_return, window=60),
        "data_source": data_source,
        "duration_ms": duration_ms,
    }

