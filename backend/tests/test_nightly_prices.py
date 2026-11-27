"""The nightly price load (nightly_prices.py) and the tracked universe.

Runs against MemoryPriceStore with the provider replaced by test_data's fake.
No network, no credentials."""

from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

import data
import nightly_prices as nightly
import universes
from data import fetch_ohlcv
from tests.test_data import NOW, FakeYahoo, _bars
from price_store import MemoryPriceStore

TODAY = pd.Timestamp(NOW.date())


@pytest.fixture
def setup(monkeypatch):
    fake = FakeYahoo()
    monkeypatch.setattr(data, "_download", fake)
    monkeypatch.setattr(data, "_now", lambda: NOW)
    store = MemoryPriceStore()
    data.configure_store(store)
    data._cache.clear()
    yield fake, store
    data.configure_store(None)
    data._cache.clear()


def no_sleep(_):
    pass


# ── the universe ────────────────────────────────────────────────────────────

def test_every_universe_has_its_source_and_yahoo_symbols():
    for name in universes.NAMES:
        u = universes.load(name)
        assert u["source"] and u["as_of"]
        assert u["count"] == len(u["tickers"]) == len(set(u["tickers"]))
        assert all(t == t.upper() and "." not in t.replace(".NS", "") for t in u["tickers"]), name
    assert all(t.endswith(".NS") for t in universes.load("nifty50")["tickers"])
    assert "BRK-B" in universes.load("sp500")["tickers"]


def test_the_tracked_set_is_the_union_of_the_lists():
    everything = universes.tickers()
    assert len(everything) == len(set(everything))
    assert 550 < len(everything) < 700
    assert universes.is_tracked("aapl") and universes.is_tracked("RELIANCE.NS")
    assert not universes.is_tracked("NOT-A-TICKER")


def test_an_unknown_universe_is_named_in_the_error():
    with pytest.raises(ValueError, match="sp500"):
        universes.load("ftse100")


# ── checks ──────────────────────────────────────────────────────────────────

def test_a_clean_download_passes():
    v = nightly.check("X", _bars("2024-01-01", "2026-09-14"), today=TODAY)
    assert v.errors == [] and v.warnings == []


def test_bad_closes_block_the_write():
    df = _bars("2025-01-01", "2026-09-14")
    df.iloc[10, df.columns.get_loc("Close")] = np.nan
    df.iloc[20, df.columns.get_loc("Close")] = -1.0
    v = nightly.check("X", df, today=TODAY)
    assert any("missing closes" in e for e in v.errors)
    assert any("below zero" in e for e in v.errors)
    assert nightly.check("X", df.iloc[0:0], today=TODAY).errors == ["no bars"]


def test_jumps_gaps_and_staleness_are_warnings():
    df = _bars("2025-01-01", "2026-08-01")
    df.iloc[100:, df.columns.get_loc("Close")] *= 4  # an unadjusted 4:1 split, backwards
    df = df.drop(df.index[200:215])                   # three weeks missing
    v = nightly.check("X", df, today=TODAY)
    assert v.errors == []
    text = " | ".join(v.warnings)
    assert "daily moves over 50%" in text
    assert "gaps longer than" in text
    assert "weekdays ago" in text


# ── the load ────────────────────────────────────────────────────────────────

def test_the_load_writes_each_ticker_under_one_batch(setup):
    fake, store = setup
    summary = nightly.run(["AAA", "BBB"], store, now=NOW, sleep=no_sleep)
    assert summary["written"] == 2 and summary["failed"] == 0
    docs = store.get_many("AAA", list(range(nightly.SINCE, NOW.year + 1)))
    assert len(docs) == NOW.year - nightly.SINCE + 1
    assert len({d["batch"] for d in docs.values()}) == 1
    assert fake.calls[0] == ("AAA", f"{nightly.SINCE}-01-01", f"{NOW.year + 1}-01-01")


def test_years_already_cached_before_since_stay_in_the_same_batch(setup):
    fake, store = setup
    fetch_ohlcv("AAA", "1999-01-01", "2001-01-01")  # a user asked for 1999
    nightly.run(["AAA"], store, now=NOW + timedelta(days=1), sleep=no_sleep)
    assert fake.calls[-1][1] == "1999-01-01"
    docs = store.get_many("AAA", list(range(1999, NOW.year + 1)))
    assert len({d["batch"] for d in docs.values()}) == 1


def test_a_dry_run_writes_nothing(setup):
    _, store = setup
    summary = nightly.run(["AAA"], store, now=NOW, dry_run=True, sleep=no_sleep)
    assert summary["written"] == 1 and store.years_for("AAA") == []


def test_one_failing_ticker_keeps_yesterdays_copy_and_the_run_goes_on(setup, monkeypatch):
    fake, store = setup
    nightly.run(["AAA", "BBB"], store, now=NOW, sleep=no_sleep)
    before = store.get_many("AAA", [NOW.year])[NOW.year]["batch"]

    def flaky(ticker, start, end):
        if ticker == "AAA":
            raise ConnectionError("reset by peer")
        return _bars(start, end)

    monkeypatch.setattr(data, "_download", flaky)
    waits = []
    summary = nightly.run(["AAA", "BBB"], store, now=NOW + timedelta(days=1), sleep=waits.append)
    assert summary["failed"] == 1 and summary["written"] == 1
    assert summary["failures"][0]["ticker"] == "AAA" and "reset by peer" in summary["failures"][0]["reason"]
    assert store.get_many("AAA", [NOW.year])[NOW.year]["batch"] == before
    # Two backoffs for AAA's retries, then the pace pause before BBB.
    assert waits == [nightly.BACKOFF_SECONDS, 2 * nightly.BACKOFF_SECONDS, nightly.PACE_SECONDS]


def test_a_download_that_fails_its_checks_is_not_written(setup, monkeypatch):
    _, store = setup

    def broken(ticker, start, end):
        df = _bars(start, end)
        df.iloc[5, df.columns.get_loc("Close")] = 0.0
        return df

    monkeypatch.setattr(data, "_download", broken)
    summary = nightly.run(["AAA"], store, now=NOW, sleep=no_sleep)
    assert summary["failed"] == 1 and "below zero" in summary["failures"][0]["reason"]
    assert store.years_for("AAA") == []


def test_main_exits_non_zero_only_when_most_of_the_load_failed(setup, monkeypatch):
    monkeypatch.setattr(nightly.time, "sleep", no_sleep)
    monkeypatch.setattr(universes, "tickers", lambda *n: ["AAA", "BBB", "CCC"])
    assert nightly.main(["--pace", "0"]) == 0
    monkeypatch.setattr(data, "_download", lambda *a: (_ for _ in ()).throw(ConnectionError("down")))
    monkeypatch.setattr(nightly, "BACKOFF_SECONDS", 0)
    assert nightly.main(["--pace", "0"]) == 1


# ── serving a tracked ticker ────────────────────────────────────────────────

def test_a_tracked_ticker_is_served_from_the_nightly_copy_all_day(setup, monkeypatch):
    fake, store = setup
    monkeypatch.setenv("NIGHTLY_PRICES", "on")
    nightly.run(["AAPL"], store, now=NOW, sleep=no_sleep)
    calls = len(fake.calls)
    later = NOW + data.PARTIAL_YEAR_TTL + timedelta(hours=12)  # past the old 6 h
    monkeypatch.setattr(data, "_now", lambda: later)
    df = fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01")
    assert df.attrs["data_source"] == "cache" and len(fake.calls) == calls


def test_the_tracked_window_still_ends(setup, monkeypatch):
    fake, store = setup
    monkeypatch.setenv("NIGHTLY_PRICES", "on")
    nightly.run(["AAPL"], store, now=NOW, sleep=no_sleep)
    monkeypatch.setattr(data, "_now", lambda: NOW + data.TRACKED_TTL + timedelta(minutes=1))
    assert fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01").attrs["data_source"] == "yfinance"


def test_without_the_switch_tracked_tickers_keep_the_six_hour_rule(setup, monkeypatch):
    fake, store = setup
    monkeypatch.delenv("NIGHTLY_PRICES", raising=False)
    nightly.run(["AAPL"], store, now=NOW, sleep=no_sleep)
    monkeypatch.setattr(data, "_now", lambda: NOW + data.PARTIAL_YEAR_TTL + timedelta(minutes=1))
    assert fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01").attrs["data_source"] == "yfinance"


def test_an_untracked_ticker_keeps_the_six_hour_rule(setup, monkeypatch):
    fake, store = setup
    monkeypatch.setenv("NIGHTLY_PRICES", "on")
    nightly.run(["ZZZZ"], store, now=NOW, sleep=no_sleep)
    monkeypatch.setattr(data, "_now", lambda: NOW + data.PARTIAL_YEAR_TTL + timedelta(minutes=1))
    assert fetch_ohlcv("ZZZZ", "2026-01-01", "2026-09-01").attrs["data_source"] == "yfinance"
