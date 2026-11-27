"""In-process cache of finished backtest results (planning/LOAD-TEST.md).

A backtest is deterministic: the same request on the same prices gives the
same answer, down to the bootstrap intervals, whose seeds come from the
request. A cache hit skips about 0.3 s of CPU, nearly all of a request's cost,
and the JSON is already rendered.

What the key covers, so a hit can never be wrong:
  - every field of the request (the whole validated model, not a hand-picked
    subset that could miss a new parameter);
  - the prices themselves: a hash of every close and every date. If Yahoo
    revises a price, or a day is added, the key changes. Nothing has to be
    invalidated by hand;
  - the code: the cache lives in the process, so a deploy starts it empty.

Values are the rendered JSON bytes (about 420 KB for 10 years), held under a
byte budget, least recently used out first. Python dicts of the same result
take several times the memory, which a 512 MiB instance cannot spare.
"""

import hashlib
import json
import os
import threading
from collections import OrderedDict

import numpy as np
import pandas as pd


def request_key(fields: dict, close: pd.Series) -> str:
    """The cache key for one request on one price series."""
    h = hashlib.sha256()
    h.update(json.dumps(fields, sort_keys=True, default=str).encode())
    h.update(b"|")
    h.update(np.ascontiguousarray(close.to_numpy(dtype=np.float64)).tobytes())
    h.update(np.ascontiguousarray(close.index.asi8).tobytes())
    return h.hexdigest()


class ByteLRU:
    """A thread-safe LRU of bytes values with a total size budget."""

    def __init__(self, max_bytes: int):
        self.max_bytes = max(0, int(max_bytes))
        self._items: OrderedDict[str, tuple[bytes, dict]] = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        """(body, extra) or None."""
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self.misses += 1
                return None
            self._items.move_to_end(key)
            self.hits += 1
            return item

    def put(self, key: str, body: bytes, extra: dict) -> None:
        size = len(body)
        if size > self.max_bytes:
            return  # larger than the whole budget: never worth evicting for
        with self._lock:
            old = self._items.pop(key, None)
            if old is not None:
                self._bytes -= len(old[0])
            self._items[key] = (body, extra)
            self._bytes += size
            while self._bytes > self.max_bytes:
                _, (evicted, _) = self._items.popitem(last=False)
                self._bytes -= len(evicted)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bytes = 0
            self.hits = self.misses = 0

    def stats(self) -> dict:
        with self._lock:
            return {"entries": len(self._items), "bytes": self._bytes, "max_bytes": self.max_bytes,
                    "hits": self.hits, "misses": self.misses}


def _budget_bytes() -> int:
    raw = os.environ.get("RESULT_CACHE_MB", "64")
    try:
        return max(0, int(float(raw) * 1024 * 1024))
    except ValueError:
        return 64 * 1024 * 1024


# One per process. RESULT_CACHE_MB=0 switches it off.
backtests = ByteLRU(_budget_bytes())
