"""Where daily prices come from — one module per vendor, chosen by config.

yfinance is the only provider today, and it is not licensed for commercial
use (ROADMAP, M12): a paid Finertia needs a licensed end-of-day feed. This
module is the seam that makes that switch one new class plus one env var,
with the cache, the routes and the engine untouched.

A provider's contract, which data.py relies on:

- `download(ticker, start, end)` returns daily bars for [start, end): `end`
  is exclusive. Columns exactly `COLUMNS`, a tz-naive DatetimeIndex, no NaN
  rows. Prices **adjusted** for splits and dividends, as of the day of the
  call (data.py's single-batch rule exists because of that).
- An unknown symbol returns an **empty frame**; a transport failure
  **raises**. data.py turns the first into "No data found" and serves the
  stale cache for the second.
- `ticker` is the symbol as users type it today, in Yahoo's conventions
  (`RELIANCE.NS`, `BRK-B`, `^GSPC`). A provider with other symbology maps it
  inside `download`; nothing upstream changes.
- `name` is stored on every cached price doc, so bars from two vendors are
  never stitched into one series.
"""

from __future__ import annotations

import os
from typing import Protocol

import pandas as pd

from price_store import COLUMNS

DEFAULT_PROVIDER = "yfinance"


class PriceProvider(Protocol):
    name: str

    def download(self, ticker: str, start: str, end: str) -> pd.DataFrame: ...


class YahooProvider:
    """Yahoo Finance through yfinance. Free, unlicensed for commercial use."""

    name = "yfinance"

    def download(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        import yfinance as yf  # noqa: PLC0415 — keep import cost off the test path

        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty:
            return df
        # Flatten MultiIndex columns if present (yfinance >=0.2 returns MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[COLUMNS].dropna()


PROVIDERS: dict[str, type] = {YahooProvider.name: YahooProvider}

_provider: PriceProvider | None = None


def get_provider() -> PriceProvider:
    """The provider named by PRICE_PROVIDER (default yfinance), built once.

    An unknown name raises rather than falling back: serving Yahoo prices
    while the operator believes a licensed feed is on is the one failure this
    module must not have.
    """
    global _provider
    if _provider is None:
        name = os.environ.get("PRICE_PROVIDER", DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER
        if name not in PROVIDERS:
            raise ValueError(f"PRICE_PROVIDER={name!r} is not one of {sorted(PROVIDERS)}")
        _provider = PROVIDERS[name]()
    return _provider


def reset_provider() -> None:
    """Forget the built provider, so the next call re-reads PRICE_PROVIDER. Tests."""
    global _provider
    _provider = None
