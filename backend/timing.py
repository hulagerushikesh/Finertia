"""Per-request step timings: where a request's time goes.

The request log line already has the total. This adds the parts that are
waiting rather than computing (the token check, each Firestore round trip,
the price provider), so a slow request can be read as "0.3 s of maths and
1.2 s of database" instead of guessed at.

The middleware opens a collector for each request; code anywhere below it
wraps a step in `with step("name"):`. Outside a request (scripts, unit tests
calling a function directly) there is no collector and `step` costs nothing.

The same numbers go out as a `Server-Timing` header, so the browser's network
panel shows them next to the request. Step names only, never data.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar

# name -> [total milliseconds, times entered]. A dict rather than a fresh
# object per step so a step run in a worker thread (which gets a copy of the
# context) still adds to the same collector.
_current: ContextVar[dict | None] = ContextVar("finertia_timings", default=None)


def begin() -> dict:
    """Open a collector for the current request and return it."""
    steps: dict = {}
    _current.set(steps)
    return steps


@contextmanager
def step(name: str):
    """Time the enclosed block under `name`. Repeated names add up."""
    steps = _current.get()
    if steps is None:
        yield
        return
    started = time.perf_counter()
    try:
        yield
    finally:
        entry = steps.setdefault(name, [0.0, 0])
        entry[0] += (time.perf_counter() - started) * 1000
        entry[1] += 1


def as_log_fields(steps: dict) -> dict:
    """`timings_ms` per step, and `timing_counts` for the steps that ran more
    than once (a portfolio fetches prices once per ticker)."""
    fields = {"timings_ms": {name: round(ms, 1) for name, (ms, _) in steps.items()}}
    counts = {name: n for name, (_, n) in steps.items() if n > 1}
    if counts:
        fields["timing_counts"] = counts
    return fields


def server_timing(steps: dict, total_ms: float) -> str:
    """The `Server-Timing` header value: each step, then the total, then
    `other`, the part outside any named step (mostly the computation)."""
    parts = []
    for name, (ms, n) in steps.items():
        desc = f';desc="x{n}"' if n > 1 else ""
        parts.append(f"{name};dur={ms:.1f}{desc}")
    named = sum(ms for ms, _ in steps.values())
    parts.append(f"other;dur={max(0.0, total_ms - named):.1f}")
    parts.append(f"total;dur={total_ms:.1f}")
    return ", ".join(parts)
