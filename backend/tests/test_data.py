"""The two-tier price cache in data.py, run against MemoryPriceStore with
yfinance replaced by a fake. No network, no credentials."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

import data
from data import DataUnavailableError, fetch_ohlcv
from price_store import COLUMNS, MemoryPriceStore, doc_to_frame, frame_to_doc

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def _bars(start: str, end: str, seed: int = 0) -> pd.DataFrame:
    """Deterministic daily bars on business days in [start, end)."""
    idx = pd.bdate_range(start, pd.Timestamp(end) - pd.Timedelta(days=1))
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, len(idx)))
    df = pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.01,
            "Low": close * 0.98,
            "Close": close,
            "Volume": np.full(len(idx), 1_000_000.0),
        },
        index=idx,
    )
    df.index.name = "Date"
    return df


class FakeYahoo:
    """Stands in for data._download. Records calls; can be told to fail, to
    return nothing, or to only know a symbol from a given year."""

    def __init__(self, listed_from: str | None = None):
        self.calls: list[tuple[str, str, str]] = []
        self.fail: Exception | None = None
        self.empty = False
        self.listed_from = listed_from
        self.seed = 0

    def __call__(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        if self.fail:
            raise self.fail
        if self.empty:
            return pd.DataFrame(columns=COLUMNS)
        if self.listed_from and pd.Timestamp(start) < pd.Timestamp(self.listed_from):
            start = self.listed_from
        return _bars(start, end, seed=self.seed)


@pytest.fixture
def yahoo(monkeypatch):
    fake = FakeYahoo()
    monkeypatch.setattr(data, "_download", fake)
    monkeypatch.setattr(data, "_now", lambda: NOW)
    store = MemoryPriceStore()
    data.configure_store(store)
    data._cache.clear()
    yield fake, store
    data.configure_store(None)
    data._cache.clear()


# ── round trip ──────────────────────────────────────────────────────────────

def test_doc_round_trip_preserves_bars():
    frame = _bars("2020-01-01", "2021-01-01")
    doc = frame_to_doc("aapl", 2020, frame, batch="b", complete=True, fetched_at="t")
    back = doc_to_frame(doc)
    assert doc["ticker"] == "AAPL"
    assert list(back.columns) == COLUMNS
    pd.testing.assert_frame_equal(back, frame, check_freq=False, check_names=False)


def test_empty_year_round_trips():
    frame = _bars("2020-01-01", "2021-01-01").iloc[0:0]
    back = doc_to_frame(frame_to_doc("X", 2020, frame, batch="b", complete=True, fetched_at="t"))
    assert back.empty and list(back.columns) == COLUMNS


# ── tiers ───────────────────────────────────────────────────────────────────

def test_miss_downloads_and_writes_every_year(yahoo):
    fake, store = yahoo
    df = fetch_ohlcv("AAPL", "2019-03-01", "2021-06-01")
    assert df.attrs["data_source"] == "yfinance"
    assert fake.calls == [("AAPL", "2019-01-01", "2022-01-01")]
    assert store.years_for("AAPL") == [2019, 2020, 2021]
    # Sliced to the request, end exclusive.
    assert df.index.min() >= pd.Timestamp("2019-03-01")
    assert df.index.max() < pd.Timestamp("2021-06-01")


def test_same_key_is_served_from_memory(yahoo):
    fake, _ = yahoo
    fetch_ohlcv("AAPL", "2019-01-01", "2020-01-01")
    df = fetch_ohlcv("aapl", "2019-01-01", "2020-01-01")
    assert df.attrs["data_source"] == "memory"
    assert len(fake.calls) == 1


def test_sub_range_of_cached_span_is_served_from_store(yahoo):
    fake, _ = yahoo
    fetch_ohlcv("AAPL", "2019-01-01", "2022-01-01")
    df = fetch_ohlcv("AAPL", "2020-02-01", "2021-11-01")
    assert df.attrs["data_source"] == "cache"
    assert len(fake.calls) == 1
    assert df.index.min() >= pd.Timestamp("2020-02-01")
    assert df.index.max() < pd.Timestamp("2021-11-01")


def test_end_is_exclusive_at_a_year_boundary(yahoo):
    fake, store = yahoo
    fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    # Nothing from 2021 was needed, so nothing from 2021 was fetched.
    assert fake.calls == [("AAPL", "2020-01-01", "2021-01-01")]
    assert store.years_for("AAPL") == [2020]


def test_missing_year_refetches_the_whole_history_under_one_batch(yahoo):
    fake, store = yahoo
    fetch_ohlcv("AAPL", "2019-01-01", "2021-01-01")   # 2019–2020
    fetch_ohlcv("AAPL", "2022-01-01", "2023-01-01")   # 2022 missing
    # The second download spans everything the ticker has, not just 2022.
    assert fake.calls[-1] == ("AAPL", "2019-01-01", "2023-01-01")
    docs = store.get_many("AAPL", [2019, 2020, 2021, 2022])
    assert len(docs) == 4
    assert len({d["batch"] for d in docs.values()}) == 1


def test_mixed_batches_are_not_stitched(yahoo):
    """The correctness rule: adjusted closes from two downloads never meet."""
    fake, store = yahoo
    fetch_ohlcv("AAPL", "2019-01-01", "2021-01-01")
    # Corrupt one year's batch id to simulate a stale neighbour.
    doc = store.get_many("AAPL", [2020])[2020]
    doc["batch"] = "older"
    store.put_many([doc])
    data._cache.clear()
    df = fetch_ohlcv("AAPL", "2019-01-01", "2021-01-01")
    assert df.attrs["data_source"] == "yfinance"
    assert len(fake.calls) == 2


def test_partial_year_expires_after_ttl(yahoo, monkeypatch):
    fake, store = yahoo
    fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01")   # current year, partial
    assert store.get_many("AAPL", [2026])[2026]["complete"] is False
    data._cache.clear()
    later = NOW + data.PARTIAL_YEAR_TTL + timedelta(minutes=1)
    monkeypatch.setattr(data, "_now", lambda: later)
    df = fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01")
    assert df.attrs["data_source"] == "yfinance"
    assert len(fake.calls) == 2


def test_complete_year_never_expires(yahoo, monkeypatch):
    fake, _ = yahoo
    fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    data._cache.clear()
    monkeypatch.setattr(data, "_now", lambda: NOW + timedelta(days=400))
    assert fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01").attrs["data_source"] == "cache"
    assert len(fake.calls) == 1


# ── failure paths ───────────────────────────────────────────────────────────

def test_yahoo_outage_serves_the_cached_span_as_stale(yahoo, monkeypatch):
    fake, _ = yahoo
    fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01")
    data._cache.clear()
    fake.fail = ConnectionError("rate limited")
    # Past the TTL, so a refresh is attempted — and fails.
    monkeypatch.setattr(data, "_now", lambda: NOW + timedelta(days=1))
    df = fetch_ohlcv("AAPL", "2026-01-01", "2026-09-01")
    assert df.attrs["data_source"] == "cache-stale"
    assert not df.empty


def test_yahoo_outage_with_nothing_cached_is_503_shaped(yahoo):
    fake, _ = yahoo
    fake.fail = ConnectionError("down")
    with pytest.raises(DataUnavailableError):
        fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")


def test_unknown_symbol_is_still_a_value_error(yahoo):
    fake, store = yahoo
    fake.empty = True
    with pytest.raises(ValueError, match="No data found for NOPE"):
        fetch_ohlcv("NOPE", "2020-01-01", "2021-01-01")
    assert store.years_for("NOPE") == []


def test_listing_younger_than_start_runs_on_the_bars_that_exist(yahoo):
    fake, store = yahoo
    fake.listed_from = "2021-01-04"
    df = fetch_ohlcv("NEW", "2019-01-01", "2022-01-01")
    assert df.index.min() >= pd.Timestamp("2021-01-04")
    # The empty years are recorded, so the next read is a cache hit — not a
    # perpetual refetch of a hole.
    docs = store.get_many("NEW", [2019, 2020, 2021])
    assert docs[2019]["dates"] == [] and docs[2020]["dates"] == []
    data._cache.clear()
    assert fetch_ohlcv("NEW", "2019-01-01", "2022-01-01").attrs["data_source"] == "cache"
    assert len(fake.calls) == 1


def test_request_entirely_before_listing_is_no_data(yahoo):
    fake, _ = yahoo
    fake.listed_from = "2021-01-04"
    with pytest.raises(ValueError, match="No data found"):
        fetch_ohlcv("NEW", "2019-01-01", "2020-01-01")


# ── store selection ─────────────────────────────────────────────────────────

def test_store_falls_back_to_memory_without_credentials(monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    data.configure_store(None)
    assert isinstance(data._get_store(), MemoryPriceStore)
    data.configure_store(None)


def test_store_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("PRICE_CACHE", "off")
    data.configure_store(None)
    assert isinstance(data._get_store(), MemoryPriceStore)
    data.configure_store(None)
