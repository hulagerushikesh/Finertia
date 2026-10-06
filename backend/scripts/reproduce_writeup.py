"""Re-run every API call behind planning/write-up.md and save the raw responses.

Goes through the real route handlers in-process (FastAPI TestClient), so the
numbers come from exactly the code production serves — only auth, the
Firestore user/run documents and the rate limiters are faked. Prices are a
fresh yfinance download (PRICE_CACHE=off), never the production price cache:
the script must not write to prod Firestore. Production's cache froze each
past year at its first download, so a fresh run can differ from prod in the
third decimal after any later Yahoo re-adjustment; that drift is the thing
this script exists to surface.

    cd backend && .venv/bin/python scripts/reproduce_writeup.py runs.json
    cd backend && .venv/bin/python scripts/reproduce_writeup.py --check runs.json

The first form re-runs every call (about a minute), saves the responses and
checks them; the second re-checks a saved file. Either prints each figure the
write-up quotes beside its fresh value and exits 1 if any no longer matches at
the precision printed. When the write-up changes a number, change it in
EXPECTED too.
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ["PRICE_CACHE"] = "off"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

PRO = {"role": "user", "isActive": True, "plan": "pro", "totalRuns": 0}


class _Doc:
    def get(self):
        return self

    exists = False

    def to_dict(self):
        return {}

    def set(self, *a, **k):
        pass

    def update(self, *a, **k):
        pass


class _Collection:
    def document(self, *a, **k):
        return _Doc()

    def add(self, *a, **k):
        return (None, _Doc())


class _Db:
    def collection(self, *a, **k):
        return _Collection()


main.verify_token = lambda token: {"uid": "reproduce", "email": "reproduce@example.com"}
main.get_user_profile = lambda uid: PRO
main.get_db = lambda: _Db()

A, B = "2018-01-01", "2024-01-01"
STRATS = ("momentum", "macd", "bollinger")

# (label, route, body) — one entry per run the write-up quotes.
CALLS = (
    [(f"validate AAPL {s} {A}..{B}", "/api/validate", {"ticker": "AAPL", "start": A, "end": B, "strategy": s}) for s in STRATS]
    + [(f"validate AAPL {s} {A}..2025-01-01", "/api/validate", {"ticker": "AAPL", "start": A, "end": "2025-01-01", "strategy": s}) for s in STRATS]
    + [(f"validate {t} bollinger {A}..{B}", "/api/validate", {"ticker": t, "start": A, "end": B, "strategy": "bollinger"}) for t in ("BABA", "PYPL", "INTC")]
    + [(f"backtest AAPL {s} {A}..{B}", "/api/backtest", {"ticker": "AAPL", "start": A, "end": B, "strategy": s}) for s in STRATS]
    + [
        ("backtest AAPL bollinger 2015-01-01..2020-01-01", "/api/backtest", {"ticker": "AAPL", "start": "2015-01-01", "end": "2020-01-01", "strategy": "bollinger"}),
        (f"backtest SPY momentum {A}..{B}", "/api/backtest", {"ticker": "SPY", "start": A, "end": B, "strategy": "momentum"}),
        (f"backtest BABA bollinger {A}..{B}", "/api/backtest", {"ticker": "BABA", "start": A, "end": B, "strategy": "bollinger"}),
    ]
    + [(f"portfolio/validate AAPL+MSFT+GOOGL {s} {A}..{B}", "/api/portfolio/validate", {"tickers": ["AAPL", "MSFT", "GOOGL"], "start": A, "end": B, "strategy": s}) for s in ("momentum", "bollinger")]
)


# Every figure the write-up quotes, as printed there: (section, label, run, path, quoted).
# `path` walks the saved response; a callable gets the response instead. The
# comparison rounds the fresh value to the precision the write-up printed, so
# "0.95" matches 0.949 and "0.949" does not match 0.951.
V24 = "validate AAPL {} 2018-01-01..2024-01-01"
V25 = "validate AAPL {} 2018-01-01..2025-01-01"
WF = ("walk_forward",)
ROLL = ("rolling_walk_forward",)
STITCH = ROLL + ("out_of_sample_stitched",)
REG = STITCH + ("regimes", "regimes")
JOINT = STITCH + ("regimes", "joint", "cells")
SNOOP = WF + ("snooping",)


def _fold(i, key):
    return lambda r: r["rolling_walk_forward"]["folds"][i][key]


def _bt(key):
    return ("benchmark_test", key)


EXPECTED = []
for s, is_, oos, pbo, perm in (
    ("momentum", "0.949", "-0.303", "0.23", "0.022"),
    ("macd", "0.511", "-0.300", "0.30", "0.008"),
    ("bollinger", "0.558", "1.169", "0.13", "0.066"),
):
    EXPECTED += [
        ("first window", f"{s} in-sample Sharpe", V24.format(s), WF + ("best_in_sample", "sharpe_ratio"), is_),
        ("first window", f"{s} out-of-sample Sharpe", V24.format(s), WF + ("best_out_of_sample", "sharpe_ratio"), oos),
        ("four checks", f"{s} PBO", V24.format(s), WF + ("overfitting", "pbo"), pbo),
        ("four checks", f"{s} permutation p", V24.format(s), ("permutation", "p_value"), perm),
    ]
EXPECTED += [
    ("first window", "momentum best lookback", V24.format("momentum"), WF + ("best_params", "momentum_lookback"), "20"),
    ("first window", "momentum best MA", V24.format("momentum"), WF + ("best_params", "ma_window"), "200"),
    ("first window", "in-sample end", V24.format("momentum"), WF + ("boundary", "in_sample_end_date"), "2022-02-16"),
    ("first window", "out-of-sample start", V24.format("momentum"), WF + ("boundary", "out_of_sample_start_date"), "2022-04-05"),
    ("first window", "bars", V24.format("momentum"), ("bars",), "1509"),
    ("first window", "purge bars", V24.format("momentum"), WF + ("boundary", "purge_bars"), "16"),
    ("four checks", "momentum DSR", V24.format("momentum"), WF + ("deflated", "deflated_sharpe_ratio"), "0.81"),
    ("four checks", "bollinger DSR", V24.format("bollinger"), WF + ("deflated", "deflated_sharpe_ratio"), "0.37"),
    ("four checks", "momentum effective N", V24.format("momentum"), WF + ("deflated", "effective_trials", "n_trials_effective"), "6"),
    ("four checks", "momentum effective N (clusters)", V24.format("momentum"), WF + ("deflated", "effective_trials", "n_trials_lower_bound"), "3"),
    ("four checks", "macd effective N", V24.format("macd"), WF + ("deflated", "effective_trials", "n_trials_effective"), "2"),
    ("four checks", "bollinger effective N", V24.format("bollinger"), WF + ("deflated", "effective_trials", "n_trials_effective"), "7"),
    ("four checks", "bollinger effective N (clusters)", V24.format("bollinger"), WF + ("deflated", "effective_trials", "n_trials_lower_bound"), "2"),
    ("four checks", "momentum OOS bars", V24.format("momentum"), WF + ("out_of_sample_bars",), "437"),
]
for s, is_, oos, verdict, pbo in (
    ("momentum", "0.766", "0.547", "held_up", "0.19"),
    ("macd", "0.656", "-0.114", "failed", "0.77"),
    ("bollinger", "0.686", "-0.157", "failed", "0.11"),
):
    EXPECTED += [
        ("window moved", f"{s} in-sample Sharpe", V25.format(s), WF + ("best_in_sample", "sharpe_ratio"), is_),
        ("window moved", f"{s} out-of-sample Sharpe", V25.format(s), WF + ("best_out_of_sample", "sharpe_ratio"), oos),
        ("window moved", f"{s} verdict", V25.format(s), WF + ("verdict",), verdict),
        ("window moved", f"{s} PBO", V25.format(s), WF + ("overfitting", "pbo"), pbo),
    ]
EXPECTED += [
    ("window moved", "in-sample end", V25.format("momentum"), WF + ("boundary", "in_sample_end_date"), "2022-10-26"),
    ("window moved", "momentum best MA", V25.format("momentum"), WF + ("best_params", "ma_window"), "20"),
]
for s, folds, stitched, lo, hi in (
    ("momentum", ("0.27", "1.10", "-0.80", "0.88"), "0.12", "-0.8", "1.3"),
    ("macd", ("-0.32", "0.58", "0.06", "-0.60"), "-0.08", None, None),
    ("bollinger", ("0.57", "-0.60", "1.90", "-1.73"), "0.44", "-0.4", "1.2"),
):
    for i, q in enumerate(folds):
        EXPECTED.append(("rolling", f"{s} fold {i + 1} Sharpe", V24.format(s), _fold(i, "out_of_sample_sharpe"), q))
    EXPECTED.append(("rolling", f"{s} stitched Sharpe", V24.format(s), STITCH + ("sharpe_ratio",), stitched))
    if lo:
        EXPECTED += [
            ("rolling", f"{s} stitched CI low", V24.format(s), STITCH + ("sharpe_interval", "low"), lo),
            ("rolling", f"{s} stitched CI high", V24.format(s), STITCH + ("sharpe_interval", "high"), hi),
        ]
    EXPECTED.append(("rolling", f"{s} verdict", V24.format(s), ROLL + ("verdict",), "regime_dependent"))
    EXPECTED.append(("rolling", f"{s} verdict, 2025 window", V25.format(s), ROLL + ("verdict",), "regime_dependent"))
EXPECTED += [
    ("rolling", "momentum distinct parameter sets", V24.format("momentum"), ROLL + ("parameter_stability", "distinct_parameter_sets"), "4"),
    ("rolling", "macd distinct parameter sets", V24.format("macd"), ROLL + ("parameter_stability", "distinct_parameter_sets"), "2"),
    ("rolling", "bollinger distinct parameter sets", V24.format("bollinger"), ROLL + ("parameter_stability", "distinct_parameter_sets"), "1"),
]
for s, vals in (
    ("market", None),
    ("momentum", ("2.26", "0.70", "-0.76")),
    ("macd", ("0.66", "2.61", "-1.76")),
    ("bollinger", ("-1.83", "0.80", "1.31")),
):
    if vals:
        for reg, q in zip(("low", "mid", "high"), vals):
            EXPECTED.append(("regimes", f"{s} {reg}-vol Sharpe", V24.format(s), REG + (reg, "sharpe_ratio"), q))
for reg, q in zip(("low", "mid", "high"), ("2.49", "0.70", "0.60")):
    EXPECTED.append(("regimes", f"market {reg}-vol Sharpe", V24.format("momentum"), REG + (reg, "market_sharpe_ratio"), q))
EXPECTED += [
    ("regimes", "low-vol ceiling", V24.format("momentum"), STITCH + ("regimes", "thresholds", "low_max"), "0.22"),
    ("regimes", "high-vol floor", V24.format("momentum"), STITCH + ("regimes", "thresholds", "high_min"), "0.32"),
]
for (vol, tr), q, n in (
    (("low", "flat"), "2.40", "124"), (("low", "up"), "2.29", "135"),
    (("mid", "flat"), "0.81", "195"), (("mid", "up"), "0.45", "81"),
    (("high", "flat"), "-1.88", "199"), (("high", "up"), "1.29", "84"),
):
    EXPECTED += [
        ("vol x trend", f"momentum {vol}/{tr} Sharpe", V24.format("momentum"), JOINT + (vol, tr, "sharpe_ratio"), q),
        ("vol x trend", f"momentum {vol}/{tr} bars", V24.format("momentum"), JOINT + (vol, tr, "bars"), n),
    ]
EXPECTED += [
    ("vol x trend", "bollinger high/flat Sharpe", V24.format("bollinger"), JOINT + ("high", "flat", "sharpe_ratio"), "2.19"),
    ("vol x trend", "bollinger high/up Sharpe", V24.format("bollinger"), JOINT + ("high", "up", "sharpe_ratio"), "-1.01"),
]
for run, excess, naive, rc, spa in (
    (V24.format("momentum"), "-6.4", "0.63", "0.89", "1.00"),
    (V24.format("bollinger"), "-25.0", "0.98", "0.99", "1.00"),
    (V25.format("momentum"), "-9.6", "0.76", "0.96", "1.00"),
    ("validate BABA bollinger 2018-01-01..2024-01-01", "15.4", "0.17", "0.33", "0.33"),
    ("validate PYPL bollinger 2018-01-01..2024-01-01", "8.8", "0.31", "0.47", "0.47"),
    ("validate INTC bollinger 2018-01-01..2024-01-01", "5.7", "0.37", "0.52", "0.53"),
):
    name = run.split()[1] + " " + run.split()[2] + " " + run.split()[3][-10:-6]
    EXPECTED += [
        ("whole grid", f"{name} best excess %/yr", run, lambda r: r["walk_forward"]["snooping"]["best"]["excess_return_annualised"] * 100, excess),
        ("whole grid", f"{name} p alone", run, SNOOP + ("best", "p_value_naive"), naive),
        ("whole grid", f"{name} Reality Check p", run, SNOOP + ("reality_check", "p_value"), rc),
        ("whole grid", f"{name} SPA p", run, SNOOP + ("spa", "p_value"), spa),
        ("whole grid", f"{name} survivors", run, SNOOP + ("stepdown", "n_beating_benchmark"), "0"),
    ]
PV = "portfolio/validate AAPL+MSFT+GOOGL {} 2018-01-01..2024-01-01"
for s, is_, oos, verdict, p, legs, excess in (
    ("momentum", "0.42", "-0.51", "failed", "0.134", "1", "-23.9"),
    ("bollinger", "0.83", "0.77", "held_up", "0.002", "3", "-18.7"),
):
    EXPECTED += [
        ("basket", f"{s} in-sample Sharpe", PV.format(s), WF + ("best_in_sample", "sharpe_ratio"), is_),
        ("basket", f"{s} out-of-sample Sharpe", PV.format(s), WF + ("best_out_of_sample", "sharpe_ratio"), oos),
        ("basket", f"{s} verdict", PV.format(s), WF + ("verdict",), verdict),
        ("basket", f"{s} timing p", PV.format(s), ("permutation", "p_value"), p),
        ("basket", f"{s} legs beating random timing", PV.format(s), ("permutation", "legs_significant"), legs),
        ("basket", f"{s} best cell vs basket %/yr", PV.format(s), lambda r: r["walk_forward"]["snooping"]["best"]["excess_return_annualised"] * 100, excess),
        ("basket", f"{s} SPA p", PV.format(s), SNOOP + ("spa", "p_value"), "1.00"),
    ]
for run, strat, bh, gap, se, p in (
    ("backtest AAPL momentum 2018-01-01..2024-01-01", "0.59", "0.98", "-0.39", "0.51", "0.36"),
    ("backtest AAPL bollinger 2018-01-01..2024-01-01", "0.06", "0.98", "-0.91", "0.54", "0.13"),
    ("backtest AAPL macd 2018-01-01..2024-01-01", "0.53", "0.98", "-0.44", "0.54", "0.39"),
    ("backtest AAPL bollinger 2015-01-01..2020-01-01", "-0.46", "0.99", "-1.45", "0.60", "0.038"),
    ("backtest SPY momentum 2018-01-01..2024-01-01", "-0.26", "0.65", "-0.91", "0.62", "0.080"),
    ("backtest BABA bollinger 2018-01-01..2024-01-01", "0.13", "-0.08", "0.21", "0.57", "0.73"),
):
    name = " ".join(run.split()[1:3]) + " " + run.split()[3][:4]
    EXPECTED += [
        ("sharpe gap", f"{name} strategy Sharpe", run, _bt("strategy_sharpe"), strat),
        ("sharpe gap", f"{name} buy-and-hold Sharpe", run, _bt("benchmark_sharpe"), bh),
        ("sharpe gap", f"{name} gap", run, _bt("difference"), gap),
        ("sharpe gap", f"{name} std error", run, _bt("standard_error"), se),
        ("sharpe gap", f"{name} p", run, _bt("p_value"), p),
    ]


for s_, lo, hi in (("momentum", "-1.4", "1.4"), ("bollinger", "0.2", "2.2")):
    EXPECTED += [
        ("four checks", f"{s_} single-split OOS CI low", f"derived oos-interval AAPL {s_}", ("low",), lo),
        ("four checks", f"{s_} single-split OOS CI high", f"derived oos-interval AAPL {s_}", ("high",), hi),
    ]


def _oos_interval(results, strategy):
    """The single-split out-of-sample Sharpe interval, which no route returns.

    /api/validate reports the out-of-sample Sharpe but not a band around it, so
    the write-up's figure is computed here from the same pieces: the winning
    cell's positions on the full window, the engine's net returns, sliced at
    the purged out-of-sample start, bootstrapped with a seed named after the
    run. Endpoints move by up to ~0.3 between seeds at 1,000 resamples, which
    is why the write-up prints them to one decimal.
    """
    from bootstrap import bootstrap_metrics, stable_seed  # noqa: PLC0415
    from data import fetch_ohlcv  # noqa: PLC0415
    from engine import apply_positions, compute_returns  # noqa: PLC0415
    from strategies import build_positions  # noqa: PLC0415

    wf = results[V24.format(strategy)]["walk_forward"]
    close = fetch_ohlcv("AAPL", "2018-01-01", "2024-01-01")["Close"]
    net = apply_positions(build_positions(close, strategy, wf["best_params"]), compute_returns(close), 0.001)["net_return"]
    oos = net.iloc[wf["boundary"]["oos_start"]:]
    band = bootstrap_metrics(oos, seed=stable_seed("AAPL", "2018-01-01", "2024-01-01", strategy, "wf-oos"))["metrics"]["sharpe_ratio"]
    return {"bars": len(oos), "point": band["point"], "low": band["low"], "high": band["high"]}


def _get(resp, path):
    if callable(path):
        return path(resp)
    for k in path:
        resp = resp[k]
    return resp


def _matches(fresh, quoted):
    if isinstance(fresh, bool) or not isinstance(fresh, (int, float)):
        return str(fresh) == quoted
    decimals = len(quoted.split(".")[1]) if "." in quoted else 0
    return round(float(fresh), decimals) == round(float(quoted), decimals)


def check(results):
    """Print every quoted figure beside its fresh value; return the mismatches."""
    bad = []
    section = None
    order = list(dict.fromkeys(e[0] for e in EXPECTED))
    for sec, label, run, path, quoted in sorted(EXPECTED, key=lambda e: order.index(e[0])):
        if sec != section:
            print(f"\n## {sec}")
            section = sec
        try:
            fresh = _get(results[run], path)
        except (KeyError, IndexError, TypeError) as exc:
            fresh, ok = f"<missing: {exc!r}>", False
        else:
            ok = _matches(fresh, quoted)
        shown = f"{fresh:.4f}" if isinstance(fresh, float) else fresh
        print(f"  {'ok ' if ok else 'XX '} {label:<42} quoted {quoted:>10}   now {shown}")
        if not ok:
            bad.append((sec, label, quoted, shown))
    print(f"\n{len(EXPECTED) - len(bad)} of {len(EXPECTED)} quoted figures reproduce.")
    return bad


def main_():
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        results = json.loads(Path(sys.argv[2]).read_text())["results"]
        sys.exit(1 if check(results) else 0)
    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "writeup_runs.json")
    client = TestClient(main.app, raise_server_exceptions=True)
    results = {}
    for label, route, body in CALLS:
        for limiter in (main.ip_limiter, main.backtest_limiter, main.validate_limiter):
            limiter._hits.clear()
        t0 = time.time()
        r = client.post(route, json=body, headers={"Authorization": "Bearer x"})
        print(f"{r.status_code}  {time.time() - t0:5.1f}s  {label}", flush=True)
        results[label] = r.json() if r.status_code == 200 else {"_status": r.status_code, "_body": r.text[:500]}
    for strategy in ("momentum", "bollinger"):
        results[f"derived oos-interval AAPL {strategy}"] = _oos_interval(results, strategy)
    out_path.write_text(json.dumps({"ran_at": time.strftime("%Y-%m-%d %H:%M"), "results": results}, default=str))
    print(f"wrote {out_path}")
    sys.exit(1 if check(results) else 0)


if __name__ == "__main__":
    main_()
