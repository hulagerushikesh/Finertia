"""The index scan: scan.py's maths and POST /api/scan end to end (fakes only)."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

import data
import scan
import universes
from price_store import MemoryPriceStore
from tests.test_data import _bars
from tests.test_routes import AUTH, PRO, api  # noqa: F401 — the fixture

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
TICKERS = ["AAA.NS", "BBB.NS", "CCC.NS", "DDD.NS"]
BODY = {"universe": "nifty50", "start": "2020-01-01", "end": "2026-01-01", "strategy": "momentum"}


@pytest.fixture
def scanning(api, monkeypatch):  # noqa: F811
    """The api fixture with a tiny 'nifty50' whose prices sit in the store,
    except DDD.NS, which the nightly load never stored."""
    client, state = api
    store = MemoryPriceStore()
    data.configure_store(store)
    data._cache.clear()
    monkeypatch.setattr(data, "_now", lambda: NOW)
    for seed, t in enumerate(TICKERS[:3]):
        df = _bars("2005-01-01", "2026-09-14", seed=seed)
        store.put_many(data.docs_for(t, df, 2005, 2026, now=NOW))
    real = universes.load
    monkeypatch.setattr(
        universes, "load",
        lambda name: {**real(name), "tickers": TICKERS} if name == "nifty50" else real(name),
    )

    def no_yahoo(*a):
        raise AssertionError("a scan must never call the provider")

    monkeypatch.setattr(data, "_download", no_yahoo)
    yield client, state
    data.configure_store(None)
    data._cache.clear()


def test_a_scan_runs_every_stored_stock_and_skips_the_rest(scanning):
    client, state = scanning
    r = client.post("/api/scan", json=BODY, headers=AUTH)
    assert r.status_code == 200, r.text
    body = r.json()
    rows = {row["ticker"]: row for row in body["rows"]}
    assert [rows[t]["status"] for t in TICKERS] == ["ok", "ok", "ok", "skipped"]
    assert "no stored prices" in rows["DDD.NS"]["reason"]
    s = body["summary"]
    assert (s["stocks"], s["ran"], s["skipped"]) == (4, 3, 1)
    assert s["expected_by_chance"] == pytest.approx(0.05 * s["tested_against_holding"], abs=0.01)
    assert body["universe_title"] == "Nifty 50"
    for k in ("sharpe_ratio", "max_drawdown", "excess_return", "p_value"):
        assert k in rows["AAA.NS"]


def test_a_scan_row_matches_the_backtest_of_that_stock(scanning, monkeypatch):
    """Same pipeline: the scan's number for a stock is the backtest's number."""
    client, state = scanning
    from api import core

    monkeypatch.setattr(core, "fetch_ohlcv", lambda t, s, e: data.cached_ohlcv(t, s, e))
    row = next(r for r in client.post("/api/scan", json=BODY, headers=AUTH).json()["rows"] if r["ticker"] == "BBB.NS")
    bt = client.post("/api/backtest", json={**BODY, "ticker": "BBB.NS"}, headers=AUTH).json()
    assert row["sharpe_ratio"] == bt["metrics"]["sharpe_ratio"]
    assert row["total_return"] == bt["metrics"]["total_return"]


def test_a_scan_counts_as_one_run_and_is_rate_limited(scanning):
    client, state = scanning
    state["profile"] = dict(PRO)
    codes = [client.post("/api/scan", json=BODY, headers=AUTH).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    # One run per scan, not one per stock: the fake profile reads 0 each
    # time, so every scan writes 0 + 1.
    assert state["db"].store["users/u1"]["runsThisPeriod"] == 1


def test_only_the_scannable_indexes_are_accepted(scanning):
    client, _ = scanning
    r = client.post("/api/scan", json={**BODY, "universe": "sp500"}, headers=AUTH)
    assert r.status_code == 422 and "Scans cover" in r.text


def test_a_rule_can_be_scanned(scanning):
    client, _ = scanning
    rule = {
        "direction": "long",
        "entry": {"all": [{"left": {"ind": "rsi", "n": 14}, "op": "<", "right": {"value": 30}}]},
        "exit": {"all": [{"left": {"ind": "rsi", "n": 14}, "op": ">", "right": {"value": 55}}]},
    }
    r = client.post("/api/scan", json={**BODY, "strategy": "rules", "rule": rule}, headers=AUTH)
    assert r.status_code == 200 and r.json()["summary"]["ran"] == 3


def test_nothing_stored_is_a_503(scanning, monkeypatch):
    client, _ = scanning
    data.configure_store(MemoryPriceStore())
    data._cache.clear()
    assert client.post("/api/scan", json=BODY, headers=AUTH).status_code == 503


# ── the maths ───────────────────────────────────────────────────────────────

def test_benjamini_hochberg_matches_the_textbook_example():
    # Benjamini & Hochberg (1995)-style: with these ten p-values at 5%, the
    # largest k with p(k) <= k/10 * 0.05 is k = 2.
    p = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]
    keep = scan.benjamini_hochberg(p)
    assert keep == [True, True] + [False] * 8
    assert scan.benjamini_hochberg([]) == []


def test_pure_noise_beats_holding_about_as_often_as_chance_says():
    rng = np.random.default_rng(7)
    rows = []
    for i in range(400):
        p = float(rng.uniform())
        rows.append({"ticker": str(i), "status": "ok", "total_return": 0.1, "excess_return": 0.0,
                     "sharpe_ratio": 0.5, "p_value": p, "sharpe_vs_hold": float(rng.normal())})
    s = scan.summarise(rows)
    # Under the null about α × N "beat" by luck; correction leaves ~none.
    assert abs(s["beats_holding"] - s["expected_by_chance"]) < 12
    assert s["survives_correction"] <= 2


def test_a_losing_strategy_never_counts_as_beating_holding():
    rows = [{"ticker": "X", "status": "ok", "total_return": -0.5, "excess_return": -1.0,
             "sharpe_ratio": -1.0, "p_value": 0.0001, "sharpe_vs_hold": -2.0}]
    s = scan.summarise(rows)
    assert s["beats_holding"] == 0 and s["survives_correction"] == 0
