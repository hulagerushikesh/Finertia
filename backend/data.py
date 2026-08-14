"""OHLCV data fetching and in-memory caching via yfinance."""

import yfinance as yf
import pandas as pd

_cache: dict = {}


def fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download OHLCV data for ticker between start and end dates, with caching."""
    key = (ticker.upper(), start, end)
    if key in _cache:
        return _cache[key]

    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"No data found for {ticker}")

    # Flatten MultiIndex columns if present (yfinance >=0.2 returns MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    _cache[key] = df
    return df
