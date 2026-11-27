"""Index scan: one strategy, every stock in an index, the core numbers each.

A backtest answers "did this work on this stock". A scan answers "on how many
of these stocks did it work, and is that more than luck would give". The
second half is the point: run anything across a hundred stocks and some will
beat holding by chance alone, so the summary sets the count of winners
beside the count chance would produce, and applies Benjamini–Hochberg so the
"survivors" number is corrected for having looked a hundred times.

Per stock this is the backtest's own pipeline (api/simulation.simulate: the
same signals, stops, sizing and costs), minus the slow parts — no bootstrap
intervals, no regime tables, no trade list. The comparison with holding is
the backtest's own Ledoit–Wolf test, read from its HAC (normal) p-value
rather than its bootstrap one, which is what keeps a hundred of them fast.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import HTTPException

from api.simulation import simulate
from metrics import compute_metrics
from sharpe_test import sharpe_difference_test

ALPHA = 0.05
# Fields kept per stock. The full metrics block is twelve numbers; a table of
# a hundred rows needs the five a reader sorts by.
KEEP = ("total_return", "annualized_return", "sharpe_ratio", "max_drawdown", "num_trades")


def scan_one(req, ticker: str, df: pd.DataFrame) -> dict:
    """One stock's row. Never raises: a stock that cannot be run is a row
    saying why, so one short listing does not sink the whole scan."""
    one = req.model_copy(update={"ticker": ticker})
    try:
        close, _, engine_out, benchmark, _ = simulate(one, df)
    except HTTPException as exc:
        return {"ticker": ticker, "status": "skipped", "reason": str(exc.detail)}
    except ValueError as exc:
        return {"ticker": ticker, "status": "skipped", "reason": str(exc)}

    net = engine_out["net_return"].fillna(0)
    m = compute_metrics(net, engine_out["equity_curve"].fillna(1), engine_out["drawdown"].fillna(0),
                        engine_out["position"])
    hold_daily = benchmark.pct_change().fillna(0)
    hold_total = float(benchmark.iloc[-1] / benchmark.iloc[0] - 1)
    test = sharpe_difference_test(net, hold_daily, resamples=1, seed=0)

    row = {"ticker": ticker, "status": "ok", "bars": int(len(close))}
    row.update({k: m[k] for k in KEEP})
    row["hold_total_return"] = round(hold_total, 6)
    row["excess_return"] = round(m["total_return"] - hold_total, 6)
    if test.get("computable"):
        row["hold_sharpe"] = test["benchmark_sharpe"]
        row["sharpe_vs_hold"] = test["difference"]
        row["p_value"] = test["p_value_normal"]
    else:
        row["hold_sharpe"] = row["sharpe_vs_hold"] = row["p_value"] = None
    return row


def benjamini_hochberg(p_values: list[float], alpha: float = ALPHA) -> list[bool]:
    """Which hypotheses survive at false-discovery rate `alpha`, in input order."""
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    if n == 0:
        return []
    order = np.argsort(p)
    thresholds = alpha * np.arange(1, n + 1) / n
    passed = p[order] <= thresholds
    keep = np.zeros(n, dtype=bool)
    if passed.any():
        last = int(np.nonzero(passed)[0].max())
        keep[order[: last + 1]] = True
    return keep.tolist()


def summarise(rows: list[dict]) -> dict:
    """The headline counts, with what chance alone would give beside them.

    "Beats holding" is a one-sided question (did the strategy do better), so a
    stock counts only when its Sharpe is above holding's and the two-sided
    p-value is under 2α — the one-sided test at α. Chance alone gives about
    α × N such stocks; Benjamini–Hochberg keeps the ones that survive the
    hundred looks.
    """
    ok = [r for r in rows if r["status"] == "ok"]
    tested = [r for r in ok if r["p_value"] is not None]
    one_sided = [
        (r["p_value"] / 2 if r["sharpe_vs_hold"] > 0 else 1 - r["p_value"] / 2) for r in tested
    ]
    survives = benjamini_hochberg(one_sided)
    for r, p1, keep in zip(tested, one_sided, survives):
        r["beats_holding"] = bool(p1 < ALPHA)
        r["survives_correction"] = bool(keep and r["sharpe_vs_hold"] > 0)

    n = len(tested)
    made_money = sum(r["total_return"] > 0 for r in ok)
    ahead = sum(r["excess_return"] > 0 for r in ok)
    return {
        "stocks": len(rows),
        "ran": len(ok),
        "skipped": len(rows) - len(ok),
        "made_money": made_money,
        "ahead_of_holding": ahead,
        "tested_against_holding": n,
        "beats_holding": sum(r.get("beats_holding", False) for r in tested),
        "expected_by_chance": round(ALPHA * n, 2),
        "survives_correction": sum(r.get("survives_correction", False) for r in tested),
        "alpha": ALPHA,
        "median_sharpe": round(float(np.median([r["sharpe_ratio"] for r in ok])), 4) if ok else None,
        "median_excess_return": round(float(np.median([r["excess_return"] for r in ok])), 6) if ok else None,
    }
