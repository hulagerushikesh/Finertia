"""Run the three strategies on a list of well-known stocks for the /stocks pages.

Every figure on finertia.hulage.in/stocks/<slug> comes from this script's
output, frontend/src/lib/stockResults.json. Like reproduce_writeup.py it goes
through the real route handlers in-process (offline_api.py) on a fresh
yfinance download, so the pages quote exactly what the workspace would show
for the same request.

    cd backend && .venv/bin/python scripts/build_stock_pages.py           # re-run, rewrite the JSON
    cd backend && .venv/bin/python scripts/build_stock_pages.py --check   # re-run, compare, exit 1 on drift
    cd backend && .venv/bin/python scripts/build_stock_pages.py --index   # rewrite stockIndex.json only, no re-run

Per stock: buy-and-hold over the period, and for each strategy a backtest at
the workspace defaults plus a validation run (walk-forward, PBO, permutation
test, rolling walk-forward). About six calls a stock, a second or two each.

A page per stock only earns its place if the numbers on it are its own. Add a
stock by adding a row to STOCKS and re-running; the frontend tests check every
row has a page.
"""

import json
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from offline_api import offline_client, post  # noqa: E402

from metrics import compute_metrics  # noqa: E402
from strategies import STRATEGY_NAMES  # noqa: E402

START, END = "2019-01-01", "2025-01-01"
LIB = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib"
OUT = LIB / "stockResults.json"
# The few fields page titles and descriptions need. src/lib/pageMeta.js sits in
# the landing page's bundle, so it imports this and not the full results.
INDEX = LIB / "stockIndex.json"

# (slug, symbol, name, market). The slug is the URL; keep it stable once published.
STOCKS = [
    ("aapl", "AAPL", "Apple", "US"),
    ("msft", "MSFT", "Microsoft", "US"),
    ("nvda", "NVDA", "Nvidia", "US"),
    ("amzn", "AMZN", "Amazon", "US"),
    ("googl", "GOOGL", "Alphabet", "US"),
    ("meta", "META", "Meta Platforms", "US"),
    ("tsla", "TSLA", "Tesla", "US"),
    ("jpm", "JPM", "JPMorgan Chase", "US"),
    ("spy", "SPY", "S&P 500 ETF (SPY)", "US"),
    ("qqq", "QQQ", "Nasdaq-100 ETF (QQQ)", "US"),
    ("amd", "AMD", "AMD", "US"),
    ("nflx", "NFLX", "Netflix", "US"),
    ("brk-b", "BRK-B", "Berkshire Hathaway", "US"),
    ("v", "V", "Visa", "US"),
    ("bac", "BAC", "Bank of America", "US"),
    ("wmt", "WMT", "Walmart", "US"),
    ("ko", "KO", "Coca-Cola", "US"),
    ("jnj", "JNJ", "Johnson & Johnson", "US"),
    ("xom", "XOM", "ExxonMobil", "US"),
    ("dis", "DIS", "Disney", "US"),
    ("dia", "DIA", "Dow Jones ETF (DIA)", "US"),
    ("iwm", "IWM", "Russell 2000 ETF (IWM)", "US"),
    ("reliance", "RELIANCE.NS", "Reliance Industries", "India"),
    ("tcs", "TCS.NS", "Tata Consultancy Services", "India"),
    ("hdfcbank", "HDFCBANK.NS", "HDFC Bank", "India"),
    ("infy", "INFY.NS", "Infosys", "India"),
    ("icicibank", "ICICIBANK.NS", "ICICI Bank", "India"),
    ("sbin", "SBIN.NS", "State Bank of India", "India"),
    ("itc", "ITC.NS", "ITC", "India"),
    ("bhartiartl", "BHARTIARTL.NS", "Bharti Airtel", "India"),
    ("lt", "LT.NS", "Larsen & Toubro", "India"),
    ("hindunilvr", "HINDUNILVR.NS", "Hindustan Unilever", "India"),
    ("bajfinance", "BAJFINANCE.NS", "Bajaj Finance", "India"),
    ("asianpaint", "ASIANPAINT.NS", "Asian Paints", "India"),
    ("maruti", "MARUTI.NS", "Maruti Suzuki", "India"),
    ("wipro", "WIPRO.NS", "Wipro", "India"),
    ("nifty-50", "^NSEI", "Nifty 50", "India"),
    ("nifty-bank", "^NSEBANK", "Nifty Bank", "India"),
    ("sensex", "^BSESN", "BSE Sensex", "India"),
]

# What the pages show, rounded to what they print. --check compares at this
# precision, so a third-decimal Yahoo re-adjustment does not count as drift.
METRIC_KEYS = ("total_return", "annualized_return", "sharpe_ratio", "max_drawdown")


def _r(x, nd=3):
    return None if x is None else round(float(x), nd)


def _metrics(m):
    return {k: _r(m[k]) for k in METRIC_KEYS}


def _buy_and_hold(backtest):
    """The benchmark leg of a backtest's equity curve, through the same metrics code."""
    eq = pd.Series([p["benchmark"] for p in backtest["equity_curve"]], dtype=float)
    net = eq.pct_change().fillna(0.0)
    drawdown = eq / eq.cummax() - 1
    return _metrics(compute_metrics(net, eq, drawdown, pd.Series(np.ones(len(eq)))))


def run_stock(client, symbol):
    out = {"strategies": {}}
    for s in STRATEGY_NAMES:
        body = {"ticker": symbol, "start": START, "end": END, "strategy": s}
        bt = post(client, "/api/backtest", body)
        va = post(client, "/api/validate", body)
        if bt.status_code != 200 or va.status_code != 200:
            raise RuntimeError(f"{symbol} {s}: backtest {bt.status_code}, validate {va.status_code}: {bt.text[:200]} {va.text[:200]}")
        bt, va = bt.json(), va.json()
        if "buy_and_hold" not in out:
            out["buy_and_hold"] = _buy_and_hold(bt)
            out["bars"] = va["bars"]
            out["first_date"] = bt["equity_curve"][0]["date"]
            out["last_date"] = bt["equity_curve"][-1]["date"]
        wf = va["walk_forward"]
        out["strategies"][s] = {
            "defaults": _metrics(bt["metrics"]),
            "trades": bt["metrics"]["num_trades"],
            "walk_forward": {
                "split_date": wf["split_date"],
                "best_params": wf["best_params"],
                "in_sample_sharpe": _r(wf["best_in_sample"]["sharpe_ratio"]),
                "out_of_sample_sharpe": _r(wf["best_out_of_sample"]["sharpe_ratio"]),
                "verdict": wf["verdict"],
                "combinations": wf["combinations_tested"],
            },
            "pbo": _r(wf["overfitting"].get("pbo"), 2) if wf["overfitting"].get("computable") else None,
            "permutation_p": _r(va["permutation"]["p_value"]),
            "rolling_verdict": va["rolling_walk_forward"]["verdict"],
        }
    return out


def build():
    client = offline_client()
    stocks = {}
    for slug, symbol, name, market in STOCKS:
        t0 = time.time()
        stocks[slug] = {"symbol": symbol, "name": name, "market": market, **run_stock(client, symbol)}
        print(f"{time.time() - t0:5.1f}s  {symbol}", flush=True)
    return {"start": START, "end": END, "generated": time.strftime("%Y-%m-%d"), "stocks": stocks}


def _wins(stocks, a, b):
    """Stocks where `a` had the higher Sharpe than `b` at the defaults."""
    return sum(s["strategies"][a]["defaults"]["sharpe_ratio"] > s["strategies"][b]["defaults"]["sharpe_ratio"] for s in stocks)


def summary(results):
    """stockIndex.json: what page titles and descriptions quote. Per stock, its
    title and index row; per strategy and per pair of strategies, the counts
    the /strategies/<a>-vs-<b> pages lead with."""
    stocks = list(results["stocks"].values())
    return {"start": results["start"], "end": results["end"], "strategies": {
        name: {
            "held_up": sum(s["strategies"][name]["walk_forward"]["verdict"] == "held_up" for s in stocks),
            "beat_random": sum(s["strategies"][name]["permutation_p"] < 0.05 for s in stocks),
        }
        for name in STRATEGY_NAMES
    }, "pairs": {
        f"{a}-vs-{b}": {a: _wins(stocks, a, b), b: _wins(stocks, b, a)}
        for a, b in combinations(STRATEGY_NAMES, 2)
    }, "stocks": {
        slug: {
            "symbol": s["symbol"],
            "name": s["name"],
            "market": s["market"],
            "buy_and_hold_return": s["buy_and_hold"]["total_return"],
            "buy_and_hold_sharpe": s["buy_and_hold"]["sharpe_ratio"],
            "held_up": sum(x["walk_forward"]["verdict"] == "held_up" for x in s["strategies"].values()),
        }
        for slug, s in results["stocks"].items()
    }}


def _diff(old, new, path=""):
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            yield from _diff(old.get(k), new.get(k), f"{path}.{k}" if path else k)
    elif old != new:
        yield f"{path}: {old} -> {new}"


def main_():
    if "--index" in sys.argv:  # rewrite stockIndex.json from the saved results, no re-run
        INDEX.write_text(json.dumps(summary(json.loads(OUT.read_text())), indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {INDEX.name}")
        return
    fresh = build()
    if "--check" in sys.argv:
        saved = json.loads(OUT.read_text())
        drift = [d for d in _diff(saved["stocks"], fresh["stocks"])]
        for d in drift:
            print("DRIFT", d)
        print(f"{len(drift)} figure(s) changed" if drift else "every figure matches")
        sys.exit(1 if drift else 0)
    OUT.write_text(json.dumps(fresh, indent=1, ensure_ascii=False) + "\n")
    INDEX.write_text(json.dumps(summary(fresh), indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} and {INDEX.name}")


if __name__ == "__main__":
    main_()
