"""Question 2 of the Nifty survival study: how much does a big search fool you?

    cd backend && .venv/bin/python scripts/nifty_grid.py           # run and save
    cd backend && .venv/bin/python scripts/nifty_grid.py --check   # re-run, exit 1 if the pick or a check moved

The stock, the period and the 834-combination grid were fixed in
planning/RESEARCH-PLAN.md ("Question 2, fixed before its run") and committed
before this script first ran. The statistics are the product's own:
walk_forward runs once per strategy on that strategy's part of the grid,
giving PBO and the whole-grid tests; the overall pick is the best in-sample
Sharpe across all three, deflated with N = 834, and the permutation test is
run on its positions.

Output: planning/research/nifty-grid.json, with every combination's
in-sample and out-of-sample Sharpe for the chart.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import offline_api  # noqa: E402,F401  (sets PRICE_CACHE=off before data is imported)

from data import fetch_ohlcv  # noqa: E402
from deflated import deflated_sharpe_ratio  # noqa: E402
from engine import compute_returns  # noqa: E402
from nifty_study import START, END, _sharpe  # noqa: E402
from purge import purged_split  # noqa: E402
from strategies import build_positions  # noqa: E402
from validation import _segment_metrics, _segment_net_return, permutation_test, walk_forward  # noqa: E402

SYMBOL = "RELIANCE.NS"
COST = 0.001
SPLIT = 0.7
OUT = Path(__file__).resolve().parents[2] / "planning" / "research" / "nifty-grid.json"
SMALL_GRID = Path(__file__).resolve().parents[2] / "planning" / "research" / "nifty-funnel.json"

GRID = {
    "momentum": [
        {"momentum_lookback": lb, "ma_window": ma, "momentum_threshold": th}
        for lb in (5, 10, 15, 20, 30, 40, 60, 80, 100, 120, 150, 200)
        for ma in (10, 20, 30, 50, 75, 100, 150, 200, 250, 300)
        for th in (0.0, 0.01, 0.02, 0.05)
    ],
    "macd": [
        {"macd_fast": f, "macd_slow": s, "macd_signal": sig}
        for f in (3, 5, 8, 10, 12, 15, 19, 25)
        for s in (10, 15, 20, 26, 30, 39, 50, 60, 80, 100)
        if f < s
        for sig in (5, 9, 12, 15)
    ],
    "bollinger": [
        {"bb_window": w, "bb_std": sd}
        for w in (5, 10, 15, 20, 25, 30, 40, 50, 75, 100)
        for sd in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
    ],
}
assert [len(g) for g in GRID.values()] == [480, 284, 70]


def build():
    close = fetch_ohlcv(SYMBOL, START, END)["Close"]
    returns = compute_returns(close)
    n = len(close)
    b = purged_split(n, int(n * SPLIT))
    is_s, oos_s = slice(0, b["is_end"]), slice(b["oos_start"], n)

    per_strategy, points, trial_sharpes = {}, [], []
    for strategy, grid in GRID.items():
        wf = walk_forward(close, COST, strategy=strategy, split_ratio=SPLIT, grid=grid, seed=0)
        per_strategy[strategy] = {
            "combinations": wf["combinations_tested"],
            "best_params": wf["best_params"],
            "is_sharpe": round(wf["best_in_sample"]["sharpe_ratio"], 3),
            "oos_sharpe": round(wf["best_out_of_sample"]["sharpe_ratio"], 3),
            "deflated_sharpe": wf["deflated"].get("deflated_sharpe_ratio"),
            "pbo": wf["overfitting"].get("pbo"),
            "reality_check_p": wf["snooping"].get("reality_check", {}).get("p_value"),
            "spa_p": wf["snooping"].get("spa", {}).get("p_value"),
            "grid_cells_beating_bh": wf["snooping"].get("stepdown", {}).get("n_beating_benchmark"),
        }
        for row in wf["grid"]:
            pos = build_positions(close, strategy, row["params"])
            oos = _segment_metrics(pos.iloc[oos_s], returns.iloc[oos_s], COST)["sharpe_ratio"]
            points.append({"strategy": strategy, "params": row["params"],
                           "is_sharpe": round(row["sharpe_ratio"], 3), "oos_sharpe": round(oos, 3)})
            trial_sharpes.append(row["sharpe_ratio"])

    pick = max(points, key=lambda p: p["is_sharpe"])
    pos = build_positions(close, pick["strategy"], pick["params"])
    selected_is = _segment_net_return(pos.iloc[is_s], returns.iloc[is_s], COST).to_numpy()
    dsr = deflated_sharpe_ratio(trial_sharpes=trial_sharpes, selected_returns=selected_is)
    perm = permutation_test(pos, returns, COST, n_trials=500)

    small = next(
        r for r in json.loads(SMALL_GRID.read_text())["universes"]["start_2011"]["default"]["rows"]
        if r["symbol"] == SYMBOL and r["strategy"] == pick["strategy"]
    )
    oos_rank = sorted(points, key=lambda p: p["oos_sharpe"], reverse=True).index(pick) + 1
    return {
        "symbol": SYMBOL, "start": START, "end": END, "cost": COST,
        "in_sample_end": str(close.index[b["is_end"] - 1].date()),
        "out_of_sample_start": str(close.index[b["oos_start"]].date()),
        "bh_is_sharpe": round(_sharpe(close.iloc[is_s]), 3),
        "bh_oos_sharpe": round(_sharpe(close.iloc[oos_s]), 3),
        "combinations": len(points),
        "pick": {
            **pick,
            "oos_rank_of_834": oos_rank,
            "deflated_sharpe": dsr.get("deflated_sharpe_ratio"),
            "deflated_bar": dsr.get("expected_max_sharpe"),
            "permutation_p": perm["p_value"],
        },
        "median_oos_sharpe": round(float(pd.Series([p["oos_sharpe"] for p in points]).median()), 3),
        "small_grid_same_strategy": {k: small[k] for k in ("best_params", "is_sharpe", "oos_sharpe")},
        "per_strategy": per_strategy,
        "points": points,
    }


def _rounded(v):
    if isinstance(v, dict):
        return {k: _rounded(x) for k, x in v.items()}
    return round(v, 2) if isinstance(v, float) else v


def main():
    fresh = build()
    head = {k: v for k, v in fresh.items() if k != "points"}
    if "--check" in sys.argv:
        saved = json.loads(OUT.read_text())
        # Two decimals: Yahoo's adjusted closes shift in the last digits
        # between downloads, which moves the Deflated Sharpe in its fourth.
        moved = {k: (saved[k], fresh[k]) for k in ("pick", "per_strategy") if _rounded(saved[k]) != _rounded(fresh[k])}
        print(json.dumps(moved, indent=1) if moved else "nothing moved")
        sys.exit(1 if moved else 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fresh, indent=1) + "\n")
    print(json.dumps(head, indent=1))


if __name__ == "__main__":
    main()
