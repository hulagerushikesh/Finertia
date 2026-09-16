"""Where a year of prices lives between requests.

Cloud Run runs at min-instances 0, so the in-memory dict in data.py is empty
on every scale-from-zero and each first request pays a yfinance round trip —
and yfinance is the flakiest dependency the product has. This is the second
tier: one Firestore document per (ticker, year), read through the Admin SDK,
so a cold instance can serve a five-year backtest without touching Yahoo.

Two stores share one interface. `MemoryPriceStore` is what tests and a
credential-less dev machine get; `FirestorePriceStore` is production. data.py
never imports firebase itself, which keeps it importable and testable with no
credentials in the environment.

The document shape is columnar — parallel arrays, one per OHLCV column — so a
year of daily bars is ~15 kB, well under Firestore's 1 MB ceiling and cheap
to read as a single fetch.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

COLLECTION = "prices"
COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def doc_id(ticker: str, year: int) -> str:
    # Firestore forbids "/" in an id; every other character a Yahoo symbol
    # uses (^, -, =, .) is allowed as-is.
    return f"{ticker.upper().replace('/', '_')}_{year}"


def frame_to_doc(ticker: str, year: int, frame: pd.DataFrame, *, batch: str,
                 complete: bool, fetched_at: str) -> dict:
    """Serialise one year's bars. Dates as ISO strings, columns as plain lists."""
    return {
        "ticker": ticker.upper(),
        "year": year,
        "batch": batch,
        "complete": complete,
        "fetched_at": fetched_at,
        "dates": [d.strftime("%Y-%m-%d") for d in frame.index],
        **{c.lower(): [float(v) for v in frame[c].tolist()] for c in COLUMNS},
    }


def doc_to_frame(doc: dict) -> pd.DataFrame:
    frame = pd.DataFrame(
        {c: doc[c.lower()] for c in COLUMNS},
        index=pd.to_datetime(doc["dates"]),
    )
    frame.index.name = "Date"
    return frame


class PriceStore(Protocol):
    def get_many(self, ticker: str, years: list[int]) -> dict[int, dict]:
        """Return {year: doc} for every year that exists; missing years absent."""

    def put_many(self, docs: list[dict]) -> None: ...

    def years_for(self, ticker: str) -> list[int]:
        """Every year cached for this ticker, in any batch."""


class MemoryPriceStore:
    """Dict-backed store. Process-local, so it behaves exactly like having no
    second tier — which is the right behaviour for tests and local dev."""

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    def get_many(self, ticker: str, years: list[int]) -> dict[int, dict]:
        out = {}
        for y in years:
            d = self._docs.get(doc_id(ticker, y))
            if d is not None:
                out[y] = d
        return out

    def put_many(self, docs: list[dict]) -> None:
        for d in docs:
            self._docs[doc_id(d["ticker"], d["year"])] = d

    def years_for(self, ticker: str) -> list[int]:
        t = ticker.upper()
        return sorted(d["year"] for d in self._docs.values() if d["ticker"] == t)

    def clear(self) -> None:
        self._docs.clear()


class FirestorePriceStore:
    """Production store. Imports firebase lazily so the module — and data.py —
    stay importable without credentials."""

    def __init__(self) -> None:
        from firebase_admin_init import get_db  # noqa: PLC0415 — deliberate

        self._db = get_db()
        self._col = self._db.collection(COLLECTION)

    def get_many(self, ticker: str, years: list[int]) -> dict[int, dict]:
        refs = [self._col.document(doc_id(ticker, y)) for y in years]
        out = {}
        # get_all is one round trip for the whole span, not one per year.
        for snap in self._db.get_all(refs):
            if snap.exists:
                d = snap.to_dict()
                out[int(d["year"])] = d
        return out

    def put_many(self, docs: list[dict]) -> None:
        batch = self._db.batch()
        for d in docs:
            batch.set(self._col.document(doc_id(d["ticker"], d["year"])), d)
        batch.commit()

    def years_for(self, ticker: str) -> list[int]:
        # Single-field equality needs no composite index. Only the year field
        # is read back, so listing a ticker with thirty cached years is cheap.
        from google.cloud.firestore_v1.base_query import FieldFilter  # noqa: PLC0415

        q = self._col.where(filter=FieldFilter("ticker", "==", ticker.upper())).select(["year"])
        return sorted(int(s.get("year")) for s in q.stream())
