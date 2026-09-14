"""OHLCV data: yfinance behind two cache tiers.

    L1  module dict, keyed (ticker, start, end)     — this process only
    L2  one Firestore doc per (ticker, year)         — survives cold starts
    L3  yfinance                                     — the flaky one

The L2 rule that matters: **every cached year of a ticker comes from the same
download.** yfinance returns *adjusted* prices, and the adjustment is as of
the day you fetch — a dividend or split after 2019 was cached rewrites every
2019 close the next time it is downloaded. Stitching a 2019 cached in June to
a 2024 fetched in September puts a phantom jump at the boundary, and a 4:1
split in between puts a 4x one. So when any year in a request is missing or
stale, the whole cached history of that ticker is re-downloaded in one call
and rewritten under a new batch id; a read is served from L2 only when every
year it needs shares that id.

Stale-on-error: if yfinance raises and L2 holds a uniform-batch copy of the
span, that copy is served with `data_source = "cache-stale"`. Bad tickers
still surface as a ValueError the way they always have — yfinance returns an
empty frame for both a typo and an outage, and the two cannot be told apart.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from price_store import COLUMNS, MemoryPriceStore, PriceStore, doc_to_frame, frame_to_doc

log = logging.getLogger("finertia.data")

# A year still in progress is re-downloaded once it is this old. Daily bars
# change once a day; six hours means an instance that woke at the open sees
# the close by the evening without hammering Yahoo on every request.
PARTIAL_YEAR_TTL = timedelta(hours=6)

_cache: dict = {}
_store: PriceStore | None = None


class DataUnavailableError(Exception):
    """yfinance failed and there is nothing cached to fall back on."""


def configure_store(store: PriceStore | None) -> None:
    """Swap the L2 store — tests pass a MemoryPriceStore, None resets to lazy."""
    global _store
    _store = store


def _get_store() -> PriceStore:
    global _store
    if _store is None:
        # Firestore only when credentials exist and the cache is not switched
        # off. A dev machine without a service account keeps working; it just
        # loses the second tier and behaves exactly as it did before.
        if os.environ.get("PRICE_CACHE", "on").lower() != "off" and os.environ.get(
            "FIREBASE_SERVICE_ACCOUNT_JSON"
        ):
            from price_store import FirestorePriceStore  # noqa: PLC0415

            _store = FirestorePriceStore()
        else:
            _store = MemoryPriceStore()
    return _store


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _download(ticker: str, start: str, end: str) -> pd.DataFrame:
    """One yfinance call, normalised. Raises on transport errors, returns an
    empty frame when Yahoo has nothing for the symbol."""
    import yfinance as yf  # noqa: PLC0415 — keep import cost off the test path

    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        return df
    # Flatten MultiIndex columns if present (yfinance >=0.2 returns MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[COLUMNS].dropna()


def _years_in(start: str, end: str) -> list[int]:
    # yfinance's `end` is exclusive, so a request ending 2024-01-01 needs no
    # 2024 bars at all.
    first = pd.Timestamp(start).year
    last = (pd.Timestamp(end) - pd.Timedelta(days=1)).year
    return list(range(first, max(first, last) + 1))


def _uniform(docs: dict[int, dict], years: list[int], *, now: datetime, fresh: bool) -> bool:
    """True when every year is present, from one batch, and (if `fresh`) any
    partial year is inside its TTL."""
    if any(y not in docs for y in years):
        return False
    batches = {docs[y]["batch"] for y in years}
    if len(batches) != 1:
        return False
    if fresh:
        for y in years:
            d = docs[y]
            if not d["complete"]:
                fetched = datetime.fromisoformat(d["fetched_at"])
                if now - fetched > PARTIAL_YEAR_TTL:
                    return False
    return True


def _assemble(docs: dict[int, dict], years: list[int], start: str, end: str) -> pd.DataFrame:
    frames = [doc_to_frame(docs[y]) for y in years]
    df = pd.concat(frames).sort_index()
    return df[(df.index >= pd.Timestamp(start)) & (df.index < pd.Timestamp(end))]


def _refresh(store: PriceStore, ticker: str, years: list[int], *, now: datetime) -> dict[int, dict]:
    """Re-download the union of the requested span and everything already
    cached for this ticker, and rewrite it all under one batch id."""
    known = store.years_for(ticker)
    span = sorted(set(years) | set(known))
    lo, hi = span[0], span[-1]
    # A span with a gap in the middle is still one download — Yahoo returns
    # whatever it has and the missing years simply produce no doc.
    df = _download(ticker, f"{lo}-01-01", f"{hi + 1}-01-01")
    if df.empty:
        raise ValueError(f"No data found for {ticker}")

    batch = now.isoformat(timespec="seconds")
    by_year = {int(y): f for y, f in df.groupby(df.index.year)}
    docs = []
    # Every year in the span gets a doc, even an empty one. A listing younger
    # than the start date, or a symbol delisted before the end, is then a
    # known-empty year rather than a hole that reads as "not cached" — the
    # backtest runs on the bars that exist, which is what it always did.
    for year in range(lo, hi + 1):
        frame = by_year.get(year, df.iloc[0:0])
        docs.append(
            frame_to_doc(
                ticker,
                year,
                frame,
                batch=batch,
                complete=year < now.year,
                fetched_at=batch,
            )
        )
    store.put_many(docs)
    return {d["year"]: d for d in docs}


def fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """OHLCV for ticker in [start, end). The frame's `.attrs["data_source"]`
    says where it came from: "memory", "cache", "yfinance" or "cache-stale"."""
    ticker = ticker.upper()
    key = (ticker, start, end)
    if key in _cache:
        df = _cache[key]
        df.attrs["data_source"] = "memory"
        return df

    store = _get_store()
    years = _years_in(start, end)
    now = _now()
    docs = store.get_many(ticker, years)

    if _uniform(docs, years, now=now, fresh=True):
        df = _assemble(docs, years, start, end)
        source = "cache"
    else:
        try:
            docs = _refresh(store, ticker, years, now=now)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 — anything transport-shaped
            if _uniform(docs, years, now=now, fresh=False):
                log.warning("yfinance failed for %s (%s); serving cached span", ticker, exc)
                df = _assemble(docs, years, start, end)
                source = "cache-stale"
            else:
                raise DataUnavailableError(
                    f"Could not download prices for {ticker} and nothing is cached for this range."
                ) from exc
        else:
            df = _assemble(docs, years, start, end)
            source = "yfinance"

    if df.empty:
        raise ValueError(f"No data found for {ticker}")

    df.attrs["data_source"] = source
    _cache[key] = df
    return df
