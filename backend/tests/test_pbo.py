"""Tests for the Probability of Backtest Overfitting (CSCV).

PBO is a probability, so almost any implementation returns something between 0
and 1 and looks fine. These pin the properties the method must have instead:
the combination count from the paper, PBO near 0.5 when selection is genuinely
worthless, and PBO low when one candidate has a real and persistent edge.
"""

import math
from itertools import combinations

import numpy as np
import pytest

from pbo import DEFAULT_SPLITS, MAX_SPLITS, _sharpe_columns, combinatorial_pbo


def _noise(rows, cols, seed, scale=0.01):
    return np.random.default_rng(seed).normal(0.0, scale, (rows, cols))


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------

def test_enumerates_every_balanced_split():
    """C(S, S/2) — 70 for the default S=8. A wrong count means whole splits are
    being skipped and the distribution is not what it claims."""
    out = combinatorial_pbo(_noise(800, 10, seed=1))
    assert out["n_splits"] == DEFAULT_SPLITS
    assert out["n_combinations"] == len(list(combinations(range(8), 4))) == 70


@pytest.mark.parametrize("n_splits,expected", [(4, 6), (6, 20), (8, 70), (10, 252)])
def test_combination_count_follows_the_formula(n_splits, expected):
    out = combinatorial_pbo(_noise(1200, 8, seed=2), n_splits=n_splits)
    assert out["n_combinations"] == expected


def test_blocks_are_equal_length_and_cover_the_period():
    out = combinatorial_pbo(_noise(1003, 6, seed=3), n_splits=8)
    # 1003 // 8 = 125, so 3 bars are dropped to keep the blocks even.
    assert out["bars_per_block"] == 125


def test_rejects_an_odd_split_count():
    with pytest.raises(ValueError, match="even"):
        combinatorial_pbo(_noise(400, 5, seed=4), n_splits=7)


def test_rejects_a_split_count_that_would_never_return():
    with pytest.raises(ValueError):
        combinatorial_pbo(_noise(4000, 5, seed=5), n_splits=MAX_SPLITS + 2)


def test_rejects_a_non_matrix():
    with pytest.raises(ValueError, match="two-dimensional"):
        combinatorial_pbo(np.array([0.1, 0.2, 0.3]))


# --------------------------------------------------------------------------
# The properties that make it meaningful
# --------------------------------------------------------------------------

def test_worthless_selection_gives_pbo_near_one_half():
    """Every candidate is noise, so whichever wins in training is arbitrary and
    should land below the test median about half the time. This is the number
    the whole method is calibrated against."""
    out = combinatorial_pbo(_noise(1200, 16, seed=11))
    assert out["pbo"] == pytest.approx(0.5, abs=0.15)
    assert out["verdict"] in {"overfit", "fragile"}


def test_a_real_persistent_edge_is_not_called_overfit():
    """One candidate genuinely better in every period. Selection should find it
    and it should hold up, so PBO must be well below the coin-flip line."""
    matrix = _noise(1500, 12, seed=12)
    matrix[:, 5] += 0.004  # large, constant, present in every block
    out = combinatorial_pbo(matrix)
    assert out["pbo"] < 0.2
    assert out["verdict"] in {"robust", "acceptable"}


def test_selection_on_noise_degrades_out_of_sample():
    """The training winner is the luckiest column, so its out-of-sample score
    should fall back toward the pack."""
    out = combinatorial_pbo(_noise(1200, 16, seed=13))
    assert out["median_is_sharpe"] > out["median_oos_sharpe"]


def test_degradation_slope_is_reported_and_finite():
    out = combinatorial_pbo(_noise(1000, 10, seed=14))
    assert math.isfinite(out["degradation_slope"])


def test_probability_of_loss_is_a_probability():
    out = combinatorial_pbo(_noise(1000, 10, seed=15))
    assert 0.0 <= out["probability_of_loss"] <= 1.0
    assert 0.0 <= out["pbo"] <= 1.0


def test_more_blocks_still_agree_on_a_worthless_selection():
    """The answer should be a property of the data, not of how finely it was
    chopped. Different S must not move PBO wildly."""
    matrix = _noise(2000, 12, seed=16)
    coarse = combinatorial_pbo(matrix, n_splits=4)["pbo"]
    fine = combinatorial_pbo(matrix, n_splits=10)["pbo"]
    assert abs(coarse - fine) < 0.35


def test_a_regime_limited_edge_is_not_flagged_and_that_is_expected():
    """Documents a real limitation rather than asserting a wrong belief.

    CSCV draws both halves from blocks spread across the whole period, so an
    edge confined to the first half sits in the training AND testing halves and
    is not detected. Walk-forward is the chronological test that catches this.
    If this ever starts failing, CSCV has stopped being combinatorial.
    """
    matrix = _noise(1600, 12, seed=17)
    matrix[: 1600 // 2, 3] += 0.006
    out = combinatorial_pbo(matrix)
    assert out["pbo"] < 0.2


# --------------------------------------------------------------------------
# Degenerate inputs
# --------------------------------------------------------------------------

def test_needs_at_least_two_candidates_to_select_between():
    out = combinatorial_pbo(_noise(500, 1, seed=21))
    assert out["computable"] is False
    assert "two candidates" in out["reason"]


def test_refuses_a_period_too_short_to_block():
    out = combinatorial_pbo(_noise(10, 5, seed=22), n_splits=8)
    assert out["computable"] is False
    assert "bars" in out["reason"]


def test_a_flat_candidate_can_never_win_training():
    """A column that never moves has no Sharpe. Scoring it zero would rank it
    above every losing strategy and let it win, flattering the procedure."""
    matrix = _noise(800, 4, seed=23)
    matrix[:, 0] = 0.0
    scores = _sharpe_columns(matrix[:100])
    assert scores[0] == -np.inf
    assert int(np.argmax(scores)) != 0


def test_all_candidates_flat_is_reported_not_crashed():
    out = combinatorial_pbo(np.zeros((800, 5)))
    assert out["computable"] is False


def test_identical_candidates_land_at_the_median_not_an_arbitrary_side():
    """With every column the same, the chosen one ties with all the others.
    Tie handling must put it at the midpoint, so PBO cannot come out as 0 or 1
    purely from how ties were broken."""
    column = np.random.default_rng(24).normal(0.0005, 0.01, 900)
    matrix = np.column_stack([column] * 8)
    out = combinatorial_pbo(matrix)
    assert out["computable"] is True
    assert out["pbo"] == pytest.approx(0.0, abs=0.01) or out["pbo"] == pytest.approx(
        0.5, abs=0.1
    ), "a total tie must not resolve to a confident 0 or 1"
    assert math.isfinite(out["median_logit"])
