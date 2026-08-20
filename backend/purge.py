"""Purging and embargoing at the walk-forward split boundary.

`walk_forward` cuts the period at one point: everything before it selects the
parameters, everything after it scores them. The two halves touch, and that
contact leaks.

The leak is the trade that straddles the cut. A position opened before the
split and still open after it earns in both halves off the same price move.
The in-sample half counts that move as evidence for choosing those parameters;
the out-of-sample half then counts the rest of the same move as independent
confirmation. It is not independent. It is the same trade, paid twice.

Measured on five years of daily bars, the momentum grid's boundary position had
already been held for up to 33 bars and continued for up to 12 more — so the
overlap is not a rounding error at the scale these strategies trade at.

The standard fix (Lopez de Prado, *Advances in Financial Machine Learning*, ch.
7) is a gap:

  purge    Drop the last `gap` bars before the split from the SELECTION window,
           so no candidate can be chosen for a trade the other half also pays.

  embargo  Drop the first `gap` bars after the split from the SCORING window,
           so the out-of-sample number is not the tail of a trade the selection
           was already rewarded for.

Both sides matter and both are the same length here, so the result is a clean
dead zone of `2 * gap` bars that neither half sees.

Sizing the gap is a judgement call, stated plainly rather than hidden:

  * The base is 1% of the period, Lopez de Prado's rule of thumb.
  * Floored at 5 bars, because 1% of a one-year request is three days — shorter
    than these strategies hold a position, so it would not clear the straddle
    it exists to clear.
  * Capped at 25 bars, because past about a month the gap costs more
    out-of-sample data than the bias it removes. A candidate that holds one
    position for months still straddles further back than the cap reaches;
    that residual is disclosed in the result rather than papered over.

Errors run toward keeping the gap, not toward keeping data: the gap is only
shortened when honouring it would leave a half too small to measure, and that
shortening is reported.
"""

from __future__ import annotations

import math

# Lopez de Prado's rule of thumb for the embargo, as a share of the sample.
EMBARGO_PCT = 0.01

MIN_GAP_BARS = 5
MAX_GAP_BARS = 25

# Below this a Sharpe ratio is not worth quoting. Matches the floor
# `walk_forward` already applies to each half before it will split at all.
MIN_HALF_BARS = 30


def purged_split(
    n: int,
    split_at: int,
    embargo_pct: float = EMBARGO_PCT,
    min_gap: int = MIN_GAP_BARS,
    max_gap: int = MAX_GAP_BARS,
    min_half: int = MIN_HALF_BARS,
) -> dict:
    """Work out where the in-sample window ends and the out-of-sample one starts.

    Returns the two boundaries plus everything needed to explain them, so the
    caller never has to re-derive the arithmetic to describe it to a user.

    `is_end` is exclusive, `oos_start` inclusive. Bars in between belong to
    neither half.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 < split_at < n:
        raise ValueError("split_at must fall strictly inside the series")

    requested = int(min(max(math.ceil(embargo_pct * n), min_gap), max_gap))

    # Room available on each side before a half drops under the floor. The gap
    # is symmetric, so it is limited by whichever side has less to spare.
    room = min(split_at - min_half, (n - split_at) - min_half)
    gap = max(0, min(requested, room))

    return {
        "is_end": split_at - gap,
        "oos_start": split_at + gap,
        "purge_bars": gap,
        "embargo_bars": gap,
        "requested_gap": requested,
        # True when the period was too short to afford the full gap, which
        # means some boundary contamination is still in the numbers.
        "shortened": gap < requested,
        "applied": gap > 0,
    }
