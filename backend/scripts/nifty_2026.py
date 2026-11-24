"""Study 3: do the Nifty survivors hold on 2026, which the study never saw?

    cd backend && .venv/bin/python scripts/nifty_2026.py           # the run
    cd backend && .venv/bin/python scripts/nifty_2026.py --check   # re-run, exit 1 if a count moved
    cd backend && .venv/bin/python scripts/nifty_2026.py --dry     # same code on 2025 (already seen), to test it

The rules are the ones fixed in planning/RESEARCH-PLAN.md ("Study 3") before
the first run. Every pair keeps the parameters its walk-forward chose in
nifty-funnel.json; nothing is re-tuned. Signals are built over the whole
history so the indicators have their warm-up, and only the holdout window is
scored, with both curves rebased at its first close, as nifty_study.py does
for its unseen years.

Output: planning/research/nifty-2026.json (--dry writes nothing).
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import offline_api  # noqa: E402,F401  (sets PRICE_CACHE=off before data is imported)
from nifty_perm import _shuffle_sharpe, run_shuffle_test  # noqa: E402
from nifty_study import COSTS, START, _sharpe  # noqa: E402

from data import fetch_ohlcv  # noqa: E402
from engine import compute_returns  # noqa: E402
from strategies import build_positions  # noqa: E402

DRY = "--dry" in sys.argv
# END is exclusive: the last close scored is 2026-11-23, the last before the plan.
HOLD_START, END = ("2025-01-01", "2026-01-01") if DRY else ("2026-01-01", "2026-11-24")
MAIN_PAIRS = [
    ("start_2011", "RCOM.NS", "momentum"),
    ("start_2011", "RCOM.NS", "macd"),
    ("start_2011", "RELINFRA.NS", "macd"),
    ("start_2011", "RPOWER.NS", "macd"),
    ("today", "ADANIENT.NS", "momentum"),
]
ZERO_VOLUME_FLAG = 20
CORR_SHUFFLES, SEED = 10_000, 42
FUNNEL = Path(__file__).resolve().parents[2] / "planning" / "research" / "nifty-funnel.json"
OUT = FUNNEL.with_name("nifty-2026.json")

_prices: dict = {}


def _ohlcv(symbol):
    if symbol not in _prices:
        _prices[symbol] = fetch_ohlcv(symbol, START, END)
    return _prices[symbol]


def score(symbol, strategy, params, cost):
    """Strategy and buy-and-hold Sharpe over the holdout, with the engine's arithmetic."""
    df = _ohlcv(symbol)
    close = df["Close"]
    returns = compute_returns(close)
    pos = build_positions(close, strategy, params)
    turnover = pos.diff().abs()
    turnover.iloc[0] = abs(pos.iloc[0])
    net = pos * returns.fillna(0.0) - turnover * cost
    equity = (1 + net.fillna(0)).cumprod()
    hold = close / close.iloc[0]

    window = equity.index >= pd.Timestamp(HOLD_START)
    eq, bh = equity[window], hold[window]
    p, r = pos[window], returns[window]
    real = _shuffle_sharpe(p.to_numpy(), r.fillna(0).to_numpy(), cost)
    return {
        "days": int(window.sum()),
        "sharpe": round(_sharpe(eq), 3),
        "hold_sharpe": round(_sharpe(bh), 3),
        "hold_return": round(float(bh.iloc[-1] / bh.iloc[0] - 1), 4),
        "strategy_return": round(float(eq.iloc[-1] / eq.iloc[0] - 1), 4),
        "days_in_market": int((p != 0).sum()),
        "zero_volume_days": int((df["Volume"][window] == 0).sum()),
        "run_shuffle_p": run_shuffle_test(p, r, cost, real)["p_value"],
    }


def main_pairs(funnel):
    rows = []
    for universe, symbol, strategy in MAIN_PAIRS:
        saved = next(
            r for r in funnel["universes"][universe]["default"]["rows"]
            if r["symbol"] == symbol and r["strategy"] == strategy
        )
        assert saved["survives"], f"{symbol} {strategy} is not a published survivor"
        row = {"universe": universe, "symbol": symbol, "strategy": strategy, "params": saved["best_params"]}
        for cname, cost in COSTS.items():
            s = score(symbol, strategy, saved["best_params"], cost)
            s["held"] = s["sharpe"] > s["hold_sharpe"]
            row[cname] = s
        row["not_tradeable_as_tested"] = row["default"]["zero_volume_days"] > ZERO_VOLUME_FLAG
        rows.append(row)
        print(f"{symbol} {strategy}: {row['default']}", flush=True)
    counted = [r for r in rows if r["universe"] == "start_2011"]
    held = sum(r["default"]["held"] for r in counted)
    return {
        "rows": rows,
        "start_2011_held": held,
        "start_2011_pairs": len(counted),
        "reading": "the survivors held" if held == len(counted) else "no sign that they held",
    }


def breadth(funnel):
    rows = []
    for r in funnel["universes"]["start_2011"]["default"]["rows"]:
        t0 = time.time()
        s = score(r["symbol"], r["strategy"], r["best_params"], COSTS["default"])
        rows.append({
            "symbol": r["symbol"],
            "strategy": r["strategy"],
            "unseen_lead": round(r["oos_sharpe"] - r["bh_oos_sharpe"], 3),
            "lead": round(s["sharpe"] - s["hold_sharpe"], 3),
        })
        print(f"{time.time() - t0:5.1f}s  breadth {r['symbol']} {r['strategy']}", flush=True)
    a = pd.Series([x["unseen_lead"] for x in rows]).rank().to_numpy()
    b = pd.Series([x["lead"] for x in rows]).rank().to_numpy()
    rho = float(np.corrcoef(a, b)[0, 1])
    rng = np.random.default_rng(SEED)
    null = np.array([np.corrcoef(a, rng.permutation(b))[0, 1] for _ in range(CORR_SHUFFLES)])
    p = float((null >= rho).sum() + 1) / (CORR_SHUFFLES + 1)
    return {
        "pairs": len(rows),
        "ahead_of_hold": sum(x["lead"] > 0 for x in rows),
        "spearman": round(rho, 3),
        "p_one_sided": round(p, 4),
        "reading": "the ranking carried over" if rho > 0 and p < 0.05 else "the ranking did not carry over",
        "rows": rows,
    }


def build():
    funnel = json.loads(FUNNEL.read_text())
    return {
        "holdout": [HOLD_START, END],
        "dry_run": DRY,
        "generated": time.strftime("%Y-%m-%d"),
        "main": main_pairs(funnel),
        "breadth": breadth(funnel),
    }


def counts(out):
    m, b = out["main"], out["breadth"]
    return {
        "held": m["start_2011_held"],
        "main": [(r["symbol"], r["strategy"], r["default"]["held"]) for r in m["rows"]],
        "ahead_of_hold": b["ahead_of_hold"],
        "spearman": b["spearman"],
    }


def main():
    fresh = build()
    summary = {k: v for k, v in fresh["breadth"].items() if k != "rows"}
    print("main:", fresh["main"]["start_2011_held"], "of", fresh["main"]["start_2011_pairs"], "-", fresh["main"]["reading"])
    print("breadth:", summary)
    if DRY:
        return
    if "--check" in sys.argv:
        saved = counts(json.loads(OUT.read_text()))
        now = counts(fresh)
        print("no count moved" if saved == now else f"{saved} -> {now}")
        sys.exit(0 if saved == now else 1)
    OUT.write_text(json.dumps(fresh, indent=1) + "\n")


if __name__ == "__main__":
    main()
