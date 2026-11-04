"""Follow-up to the Nifty survival study: the timing test, re-run fairly.

    cd backend && .venv/bin/python scripts/nifty_perm.py           # run and save
    cd backend && .venv/bin/python scripts/nifty_perm.py --check   # re-run, exit 1 if a count moved

The write-up found two flaws in question 1's timing test. The rules for this
re-run were fixed in planning/RESEARCH-PLAN.md ("Follow-up, fixed before its
run") before it first ran:

  1. Test the walk-forward's pick (best_params from nifty-funnel.json), not
     the default parameters.
  2. Beside the product's day-by-day shuffle, shuffle whole runs of unchanged
     position, so the shuffles trade about as often as the real strategy and
     a higher cost does not lower the bar.

The product's permutation_test is called unchanged for the day shuffle.

Output: planning/research/nifty-perm.json.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import offline_api  # noqa: E402,F401  (sets PRICE_CACHE=off before data is imported)

from data import fetch_ohlcv  # noqa: E402
from engine import compute_returns  # noqa: E402
from nifty_study import COSTS, END, START  # noqa: E402
from strategies import build_positions  # noqa: E402
from validation import permutation_test  # noqa: E402

TRIALS, SEED = 500, 42
FUNNEL = Path(__file__).resolve().parents[2] / "planning" / "research" / "nifty-funnel.json"
OUT = FUNNEL.with_name("nifty-perm.json")


def _shuffle_sharpe(pos: np.ndarray, ret: np.ndarray, cost: float) -> float:
    # The same arithmetic as the product's shuffle loop, so the two tests
    # differ only in what gets shuffled.
    trades = np.abs(np.diff(pos, prepend=pos[0])) > 0
    net = pos * ret - trades * cost
    sd = net.std()
    total = np.prod(1 + net) - 1
    if sd == 0 or total <= -1:
        return 0.0
    return ((1 + total) ** (252 / len(net)) - 1) / (sd * np.sqrt(252))


def run_shuffle_test(position, returns, cost, real_sharpe):
    """p-value of the real Sharpe against shuffles of whole holding runs."""
    pos = position.to_numpy()
    ret = returns.fillna(0).to_numpy()
    cuts = np.flatnonzero(np.diff(pos)) + 1
    runs = np.split(pos, cuts)
    rng = np.random.default_rng(SEED)
    sharpes = np.empty(TRIALS)
    for i in range(TRIALS):
        order = rng.permutation(len(runs))
        sharpes[i] = _shuffle_sharpe(np.concatenate([runs[j] for j in order]), ret, cost)
    return {
        "runs": len(runs),
        "p_value": round(float((sharpes >= real_sharpe).sum() + 1) / (TRIALS + 1), 4),
    }


def build():
    funnel = json.loads(FUNNEL.read_text())
    prices = {}
    out = {"start": START, "end": END, "trials": TRIALS, "universes": {}}
    for uname, by_cost in funnel["universes"].items():
        out["universes"][uname] = {}
        for cname, block in by_cost.items():
            cost = COSTS[cname]
            rows = []
            for r in block["rows"]:
                if r["symbol"] not in prices:
                    close = fetch_ohlcv(r["symbol"], START, END)["Close"]
                    prices[r["symbol"]] = (close, compute_returns(close))
                close, returns = prices[r["symbol"]]
                pos = build_positions(close, r["strategy"], r["best_params"])
                day = permutation_test(pos, returns, cost, n_trials=TRIALS, seed=SEED)
                runs = run_shuffle_test(pos, returns, cost, day["real_sharpe"])
                other_checks = (
                    r["ahead_out_of_sample"]
                    and r["deflated_sharpe"] is not None and r["deflated_sharpe"] > 0.95
                    and r["pbo"] is not None and r["pbo"] < 0.5
                )
                rows.append({
                    "symbol": r["symbol"], "strategy": r["strategy"],
                    "p_defaults_day": r["permutation_p"],
                    "p_pick_day": day["p_value"],
                    "p_pick_runs": runs["p_value"],
                    "runs": runs["runs"],
                    "survives_before": r["survives"],
                    "survives_after": bool(other_checks and runs["p_value"] < 0.05),
                })
            out["universes"][uname][cname] = {
                "passing_timing_test": {
                    "defaults_day_shuffle": sum(x["p_defaults_day"] < 0.05 for x in rows),
                    "pick_day_shuffle": sum(x["p_pick_day"] < 0.05 for x in rows),
                    "pick_run_shuffle": sum(x["p_pick_runs"] < 0.05 for x in rows),
                },
                "survives_before": sum(x["survives_before"] for x in rows),
                "survives_after": sum(x["survives_after"] for x in rows),
                "survivors_after": [f"{x['symbol']} {x['strategy']}" for x in rows if x["survives_after"]],
                "rows": rows,
            }
            print(uname, cname, {k: v for k, v in out["universes"][uname][cname].items() if k != "rows"}, flush=True)
    return out


def main():
    fresh = build()
    if "--check" in sys.argv:
        saved = json.loads(OUT.read_text())
        # Survivors must match exactly. A pass count may move by one: Yahoo's
        # adjusted closes shift slightly between downloads, enough to carry a
        # pair whose p sits right at 0.05 across the line.
        moved = []
        for u in fresh["universes"]:
            for c in fresh["universes"][u]:
                s, f = saved["universes"][u][c], fresh["universes"][u][c]
                for k in ("survives_before", "survives_after", "survivors_after"):
                    if s[k] != f[k]:
                        moved.append(f"{u} {c} {k}: {s[k]} -> {f[k]}")
                for k, v in f["passing_timing_test"].items():
                    if abs(s["passing_timing_test"][k] - v) > 1:
                        moved.append(f"{u} {c} {k} passes: {s['passing_timing_test'][k]} -> {v}")
        print("\n".join(moved) or "no count moved")
        sys.exit(1 if moved else 0)
    OUT.write_text(json.dumps(fresh, indent=1) + "\n")


if __name__ == "__main__":
    main()
