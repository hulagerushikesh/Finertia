"""Tests for the Deflated Sharpe Ratio.

Statistical code fails quietly — a wrong constant or a mixed-up annualisation
still returns a plausible probability. So these pin against values that come
from outside this codebase: the published figure in Bailey and Lopez de Prado
(2014), the closed form from Lo (2002) that PSR must reduce to under Normality,
and a Monte-Carlo simulation of the quantity being approximated.
"""

import math

import numpy as np
import pytest

from deflated import (
    EULER_MASCHERONI,
    _norm_cdf,
    _norm_ppf,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
)


# --------------------------------------------------------------------------
# Normal distribution helpers, which everything else is built on
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "p,expected",
    [
        (0.5, 0.0),
        (0.95, 1.6448536270),
        (0.975, 1.9599639845),
        (0.99, 2.3263478740),
        (0.025, -1.9599639845),
        (0.001, -3.0902323062),
    ],
)
def test_norm_ppf_matches_published_quantiles(p, expected):
    assert _norm_ppf(p) == pytest.approx(expected, abs=1e-6)


def test_norm_ppf_rejects_values_outside_the_open_unit_interval():
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            _norm_ppf(bad)


def test_norm_cdf_and_ppf_are_inverses():
    for x in (-3.0, -1.5, -0.2, 0.0, 0.7, 2.4):
        assert _norm_ppf(_norm_cdf(x)) == pytest.approx(x, abs=1e-6)


def test_euler_mascheroni_constant_is_correct():
    # The paper's snippet uses 0.5772156649; a typo here silently shifts every
    # noise bar in the app.
    assert EULER_MASCHERONI == pytest.approx(0.5772156649015329, abs=1e-15)


# --------------------------------------------------------------------------
# Expected maximum Sharpe
# --------------------------------------------------------------------------

def test_reproduces_the_papers_published_figure():
    """Bailey & Lopez de Prado: with E[SR]=0, V[SR]=1 and N=1000 independent
    backtests, the expected maximum Sharpe is 3.26 even when the true SR is
    zero. This is the number the whole correction rests on."""
    assert expected_max_sharpe(1.0, 1000) == pytest.approx(3.26, abs=0.01)


def test_matches_monte_carlo_simulation_of_the_maximum():
    """The analytic form approximates E[max of N standard Normals]. Simulating
    it directly is an independent check that the formula is assembled right."""
    rng = np.random.default_rng(20260819)
    for n_trials in (10, 100, 500):
        simulated = np.mean([rng.normal(0.0, 1.0, n_trials).max() for _ in range(20_000)])
        assert expected_max_sharpe(1.0, n_trials) == pytest.approx(simulated, abs=0.05)


def test_noise_bar_rises_with_more_trials():
    bars = [expected_max_sharpe(1.0, n) for n in (2, 10, 100, 1000, 10_000)]
    assert bars == sorted(bars), "trying more combinations must raise the bar, never lower it"


def test_noise_bar_scales_linearly_with_dispersion():
    # Doubling the spread of trial Sharpes doubles the expected maximum.
    assert expected_max_sharpe(2.0, 50) == pytest.approx(2 * expected_max_sharpe(1.0, 50))


def test_a_single_trial_is_not_a_selection():
    # Z^-1(1 - 1/1) is undefined; one trial involves no cherry-picking anyway.
    assert expected_max_sharpe(1.0, 1) == 0.0


def test_identical_trials_leave_nothing_to_deflate():
    assert expected_max_sharpe(0.0, 500) == 0.0


def test_rejects_a_non_positive_trial_count():
    with pytest.raises(ValueError):
        expected_max_sharpe(1.0, 0)


# --------------------------------------------------------------------------
# Probabilistic Sharpe Ratio
# --------------------------------------------------------------------------

def test_psr_reduces_to_lo_2002_under_normality():
    """With skew 0 and kurtosis 3 the denominator must collapse to
    sqrt(1 + SR^2/2), the standard error in Lo (2002). If kurtosis were being
    read as excess, this identity breaks."""
    sharpe, n_obs = 0.1, 1000
    lo = _norm_cdf(sharpe * math.sqrt(n_obs - 1) / math.sqrt(1 + sharpe**2 / 2))
    assert probabilistic_sharpe_ratio(sharpe, 0.0, n_obs, 0.0, 3.0) == pytest.approx(lo, abs=1e-12)


def test_kurtosis_is_non_excess():
    """A Normal distribution must be the neutral case at kurtosis 3, not 0.
    Passing 0 (excess) has to give a different answer, or the convention is
    being silently ignored."""
    normal = probabilistic_sharpe_ratio(0.1, 0.0, 1000, 0.0, 3.0)
    as_excess = probabilistic_sharpe_ratio(0.1, 0.0, 1000, 0.0, 0.0)
    assert normal != pytest.approx(as_excess)


def test_a_sharpe_exactly_at_the_benchmark_is_a_coin_flip():
    assert probabilistic_sharpe_ratio(0.5, 0.5, 500, 0.0, 3.0) == pytest.approx(0.5)


def test_longer_track_record_increases_confidence():
    short = probabilistic_sharpe_ratio(0.05, 0.0, 100, 0.0, 3.0)
    long = probabilistic_sharpe_ratio(0.05, 0.0, 2000, 0.0, 3.0)
    assert long > short


def test_negative_skew_and_fat_tails_reduce_confidence():
    baseline = probabilistic_sharpe_ratio(0.1, 0.0, 1000, 0.0, 3.0)
    assert probabilistic_sharpe_ratio(0.1, 0.0, 1000, -1.5, 3.0) < baseline
    assert probabilistic_sharpe_ratio(0.1, 0.0, 1000, 0.0, 12.0) < baseline


def test_returns_nan_when_the_variance_estimate_goes_non_positive():
    # Extreme moments can drive the denominator negative; a confident number
    # there would be a lie.
    result = probabilistic_sharpe_ratio(0.9, 0.0, 500, skew=5.0, kurtosis=1.0)
    assert math.isnan(result)


def test_psr_rejects_too_few_observations():
    with pytest.raises(ValueError):
        probabilistic_sharpe_ratio(0.1, 0.0, 1, 0.0, 3.0)


# --------------------------------------------------------------------------
# The end-to-end deflation
# --------------------------------------------------------------------------

def _returns(mean, std, n, seed):
    return np.random.default_rng(seed).normal(mean, std, n)


def test_annualised_sharpes_are_de_annualised_before_use():
    """T counts daily bars, so an annualised Sharpe fed straight in overstates
    the statistic by about sqrt(252). Passing the same data both ways must give
    the same answer once the flag is set correctly."""
    daily = _returns(0.0004, 0.01, 800, seed=1)
    trials_annual = [0.8, 1.1, 0.4, 1.5, 0.9]
    trials_daily = [t / math.sqrt(252) for t in trials_annual]

    a = deflated_sharpe_ratio(trials_annual, daily, annualized=True)
    b = deflated_sharpe_ratio(trials_daily, daily, annualized=False)

    # Same data described two ways must give the same answer everywhere. The
    # flag is about input units only; reporting is always annualised.
    assert a == b
    # And the reported Sharpe is annualised, so it belongs beside the app's
    # other Sharpe ratios rather than being ~16x smaller than them.
    raw_per_obs = daily.mean() / daily.std(ddof=1)
    assert a["selected_sharpe"] == pytest.approx(raw_per_obs * math.sqrt(252), abs=1e-6)


def test_deflation_is_strictly_harsher_than_the_undeflated_probability():
    daily = _returns(0.0006, 0.01, 1000, seed=2)
    out = deflated_sharpe_ratio([0.3, 0.9, 1.4, 0.6, 1.1, 0.2], daily)
    assert out["computable"] is True
    assert out["deflated_sharpe_ratio"] <= out["psr_vs_zero"]


def test_more_trials_make_the_same_result_less_believable():
    """The core claim: an identical return series should be judged more
    sceptically when it was cherry-picked from a wider search."""
    daily = _returns(0.0008, 0.01, 1200, seed=3)
    narrow = deflated_sharpe_ratio([0.9, 1.0, 1.1], daily)
    wide = deflated_sharpe_ratio([0.9, 1.0, 1.1] * 40, daily)
    assert wide["expected_max_sharpe"] > narrow["expected_max_sharpe"]
    assert wide["deflated_sharpe_ratio"] < narrow["deflated_sharpe_ratio"]


def test_a_genuinely_strong_strategy_still_clears_the_bar():
    """The correction must not reject everything — otherwise it is useless."""
    strong = _returns(0.0025, 0.008, 1500, seed=4)  # ~5 annualised Sharpe
    out = deflated_sharpe_ratio([1.0, 1.2, 0.8, 1.1], strong)
    assert out["clears_noise_bar"] is True
    assert out["verdict"] == "significant"


def test_a_zero_edge_strategy_is_not_declared_significant():
    noise = _returns(0.0, 0.01, 1200, seed=5)
    out = deflated_sharpe_ratio([0.1, 0.5, -0.3, 0.9, 0.2, -0.1], noise)
    assert out["verdict"] in {"noise", "not_significant", "inconclusive"}


def test_declines_when_the_strategy_is_flat_almost_every_bar():
    """A series of mostly zeros produced kurtosis near 1000 in testing. The
    formula still returns a number for it, and that number means nothing, so
    the result has to be refused rather than reported."""
    mostly_flat = np.zeros(1000)
    mostly_flat[:12] = 0.02
    out = deflated_sharpe_ratio([0.4, 0.9, 1.2], mostly_flat)
    assert out["verdict"] == "inconclusive"
    assert out["unreliable"] is not None
    assert out["active_bars"] == 12


def test_reports_not_computable_rather_than_crashing_on_empty_input():
    assert deflated_sharpe_ratio([], _returns(0.001, 0.01, 100, 6))["computable"] is False
    assert deflated_sharpe_ratio([1.0], np.array([0.01]))["computable"] is False


@pytest.mark.parametrize("value", [0.001, 1.0, 0.05, 1e-5, 0.0])
def test_a_constant_return_series_has_no_sharpe_to_deflate(value):
    """Floating-point summation leaves a flat series with std ~4e-19 rather
    than 0, which an exact zero-check misses and which implies a Sharpe around
    2e15. Every constant series must be refused, whatever its level."""
    out = deflated_sharpe_ratio([0.5, 0.9], np.full(500, value))
    assert out["computable"] is False


def test_non_finite_inputs_are_dropped_not_propagated():
    daily = _returns(0.0005, 0.01, 600, seed=7)
    with_junk = np.concatenate([daily, [np.nan, np.inf]])
    clean = deflated_sharpe_ratio([0.5, 0.8, 1.0], daily)
    dirty = deflated_sharpe_ratio([0.5, np.nan, 0.8, None, 1.0], with_junk)
    assert dirty["n_trials"] == clean["n_trials"]
    assert dirty["n_obs"] == clean["n_obs"]
    assert dirty["deflated_sharpe_ratio"] == pytest.approx(clean["deflated_sharpe_ratio"])
