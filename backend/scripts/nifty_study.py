"""Question 1 of the Nifty survival study: how many strategies survive honest testing?

    cd backend && .venv/bin/python scripts/nifty_study.py           # both universes, all three costs
    cd backend && .venv/bin/python scripts/nifty_study.py --check   # re-run, exit 1 if any count moved

Every number goes through the real route handlers in-process (offline_api.py),
the way build_stock_pages.py does, so the study tests what the product runs.
The rules are the ones fixed in planning/RESEARCH-PLAN.md before the first run:

  beat in-sample   the walk-forward's chosen parameters have a higher Sharpe
                   than buy-and-hold over the in-sample years
  ahead out of     ... and still a higher Sharpe than buy-and-hold over the
    sample         years the search never saw
  survives         ... and permutation p < 0.05, Deflated Sharpe > 0.95 and
                   PBO < 0.5

Buy-and-hold's Sharpe for each window is computed from the benchmark leg of a
full-period backtest, sliced at the walk-forward's own boundary dates.

Output: planning/research/nifty-funnel.json, one row per stock x strategy x
cost, and the funnel counts.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nifty_universe import START_2011, TODAY  # noqa: E402
from offline_api import offline_client, post  # noqa: E402

from metrics import compute_metrics  # noqa: E402
from strategies import STRATEGY_NAMES  # noqa: E402

START, END = "2011-01-01", "2026-01-01"
COSTS = {"half": 0.0005, "default": 0.001, "double": 0.002}
OUT = Path(__file__).resolve().parents[2] / "planning" / "research" / "nifty-funnel.json"


def _sharpe(equity: pd.Series) -> float:
    # compute_metrics reads total return as equity[-1] - 1, so a slice taken
    # from the middle of a curve has to be rebased to start at 1.
    equity = equity / equity.iloc[0]
    net = equity.pct_change().fillna(0.0)
    drawdown = equity / equity.cummax() - 1
    return float(compute_metrics(net, equity, drawdown, pd.Series(np.ones(len(equity))))["sharpe_ratio"])


def _call(client, path, body):
    r = post(client, path, body)
    if r.status_code != 200:
        raise RuntimeError(f"{body['ticker']} {body['strategy']} {path}: {r.status_code} {r.text[:200]}")
    return r.json()


def run_one(client, symbol, strategy, cost):
    body = {"ticker": symbol, "start": START, "end": END, "strategy": strategy, "transaction_cost": cost}
    bt = _call(client, "/api/backtest", body)
    va = _call(client, "/api/validate", body)
    wf = va["walk_forward"]
    bench = pd.Series(
        [p["benchmark"] for p in bt["equity_curve"]],
        index=pd.to_datetime([p["date"] for p in bt["equity_curve"]]),
        dtype=float,
    )
    b = wf["boundary"]
    bh_is = _sharpe(bench[: b["in_sample_end_date"]])
    bh_oos = _sharpe(bench[b["out_of_sample_start_date"] :])
    is_sharpe = wf["best_in_sample"]["sharpe_ratio"]
    oos_sharpe = wf["best_out_of_sample"]["sharpe_ratio"]
    pbo = wf["overfitting"].get("pbo") if wf["overfitting"].get("computable") else None
    dsr = wf["deflated"].get("deflated_sharpe_ratio") if wf["deflated"].get("computable") else None
    perm_p = va["permutation"]["p_value"]

    beat_is = is_sharpe > bh_is
    ahead_oos = beat_is and oos_sharpe > bh_oos
    luck = perm_p < 0.05 and dsr is not None and dsr > 0.95 and pbo is not None and pbo < 0.5
    snoop = wf["snooping"]
    return {
        "symbol": symbol,
        "strategy": strategy,
        "first_date": bt["equity_curve"][0]["date"],
        "split": b["out_of_sample_start_date"],
        "best_params": wf["best_params"],
        "is_sharpe": round(is_sharpe, 3),
        "oos_sharpe": round(oos_sharpe, 3),
        "bh_is_sharpe": round(bh_is, 3),
        "bh_oos_sharpe": round(bh_oos, 3),
        "permutation_p": round(perm_p, 3),
        "deflated_sharpe": None if dsr is None else round(dsr, 3),
        "pbo": None if pbo is None else round(pbo, 2),
        "grid_cells_beating_bh": snoop["stepdown"]["n_beating_benchmark"] if snoop.get("computable") else None,
        "beat_in_sample": beat_is,
        "ahead_out_of_sample": ahead_oos,
        "survives": ahead_oos and luck,
    }


def funnel(rows):
    return {
        "tested": len(rows),
        "beat_in_sample": sum(r["beat_in_sample"] for r in rows),
        "ahead_out_of_sample": sum(r["ahead_out_of_sample"] for r in rows),
        "survives": sum(r["survives"] for r in rows),
        "any_grid_cell_beats_bh": sum(bool(r["grid_cells_beating_bh"]) for r in rows),
    }


def build():
    client = offline_client()
    universes = {
        "start_2011": [s for s, _, _ in START_2011 if s],
        "today": TODAY,
    }
    out = {
        "start": START,
        "end": END,
        "generated": time.strftime("%Y-%m-%d"),
        "missing_from_yahoo": [{"name": n, "note": note} for s, n, note in START_2011 if not s],
        "universes": {},
    }
    for uname, symbols in universes.items():
        out["universes"][uname] = {}
        for cname, cost in COSTS.items():
            rows = []
            for symbol in symbols:
                t0 = time.time()
                for strategy in STRATEGY_NAMES:
                    rows.append(run_one(client, symbol, strategy, cost))
                print(f"{time.time() - t0:5.1f}s  {uname} {cname} {symbol}", flush=True)
            out["universes"][uname][cname] = {"funnel": funnel(rows), "rows": rows}
    return out


def main():
    fresh = build()
    if "--check" in sys.argv:
        saved = json.loads(OUT.read_text())
        moved = [
            f"{u} {c}: {saved['universes'][u][c]['funnel']} -> {fresh['universes'][u][c]['funnel']}"
            for u in fresh["universes"]
            for c in fresh["universes"][u]
            if saved["universes"][u][c]["funnel"] != fresh["universes"][u][c]["funnel"]
        ]
        print("\n".join(moved) or "no count moved")
        sys.exit(1 if moved else 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fresh, indent=1) + "\n")
    for u, by_cost in fresh["universes"].items():
        for c, v in by_cost.items():
            print(u, c, v["funnel"])


if __name__ == "__main__":
    main()
