"""The workspace's Indian ticker suggestions are the index scan's own lists.

frontend/src/lib/indianTickers.json is a hand-named copy of the Nifty 50 and
Nifty Next 50 symbols in backend/universes. When those lists are refreshed,
this fails until the suggestions are too, so the two never disagree.
"""

import json
from pathlib import Path

import universes

COPY = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "indianTickers.json"


def test_the_suggestions_are_the_nifty_lists():
    rows = json.loads(COPY.read_text())["tickers"]
    symbols = [r["symbol"] for r in rows]
    assert len(symbols) == len(set(symbols))
    expected = set(universes.load("nifty50")["tickers"]) | set(universes.load("niftynext50")["tickers"])
    assert set(symbols) == expected
    assert all(r["name"].strip() for r in rows)
