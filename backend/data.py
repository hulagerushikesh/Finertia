"""OHLCV data: a price provider behind two cache tiers.

    L1  bounded in-process LRU, keyed (ticker, start, end) — this process only
    L2  one Firestore doc per (ticker, year)         — survives cold starts
    L3  the provider (price_providers.py; yfinance today) — the flaky one

L2 docs record which provider wrote them, and a read is served from L2 only
when they are all the current provider's: switching vendors refetches each
ticker on first use instead of splicing two vendors' adjustments together.

The L2 rule that matters: **every cached year of a ticker comes from the same
download.** yfinance returns *adjusted* prices, and the adjustment is as of
the day you fetch — a dividend or split after 2019 was cached rewrites every
2019 close the next time it is downloaded. Stitching a 2019 cached in June to
a 2024 fetched in September puts a phantom jump at the boundary, and a 4:1
split in between puts a 4x one. So when any year in a request is missing or
stale, the whole cached history of that ticker is re-downloaded in one call
and rewritten under a new batch id; a read is served from L2 only when every
year it needs shares that id.

L1 holds at most L1_MAX_ENTRIES frames and drops each after L1_TTL. It used
to be a plain dict that only grew: every new date range was a new entry for
the life of a 512 MiB instance, and an entry never noticed the six-hour rule
that L2 keeps for the current year.

One fetch per ticker at a time: requests run in worker threads, so ten users
opening the same uncached ticker would otherwise make ten provider downloads
and ten rewrites of its L2 docs. The first takes the ticker's lock and fills
the caches; the rest wait, then find it there.

Stale-on-error: if yfinance raises and L2 holds a uniform-batch copy of the
span, that copy is served with `data_source = "cache-stale"`. Bad tickers
still surface as a ValueError the way they always have — yfinance returns an
empty frame for both a typo and an outage, and the two cannot be told apart.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import pandas as pd

from price_providers import get_provider
from price_store import MemoryPriceStore, PriceStore, doc_to_frame, frame_to_doc
from timing import step

log = logging.getLogger("finertia.data")

# A year still in progress is re-downloaded once it is this old. Daily bars
# change once a day; six hours means an instance that woke at the open sees
# the close by the evening without hammering Yahoo on every request.
PARTIAL_YEAR_TTL = timedelta(hours=6)

# A backtest frame is ~10 years of daily bars, roughly 100-200 KB, so 200 of
# them stay well inside the instance's memory next to the requests in flight.
L1_MAX_ENTRIES = 200
L1_TTL = PARTIAL_YEAR_TTL


class _MemoryCache:
    """A thread-safe LRU with a time to live. `clock` is swappable for tests."""

    def __init__(self, max_entries: int, ttl_seconds: float, clock=time.monotonic):
        self.max_entries, self.ttl, self.clock = max_entries, ttl_seconds, clock
        self._items: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            df, stored = item
            if self.clock() - stored > self.ttl:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return df

    def put(self, key, df) -> None:
        with self._lock:
            self._items[key] = (df, self.clock())
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __contains__(self, key) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


_cache = _MemoryCache(L1_MAX_ENTRIES, L1_TTL.total_seconds())
_store: PriceStore | None = None

# One lock per ticker, for single-flight fetches. One small object per
# distinct ticker ever requested on this instance; not worth evicting.
_ticker_locks: dict[str, threading.Lock] = {}
_ticker_locks_guard = threading.Lock()


def _ticker_lock(ticker: str) -> threading.Lock:
    with _ticker_locks_guard:
        return _ticker_locks.setdefault(ticker, threading.Lock())


class DataUnavailableError(Exception):
    """The provider failed and there is nothing cached to fall back on."""


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
        # The emulator counts as credentials: end-to-end tests seed prices
        # there so a run never reaches Yahoo.
        has_firestore = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get(
            "FIRESTORE_EMULATOR_HOST"
        )
        if os.environ.get("PRICE_CACHE", "on").lower() != "off" and has_firestore:
            from price_store import FirestorePriceStore  # noqa: PLC0415

            _store = FirestorePriceStore()
        else:
            _store = MemoryPriceStore()
    return _store


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _download(ticker: str, start: str, end: str) -> pd.DataFrame:
    """One provider call. Raises on transport errors, returns an empty frame
    when the provider has nothing for the symbol."""
    return get_provider().download(ticker, start, end)


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
    provider = get_provider().name
    if any(docs[y].get("provider", "yfinance") != provider for y in years):
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
    with step("prices_read"):
        known = store.years_for(ticker)
    span = sorted(set(years) | set(known))
    lo, hi = span[0], span[-1]
    # A span with a gap in the middle is still one download — Yahoo returns
    # whatever it has and the missing years simply produce no doc.
    with step("prices_fetch"):
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
                provider=get_provider().name,
            )
        )
    with step("prices_write"):
        store.put_many(docs)
    return {d["year"]: d for d in docs}


def fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """OHLCV for ticker in [start, end). The frame's `.attrs["data_source"]`
    says where it came from: "memory", "cache", "cache-stale", or the
    provider's name ("yfinance") for a fresh download."""
    ticker = ticker.upper()
    key = (ticker, start, end)
    hit = _from_memory(key)
    if hit is not None:
        return hit

    lock = _ticker_lock(ticker)
    # Normally ~0; long when another request is downloading this ticker.
    with step("prices_wait"):
        lock.acquire()
    try:
        # Whoever held the lock may have just fetched this exact range.
        hit = _from_memory(key)
        if hit is not None:
            return hit
        return _fetch_through_store(ticker, start, end, key)
    finally:
        lock.release()


def _from_memory(key) -> pd.DataFrame | None:
    """The cached frame, as a shallow copy labelled "memory". A copy, so that
    labelling it cannot change the source another request is reading."""
    df = _cache.get(key)
    if df is None:
        return None
    out = df.copy(deep=False)
    out.attrs = {**df.attrs, "data_source": "memory"}
    return out


def _fetch_through_store(ticker: str, start: str, end: str, key) -> pd.DataFrame:
    store = _get_store()
    years = _years_in(start, end)
    now = _now()
    with step("prices_read"):
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
                log.warning("%s failed for %s (%s); serving cached span", get_provider().name, ticker, exc)
                df = _assemble(docs, years, start, end)
                source = "cache-stale"
            else:
                raise DataUnavailableError(
                    f"Could not download prices for {ticker} and nothing is cached for this range."
                ) from exc
        else:
            df = _assemble(docs, years, start, end)
            source = get_provider().name

    if df.empty:
        raise ValueError(f"No data found for {ticker}")

    df.attrs["data_source"] = source
    _cache.put(key, df)
    return df
