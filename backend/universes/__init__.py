"""The tracked universe: the index lists the nightly price load keeps fresh.

One JSON file per index, each naming its source and the date it was taken.
Index membership changes a few times a year; the lists are refreshed by hand
(see each file's `source`), not scraped at run time, so the nightly load
never depends on a page that can move.

Symbols are Yahoo's: "BRK-B" not "BRK.B", and ".NS" on every NSE listing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ("sp500", "nasdaq100", "nifty50", "niftynext50")


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    if name not in NAMES:
        raise ValueError(f"Unknown universe '{name}'. Choose one of: {', '.join(NAMES)}.")
    return json.loads((HERE / f"{name}.json").read_text())


def tickers(*names: str) -> list[str]:
    """Union of the named universes (all of them when none is named), sorted."""
    out: set[str] = set()
    for n in names or NAMES:
        out.update(load(n)["tickers"])
    return sorted(out)


@lru_cache(maxsize=1)
def _tracked() -> frozenset[str]:
    return frozenset(tickers())


def is_tracked(ticker: str) -> bool:
    return ticker.upper() in _tracked()
