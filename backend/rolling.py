"""Rolling (anchored) walk-forward — the verdict as a distribution, not a draw.

`validation.walk_forward` splits the period once, at 70%, and reports the
winner's out-of-sample Sharpe. That is one draw. On AAPL 2018→2024-01-01 the
draw says momentum fails and Bollinger holds up; extend the end date by a year
and the split moves eight months later, the out-of-sample half lands in a
different regime, and the verdict inverts. Nothing about the strategies
changed. A single split cannot tell "this edge does not persist" apart from
"this edge does not persist *in the particular stretch the split happened to
score*".

This module walks the split forward instead:

    |---- IS (fold 0) ----|  OOS 0  |  OOS 1  |  OOS 2  |  OOS 3  |
    |---- IS (fold 1) --------------|  OOS 1  |  OOS 2  |  OOS 3  |
    |---- IS (fold 2) ------------------------|  OOS 2  |  OOS 3  |
    |---- IS (fold 3) ----------------------------------|  OOS 3  |

Anchored, because that is what you would do live: at each re-fit you use all
the history you have, not a fixed-length window. Each fold sweeps the grid on
its in-sample stretch and scores the winner only on the next segment. The
segments tile the period after the first split, so every bar from then on —
bar the embargo gap after each re-fit — is scored out-of-sample exactly once,
by parameters chosen before it and never on it. Stitching
the segments together gives an out-of-sample equity curve for the *procedure*
— "re-optimise periodically and trade the winner" — rather than for one
parameter set.

What comes out:

  - one verdict per fold, so a strategy that earned in 2019–21 and lost in
    2022 shows up as exactly that, not as an average;
  - the market's own return and realised volatility over each segment, so a
    failed fold can be read against what the market was doing;
  - how often the chosen parameters changed between folds — a winner that
    moves every re-fit was never one strategy;
  - metrics and a bootstrap interval on the stitched series.

The purge-and-embargo gap from `purge.py` sits at every boundary, and because
the folds are anchored, the bars purged from fold k+1's in-sample stretch are
the last bars of fold k's out-of-sample segment — the trade that straddles the
cut is scored once, on the side where it was opened, and never used to select.

Pure pandas/numpy. Positions are built once per grid cell on the full series
and sliced per fold; building them per fold on a slice would leave the first
warm-up bars flat and understate every fold.
"""

from collections import Counter

import numpy as np
import pandas as pd

from bootstrap import bootstrap_metrics
from engine import compute_returns
from metrics import compute_metrics
from purge import MIN_HALF_BARS, purged_split
from regimes import regime_breakdown
from strategies import build_positions, longest_window, param_grid
from validation import _segment_metrics, _segment_net_return, _verdict

DEFAULT_FOLDS = 4
# The first in-sample stretch. Below this the earliest folds select on so
# little history that their verdicts are noise about the grid, not the market.
MIN_TRAIN_RATIO = 0.4
TRADING_DAYS = 252


def _fold_edges(n: int, n_folds: int, min_train_ratio: float) -> list[int]:
    """Nominal split points: the first at `min_train_ratio`, the rest tiling
    what remains into `n_folds` equal segments. Returns n_folds + 1 edges;
    fold k scores [edges[k], edges[k+1])."""
    first = int(n * min_train_ratio)
    remaining = n - first
    fold_len = remaining // n_folds
    if first < MIN_HALF_BARS or fold_len < MIN_HALF_BARS:
        raise ValueError(
            f"Date range is too short for {n_folds} folds — the first in-sample "
            f"stretch and every out-of-sample segment need at least "
            f"{MIN_HALF_BARS} bars. Use a longer period or fewer folds."
        )
    edges = [first + k * fold_len for k in range(n_folds)]
    edges.append(n)
    return edges


def _overall_verdict(fold_sharpes: list[float], stitched_sharpe: float) -> str:
    positive = sum(1 for s in fold_sharpes if s > 0)
    if positive == len(fold_sharpes) and stitched_sharpe > 0:
        return "consistent"
    if positive == 0:
        return "failed"
    return "regime_dependent"


def rolling_walk_forward(
    close: pd.Series,
    transaction_cost: float,
    strategy: str = "momentum",
    base_params: dict | None = None,
    n_folds: int = DEFAULT_FOLDS,
    min_train_ratio: float = MIN_TRAIN_RATIO,
    grid: list[dict] | None = None,
    seed: int = 0,
) -> dict:
    """Anchored walk-forward over `n_folds` consecutive out-of-sample segments.

    Same inputs as `walk_forward`. The grid is swept once per fold on that
    fold's in-sample stretch; the winner is scored on the segment that follows
    and nowhere else.
    """
    base_params = base_params or {}
    n = len(close)
    if not 0.2 <= min_train_ratio <= 0.8:
        raise ValueError("min_train_ratio must be between 0.2 and 0.8")
    if n_folds < 2:
        raise ValueError("n_folds must be at least 2 — one fold is walk_forward()")

    edges = _fold_edges(n, n_folds, min_train_ratio)
    returns = compute_returns(close)
    combos = grid if grid is not None else param_grid(strategy)

    # One position series per grid cell, on the full history. Every fold
    # slices these; nothing is rebuilt per fold.
    cells = []
    for combo in combos:
        params = {**base_params, **combo}
        cells.append(
            {
                "params": combo,
                "warmup": longest_window(strategy, params),
                "position": build_positions(close, strategy, params),
            }
        )

    folds = []
    stitched_net = []
    stitched_pos = []
    for k in range(n_folds):
        split_at = edges[k]
        oos_end = edges[k + 1]
        boundary = purged_split(n, split_at)
        is_end, oos_start = boundary["is_end"], boundary["oos_start"]
        # The gap is sized for a split of the whole series; the last fold's
        # segment can be short enough that the embargo eats into it. Keep the
        # segment above the floor rather than let it collapse.
        if oos_end - oos_start < MIN_HALF_BARS:
            oos_start = max(split_at, oos_end - MIN_HALF_BARS)
        is_slice = slice(0, is_end)
        oos_slice = slice(oos_start, oos_end)

        # --- sweep the grid on this fold's in-sample stretch --------------
        sweep = []
        for cell in cells:
            # A cell whose warm-up exceeds the in-sample stretch can never fire
            # inside it; it may still qualify in a later, longer fold.
            if cell["warmup"] >= is_end:
                continue
            m = _segment_metrics(
                cell["position"].iloc[is_slice], returns.iloc[is_slice], transaction_cost
            )
            sweep.append((m["sharpe_ratio"], cell))
        if not sweep:
            raise ValueError(
                "No parameter combination fits inside the first in-sample stretch — "
                "every option needs more history than it provides."
            )
        is_sharpe, best = max(sweep, key=lambda t: t[0])

        # --- score the winner on the next segment only --------------------
        oos_pos = best["position"].iloc[oos_slice]
        oos_ret = returns.iloc[oos_slice]
        oos = _segment_metrics(oos_pos, oos_ret, transaction_cost)
        stitched_net.append(_segment_net_return(oos_pos, oos_ret, transaction_cost))
        stitched_pos.append(oos_pos)

        # What the market itself did over the segment, so a fold's verdict
        # can be read against the regime it was scored in.
        seg_close = close.iloc[oos_slice]
        benchmark = float(seg_close.iloc[-1] / seg_close.iloc[0] - 1)
        realised_vol = float(oos_ret.std() * TRADING_DAYS ** 0.5)

        folds.append(
            {
                "fold": k,
                "in_sample_bars": is_end,
                "in_sample_end_date": str(close.index[is_end - 1].date()),
                "gap_bars": oos_start - is_end,
                "out_of_sample_start_date": str(close.index[oos_start].date()),
                "out_of_sample_end_date": str(close.index[oos_end - 1].date()),
                "out_of_sample_bars": oos_end - oos_start,
                "combinations_tested": len(sweep),
                "best_params": best["params"],
                "in_sample_sharpe": round(float(is_sharpe), 6),
                "out_of_sample_sharpe": oos["sharpe_ratio"],
                "out_of_sample_return": oos["total_return"],
                "out_of_sample_max_drawdown": oos["max_drawdown"],
                "verdict": _verdict(is_sharpe, oos["sharpe_ratio"]),
                "benchmark_return": round(benchmark, 6),
                "realised_volatility": round(realised_vol, 6),
            }
        )

    # --- the stitched out-of-sample curve -------------------------------
    net = pd.concat(stitched_net)
    pos = pd.concat(stitched_pos)
    equity = (1 + net).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()
    stitched = compute_metrics(net, equity, drawdown, pos)
    ci = bootstrap_metrics(net, seed=seed)
    stitched_block = {
        **stitched,
        "bars": int(len(net)),
        "start_date": str(net.index[0].date()),
        "end_date": str(net.index[-1].date()),
        "sharpe_interval": (
            ci["metrics"]["sharpe_ratio"] if ci.get("available") else {"available": False, "reason": ci.get("reason")}
        ),
        # The out-of-sample record broken down by the market's volatility
        # regime. Labels are computed on the full market series, so the
        # embargo gaps between segments do not distort the window.
        "regimes": regime_breakdown(net, pos, returns),
    }

    # --- did the winner stay the same winner? ---------------------------
    keys = [tuple(sorted(f["best_params"].items())) for f in folds]
    modal_key, modal_count = Counter(keys).most_common(1)[0]
    stability = {
        "distinct_parameter_sets": len(set(keys)),
        "modal_params": dict(modal_key),
        "modal_share": round(modal_count / n_folds, 6),
    }

    fold_sharpes = [f["out_of_sample_sharpe"] for f in folds]
    counts = Counter(f["verdict"] for f in folds)

    return {
        "strategy": strategy,
        "n_folds": n_folds,
        "min_train_ratio": min_train_ratio,
        "first_split_date": str(close.index[edges[0]].date()),
        "folds": folds,
        "folds_positive": sum(1 for s in fold_sharpes if s > 0),
        "verdict_counts": dict(counts),
        "out_of_sample_sharpe_range": [round(min(fold_sharpes), 6), round(max(fold_sharpes), 6)],
        "out_of_sample_stitched": stitched_block,
        "parameter_stability": stability,
        "verdict": _overall_verdict(fold_sharpes, stitched["sharpe_ratio"]),
    }
