"""The provider seam (price_providers.py) and how data.py's cache respects it.

The cache must never splice two vendors' bars into one series, and must not
refetch the whole existing cache on the deploy that introduces the field."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import data
import price_providers
from data import DataUnavailableError, fetch_ohlcv
from price_providers import YahooProvider, get_provider
from price_store import COLUMNS, frame_to_doc
from tests.test_data import NOW, _bars, yahoo  # noqa: F401 — the fixture


def _use(monkeypatch, name):
    monkeypatch.setattr(price_providers, "_provider", SimpleNamespace(name=name, download=None))


# ── choosing a provider ─────────────────────────────────────────────────────

def test_default_is_yfinance(monkeypatch):
    monkeypatch.delenv("PRICE_PROVIDER", raising=False)
    monkeypatch.setattr(price_providers, "_provider", None)
    assert isinstance(get_provider(), YahooProvider)
    assert get_provider().name == "yfinance"


def test_name_is_case_and_space_insensitive(monkeypatch):
    monkeypatch.setenv("PRICE_PROVIDER", "  YFinance ")
    monkeypatch.setattr(price_providers, "_provider", None)
    assert get_provider().name == "yfinance"


def test_unknown_provider_refuses_rather_than_falling_back(monkeypatch):
    """Silently serving Yahoo while the operator thinks a licensed feed is on
    is the failure this seam must not have."""
    monkeypatch.setenv("PRICE_PROVIDER", "eodhd-typo")
    monkeypatch.setattr(price_providers, "_provider", None)
    with pytest.raises(ValueError, match="eodhd-typo"):
        get_provider()


# ── the cache keeps vendors apart ───────────────────────────────────────────

def test_cached_docs_name_their_provider(yahoo):
    _, store = yahoo
    fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    assert store.get_many("AAPL", [2020])[2020]["provider"] == "yfinance"


def test_docs_from_before_the_field_are_yfinance_and_still_hit(yahoo):
    """The deploy that adds `provider` must not refetch every cached ticker."""
    fake, store = yahoo
    doc = frame_to_doc("AAPL", 2020, _bars("2020-01-01", "2021-01-01"), batch="b", complete=True, fetched_at="t")
    del doc["provider"]
    store.put_many([doc])
    df = fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    assert df.attrs["data_source"] == "cache"
    assert fake.calls == []


def test_switching_provider_refetches_instead_of_splicing(yahoo, monkeypatch):
    fake, store = yahoo
    fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    data._cache.clear()

    _use(monkeypatch, "licensed")
    df = fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    assert df.attrs["data_source"] == "licensed"
    assert len(fake.calls) == 2
    assert store.get_many("AAPL", [2020])[2020]["provider"] == "licensed"

    data._cache.clear()
    assert fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01").attrs["data_source"] == "cache"
    assert len(fake.calls) == 2


def test_new_provider_down_does_not_serve_the_old_vendors_bars(yahoo, monkeypatch):
    """Stale-on-error is for the same vendor's last good copy. Falling back to
    unlicensed Yahoo bars after switching to a licensed feed would defeat the
    switch."""
    fake, _ = yahoo
    fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")
    data._cache.clear()

    _use(monkeypatch, "licensed")
    fake.fail = ConnectionError("down")
    with pytest.raises(DataUnavailableError):
        fetch_ohlcv("AAPL", "2020-01-01", "2021-01-01")


# ── YahooProvider normalises what yfinance returns ──────────────────────────

def test_yahoo_provider_normalises_the_frame(monkeypatch):
    import yfinance

    idx = pd.date_range("2024-01-02", periods=3, freq="B", tz="America/New_York")
    raw = pd.DataFrame(
        {
            ("Close", "AAPL"): [1.0, np.nan, 3.0],
            ("High", "AAPL"): [1.1, 2.1, 3.1],
            ("Low", "AAPL"): [0.9, 1.9, 2.9],
            ("Open", "AAPL"): [1.0, 2.0, 3.0],
            ("Volume", "AAPL"): [10.0, 20.0, 30.0],
        },
        index=idx,
    )
    seen = {}

    def fake_download(ticker, **kw):
        seen.update(kw, ticker=ticker)
        return raw.copy()

    monkeypatch.setattr(yfinance, "download", fake_download)
    df = YahooProvider().download("AAPL", "2024-01-01", "2024-01-06")

    assert list(df.columns) == COLUMNS
    assert df.index.tz is None
    assert len(df) == 2  # the NaN row is dropped
    assert seen["auto_adjust"] is True  # adjusted prices: the contract data.py relies on
    assert (seen["start"], seen["end"]) == ("2024-01-01", "2024-01-06")


def test_yahoo_provider_passes_an_empty_frame_through(monkeypatch):
    import yfinance

    monkeypatch.setattr(yfinance, "download", lambda *a, **k: pd.DataFrame())
    assert YahooProvider().download("NOPE", "2024-01-01", "2024-02-01").empty
