"""Probability of Backtest Overfitting, via Combinatorially Symmetric Cross-Validation.

The Deflated Sharpe Ratio in `deflated.py` asks whether one selected result
survives the search that found it. This asks a different and broader question:
is the *selection procedure itself* prone to overfitting on this data?

The method is from Bailey, Borwein, Lopez de Prado and Zhu (2014), "The
Probability of Backtest Overfitting". The idea:

  Split the period into S equal blocks. For every way of choosing S/2 of them
  as a training set (with the rest as the test set), pick whichever strategy
  scored best in training, then look at where that same strategy ranks in the
  test half. If the selection procedure works, the training winner should keep
  ranking near the top. If it is fitting noise, the winner lands wherever.

  PBO is the share of splits where the training winner finishes below the
  median of the test half. A PBO near 0.5 means selecting on in-sample
  performance is no better than picking at random.

Note the asymmetry this catches that a single 70/30 split cannot: one split
gives one answer, and that answer depends heavily on where the split fell.
C(S, S/2) splits give a distribution.

What it deliberately does NOT catch, which matters when reading the result:
CSCV draws its training and testing halves from blocks spread across the whole
period, so both halves span the same regimes. A strategy whose edge existed
only in the first two years is still present in both halves and will not be
flagged here — verified in testing, where an edge confined to the first half of
the data still produced a PBO of 0.01. Detecting that is walk-forward's job,
because walk-forward is chronological and this is not. The two answer different
questions and neither replaces the other:

  walk-forward  Did the edge survive into a later period it was not fitted on?
  PBO           Is picking a winner on in-sample score better than picking at
                random, across every way of dividing this period?

Two further diagnostics come almost free once the splits exist:

  performance degradation  Regress each split's out-of-sample score on its
                           in-sample score. A negative slope means better
                           in-sample selection actively predicts worse
                           out-of-sample results.

  probability of loss      Share of splits where the training winner actually
                           lost money out-of-sample.

Pure numpy and stdlib, like the rest of the engine.
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np

# C(S, S/2) grows fast: S=8 gives 70 splits, S=10 gives 252, S=16 gives 12,780.
# Eight keeps a validation request interactive while still producing a
# distribution rather than a single number.
DEFAULT_SPLITS = 8

# Guard against a caller asking for something that would never return. C(20,10)
# is already 184,756 splits.
MAX_SPLITS = 16

TRADING_DAYS = 252


def _sharpe_columns(block: np.ndarray) -> np.ndarray:
    """Per-observation Sharpe for every column of a (rows x strategies) block.

    Columns that never move have no Sharpe; they are scored as -inf so they
    sort last and can never be chosen as a training winner. Zero would rank
    them above genuinely losing strategies, which would flatter the procedure.
    """
    mean = block.mean(axis=0)
    std = block.std(axis=0, ddof=1)
    out = np.full(block.shape[1], -np.inf)
    live = std > 0
    out[live] = mean[live] / std[live]
    return out


def combinatorial_pbo(
    returns_matrix,
    n_splits: int = DEFAULT_SPLITS,
) -> dict:
    """Run CSCV over a (T observations x N strategies) matrix of per-bar returns.

    Every column is one candidate — here, one parameter combination from the
    walk-forward grid — and every row is one bar, aligned across all of them.
    """
    matrix = np.asarray(returns_matrix, dtype=float)

    if matrix.ndim != 2:
        raise ValueError("returns_matrix must be two-dimensional (bars x strategies)")
    if n_splits % 2 != 0:
        raise ValueError("n_splits must be even so the halves are the same size")
    if not 2 <= n_splits <= MAX_SPLITS:
        raise ValueError(f"n_splits must be between 2 and {MAX_SPLITS}")

    n_obs, n_strategies = matrix.shape

    if n_strategies < 2:
        return {
            "computable": False,
            "reason": "Overfitting of a selection needs at least two candidates to select between.",
        }
    if n_obs < n_splits * 2:
        return {
            "computable": False,
            "reason": (
                f"Need at least {n_splits * 2} bars to form {n_splits} blocks; "
                f"this period has {n_obs}."
            ),
        }

    # Drop the remainder so every block is the same length, which the method
    # requires. Trimming from the front keeps the most recent data, which is
    # the half anyone actually cares about.
    block_len = n_obs // n_splits
    trimmed = matrix[n_obs - block_len * n_splits:]
    blocks = [
        np.arange(i * block_len, (i + 1) * block_len) for i in range(n_splits)
    ]

    half = n_splits // 2
    logits: list[float] = []
    is_scores: list[float] = []
    oos_scores: list[float] = []
    below_median = 0
    losing = 0

    for chosen in combinations(range(n_splits), half):
        chosen_set = set(chosen)
        # Rows are re-joined in their original chronological order, not in the
        # order the blocks were picked — path-dependent measures would
        # otherwise depend on an arbitrary permutation.
        train_idx = np.concatenate([blocks[i] for i in sorted(chosen_set)])
        test_idx = np.concatenate(
            [blocks[i] for i in range(n_splits) if i not in chosen_set]
        )

        train_sharpe = _sharpe_columns(trimmed[train_idx])
        test_sharpe = _sharpe_columns(trimmed[test_idx])

        if not np.isfinite(train_sharpe).any():
            continue  # nothing was live in this training half

        best = int(np.argmax(train_sharpe))
        chosen_oos = test_sharpe[best]
        if not math.isfinite(chosen_oos):
            continue

        # Rank of the chosen strategy's out-of-sample score, 1 = worst.
        # `argsort` twice would break ties arbitrarily; counting strictly-worse
        # peers plus half the ties keeps a tie at the midpoint rather than
        # handing it an arbitrary side of the median.
        finite = np.isfinite(test_sharpe)
        worse = int(np.sum(test_sharpe[finite] < chosen_oos))
        tied = int(np.sum(test_sharpe[finite] == chosen_oos))
        rank = worse + (tied + 1) / 2.0

        omega = rank / (n_strategies + 1)
        # Clamp before the logit: omega can reach the open interval's edges when
        # the chosen strategy is the outright best or worst, and log(0) is not a
        # number anyone wants in an average.
        omega = min(max(omega, 1e-9), 1 - 1e-9)
        logits.append(math.log(omega / (1 - omega)))

        is_scores.append(float(train_sharpe[best]))
        oos_scores.append(float(chosen_oos))
        if omega < 0.5:
            below_median += 1
        if chosen_oos < 0:
            losing += 1

    n_used = len(logits)
    if n_used == 0:
        return {
            "computable": False,
            "reason": "No split produced a usable comparison — the candidates never traded.",
        }

    pbo = below_median / n_used

    # Performance degradation: how out-of-sample score moves with in-sample
    # score across splits. A negative slope is the damning case — it means
    # picking harder in-sample actively costs you out-of-sample.
    is_arr = np.array(is_scores)
    oos_arr = np.array(oos_scores)
    if float(is_arr.std()) > 0:
        slope, intercept = np.polyfit(is_arr, oos_arr, 1)
    else:
        slope, intercept = 0.0, float(oos_arr.mean())

    return {
        "computable": True,
        "n_splits": n_splits,
        "n_combinations": n_used,
        "n_strategies": n_strategies,
        "bars_per_block": block_len,
        "pbo": round(pbo, 6),
        "probability_of_loss": round(losing / n_used, 6),
        # Annualised so the numbers read like every other Sharpe in the app.
        "median_is_sharpe": round(float(np.median(is_arr)) * math.sqrt(TRADING_DAYS), 6),
        "median_oos_sharpe": round(float(np.median(oos_arr)) * math.sqrt(TRADING_DAYS), 6),
        "degradation_slope": round(float(slope), 6),
        "degradation_intercept": round(
            float(intercept) * math.sqrt(TRADING_DAYS), 6
        ),
        "median_logit": round(float(np.median(logits)), 6),
        "verdict": _pbo_verdict(pbo),
    }


def _pbo_verdict(pbo: float) -> str:
    """Plain reading of the probability.

    0.5 is the meaningful landmark, not an arbitrary threshold: at that level
    the strategy chosen in-sample lands below the out-of-sample median as often
    as not, which is what picking at random would do.
    """
    if pbo >= 0.5:
        return "overfit"
    if pbo >= 0.35:
        return "fragile"
    if pbo >= 0.2:
        return "acceptable"
    return "robust"
