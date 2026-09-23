"""The Sharpe-difference test, pinned at the three places it can quietly lie.

The p-value is the one number on the page a reader cannot sanity-check by eye,
so the tests aim at its machinery rather than at its output: the statistic is
the textbook Sharpe difference, the standard error uses the pairing (a paired
test on correlated series must be tighter than an unpaired one, or the whole
module is pointless), and the bootstrap is a null distribution rather than an
arbitrary number between 0 and 1.

The dependent null used throughout is the mixture
`a = mu + w(b - mu) + sqrt(1-w^2)(c - mu)`: it carries the benchmark's own
mean and variance — and therefore exactly its Sharpe ratio — while correlating
with it at w. The obvious alternative, "trade the benchmark's asset on a
fraction f of the bars", is NOT a null: that strategy's population Sharpe is
sqrt(f) times the benchmark's, whatever it is scaled by.
"""

import math

import numpy as np
import pandas as pd
import pytest

from sharpe_test import (
    ALPHA,
    MIN_BARS,
    TRADING_DAYS,
    _hac_variance,
    _influence,
    andrews_bandwidth,
    sharpe_difference_test,
)

MU, SIG = 0.0004, 0.012


def index(n):
    return pd.date_range("2018-01-01", periods=n, freq="B")


def noise(n=1000, mu=MU, sig=SIG, seed=0):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mu, sig, n), index=index(n))


def mixture(n=1000, w=0.7, edge=0.0, seed=0):
    """A paired (strategy, benchmark) with equal population Sharpe when edge=0."""
    rng = np.random.default_rng(seed)
    b = rng.normal(MU, SIG, n)
    c = rng.normal(MU, SIG, n)
    a = MU + w * (b - MU) + math.sqrt(1 - w ** 2) * (c - MU) + edge
    idx = index(n)
    return pd.Series(a, index=idx), pd.Series(b, index=idx)


def ar1(n=1000, rho=0.0, seed=0):
    rng = np.random.default_rng(seed)
    e = rng.normal(0, 1, n)
    out = np.empty(n)
    out[0] = e[0]
    for t in range(1, n):
        out[t] = rho * out[t - 1] + e[t]
    return out


# ---------------------------------------------------------------------------
# The statistic is the Sharpe difference
# ---------------------------------------------------------------------------


class TestTheStatistic:
    def test_the_two_sharpes_are_mean_over_sd_annualised(self):
        a, b = mixture(seed=1)
        r = sharpe_difference_test(a, b, resamples=200, seed=1)
        for series, key in ((a, "strategy_sharpe"), (b, "benchmark_sharpe")):
            x = series.to_numpy()
            expected = x.mean() / x.std(ddof=0) * math.sqrt(TRADING_DAYS)
            assert r[key] == pytest.approx(expected, abs=5e-5)
        assert r["difference"] == pytest.approx(r["strategy_sharpe"] - r["benchmark_sharpe"], abs=1e-4)

    def test_sharpe_is_scale_free_so_leverage_moves_nothing(self):
        """Doubling every return doubles mean and standard deviation alike. A
        test that moved would be measuring position size, not skill."""
        a, b = mixture(seed=2)
        plain = sharpe_difference_test(a, b, resamples=300, seed=4)
        levered = sharpe_difference_test(a * 3, b, resamples=300, seed=4)
        assert levered["strategy_sharpe"] == pytest.approx(plain["strategy_sharpe"], abs=1e-3)
        assert levered["p_value"] == plain["p_value"]

    def test_a_fixed_multiple_of_the_benchmark_has_nothing_to_test(self):
        b = noise(seed=3)
        r = sharpe_difference_test(b * 2, b, resamples=200, seed=3)
        assert r["computable"]
        assert r["difference"] == 0.0
        assert r["standard_error"] == 0.0
        assert r["p_value"] == 1.0
        assert "same Sharpe ratio" in r["verdict"]

    def test_the_identical_series_is_the_same_case(self):
        b = noise(seed=4)
        assert sharpe_difference_test(b, b, resamples=200, seed=4)["p_value"] == 1.0

    def test_the_sign_says_which_side_is_ahead(self):
        a, b = mixture(edge=0.0006, seed=5)
        ahead = sharpe_difference_test(a, b, resamples=300, seed=5)
        behind = sharpe_difference_test(b, a, resamples=300, seed=5)
        assert ahead["difference"] > 0 > behind["difference"]
        assert ahead["difference"] == pytest.approx(-behind["difference"], abs=1e-4)
        assert ahead["p_value"] == pytest.approx(behind["p_value"], abs=0.05)


# ---------------------------------------------------------------------------
# The standard error uses the pairing and the dependence
# ---------------------------------------------------------------------------


class TestStandardError:
    def test_pairing_shrinks_the_error_bar(self):
        """The reason this is not a two-sample t-test. Two strategies with the
        same Sharpes, one riding the benchmark's own bars and one independent
        of it: the correlated pair's difference is pinned far more tightly."""
        tight = sharpe_difference_test(*mixture(w=0.95, seed=6), resamples=200, seed=6)
        loose = sharpe_difference_test(*mixture(w=0.0, seed=6), resamples=200, seed=6)
        assert tight["standard_error"] < 0.4 * loose["standard_error"]

    def test_persistence_widens_it(self):
        """A series whose influence function is autocorrelated carries less
        information per bar than its length suggests, and the HAC term has to
        say so."""
        n = 1500
        idx = index(n)
        b = pd.Series(MU + SIG * ar1(n, 0.0, seed=7), index=idx)
        a_iid = pd.Series(MU + SIG * ar1(n, 0.0, seed=8), index=idx)
        a_slow = pd.Series(MU + SIG * ar1(n, 0.6, seed=8) * math.sqrt(1 - 0.6 ** 2), index=idx)
        iid = sharpe_difference_test(a_iid, b, resamples=200, seed=7)
        slow = sharpe_difference_test(a_slow, b, resamples=200, seed=7)
        assert slow["hac_lags"] > iid["hac_lags"]
        assert slow["standard_error"] > iid["standard_error"]

    def test_no_measurable_persistence_means_no_lags(self):
        """A series whose lag-1 autocovariance is exactly zero: the long-run
        variance of white noise is its variance, and the rule has to say so
        rather than adding lags for their own sake."""
        # Products at lag 1 run +1, -1, +1, -1 over each four-bar block, so the
        # lag-1 autocovariance cancels exactly over a whole number of blocks.
        u = np.append(np.array([1.0, 1.0, -1.0, -1.0] * 250), 1.0)
        assert float(np.sum(u[1:] * u[:-1])) == 0.0
        assert andrews_bandwidth(u) == 0.0

    def test_white_noise_gets_a_bandwidth_of_a_few_bars_at_most(self):
        """rho-hat on white noise is O(1/sqrt(T)) rather than 0, and the
        bandwidth is O((rho^2 T)^(1/3)) — so it stays a small constant as the
        sample grows instead of drifting up with it."""
        for n in (500, 2000, 8000):
            assert andrews_bandwidth(ar1(n, 0.0, seed=9)) < 4.0

    def test_bandwidth_grows_with_persistence(self):
        widths = [andrews_bandwidth(ar1(2000, rho, seed=10)) for rho in (0.0, 0.3, 0.6, 0.9)]
        assert widths == sorted(widths)
        assert widths[-1] > 5

    def test_no_lags_is_just_the_variance(self):
        u = ar1(500, 0.5, seed=11)
        assert float(_hac_variance(u, 0)) == pytest.approx(float((u ** 2).mean()))

    def test_bartlett_never_returns_a_negative_variance(self):
        """An alternating series has strongly negative odd autocovariances —
        the case that makes a truncated (rectangular) kernel go negative and
        hand back an imaginary standard error. Nothing clamps the result, so
        this passes only while the weights really are Bartlett's."""
        u = np.array([1.0, -1.0] * 300)
        for lags in (1, 2, 5, 20, 100, 599):
            assert float(_hac_variance(u, lags)) >= 0.0
        # A rectangular kernel on this series is gamma0 + 2*gamma1 = 1 - 2 < 0.
        assert float((u ** 2).mean()) + 2 * float((u[1:] * u[:-1]).sum() / len(u)) < 0

    def test_positive_autocorrelation_raises_the_long_run_variance(self):
        u = ar1(2000, 0.7, seed=12)
        assert float(_hac_variance(u, 10)) > 1.5 * float(_hac_variance(u, 0))

    def test_the_influence_series_is_centred(self):
        a, b = mixture(seed=13)
        u = _influence(a.to_numpy()[None, :], b.to_numpy()[None, :])[0]
        assert u.mean() == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# The p-value behaves like a p-value
# ---------------------------------------------------------------------------


class TestPValue:
    def test_it_cannot_reach_zero(self):
        a, b = mixture(edge=0.01, seed=14)
        r = sharpe_difference_test(a, b, resamples=200, seed=14)
        assert r["p_value"] == pytest.approx(1 / 201, abs=1e-4)
        assert r["significant"]

    def test_deterministic_under_a_seed(self):
        a, b = mixture(seed=15)
        first = sharpe_difference_test(a, b, resamples=300, seed=2)
        again = sharpe_difference_test(a, b, resamples=300, seed=2)
        other = sharpe_difference_test(a, b, resamples=300, seed=3)
        assert first == again
        assert first["strategy_sharpe"] == other["strategy_sharpe"]

    def test_a_planted_edge_is_found(self):
        a, b = mixture(n=1500, edge=0.0009, seed=16)
        r = sharpe_difference_test(a, b, resamples=500, seed=16)
        assert r["p_value"] < ALPHA
        assert r["significant"]
        assert "above buy-and-hold" in r["verdict"]

    def test_the_same_edge_on_a_short_sample_is_not(self):
        """Power is a function of length, and the honest answer on 150 bars is
        that the gap cannot be told from noise."""
        a, b = mixture(n=150, edge=0.0009, seed=16)
        r = sharpe_difference_test(a, b, resamples=500, seed=16)
        assert r["p_value"] > ALPHA
        assert not r["significant"]
        assert "inside what this much data" in r["verdict"]

    def test_two_sided_means_a_loser_is_flagged_too(self):
        a, b = mixture(n=1500, edge=-0.0009, seed=17)
        r = sharpe_difference_test(a, b, resamples=500, seed=17)
        assert r["significant"]
        assert "BELOW" in r["verdict"]

    def test_the_pairing_survives_into_the_bootstrap(self):
        """A strategy that adds a constant 0.04% a day to the benchmark and
        takes no extra risk: the Sharpe gap is +0.55 with a standard error of
        0.01, because every resampled bar carries both series together. Draw
        the two series their own index paths and that certainty evaporates —
        the null would be two unrelated assets, which is not the question."""
        b = noise(seed=27)
        r = sharpe_difference_test(b + 0.0004, b, resamples=500, seed=27)
        assert r["difference"] > 0.5
        assert r["standard_error"] < 0.05
        assert r["p_value"] == pytest.approx(1 / 501, abs=1e-4)

    def test_null_p_values_sit_around_a_half(self):
        """Two-sided means both tails count. Under a true null a p-value is
        roughly uniform, so its median belongs near 0.5 — counting one tail
        only would halve it while leaving every rejection test above happy."""
        ps = [
            sharpe_difference_test(*mixture(n=800, w=0.7, seed=100 + s), resamples=300, seed=s)["p_value"]
            for s in range(24)
        ]
        assert 0.30 < float(np.median(ps)) < 0.70

    def test_a_true_null_is_usually_not_rejected(self):
        """Not a size study — those live in the module docstring — but the
        cheapest possible guard against a p-value that is small by default."""
        rejects = 0
        for s in range(20):
            r = sharpe_difference_test(*mixture(n=800, w=0.7, seed=100 + s), resamples=200, seed=s)
            rejects += r["significant"]
        assert rejects <= 5

    def test_the_bootstrap_and_the_normal_agree_on_a_long_clean_sample(self):
        a, b = mixture(n=2000, edge=0.0004, seed=18)
        r = sharpe_difference_test(a, b, resamples=1000, seed=18)
        assert abs(r["p_value"] - r["p_value_normal"]) < 0.10

    def test_more_resamples_do_not_move_the_point_estimates(self):
        a, b = mixture(seed=19)
        few = sharpe_difference_test(a, b, resamples=200, seed=19)
        many = sharpe_difference_test(a, b, resamples=1000, seed=19)
        assert few["difference"] == many["difference"]
        assert few["standard_error"] == many["standard_error"]
        assert few["resamples"] == 200 and many["resamples"] == 1000


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


class TestGuards:
    def test_too_short_degrades_rather_than_guessing(self):
        a, b = mixture(n=MIN_BARS - 1, seed=20)
        r = sharpe_difference_test(a, b, resamples=100, seed=20)
        assert r["computable"] is False
        assert str(MIN_BARS) in r["reason"]
        assert r["bars"] == MIN_BARS - 1

    def test_exactly_the_floor_computes(self):
        a, b = mixture(n=MIN_BARS, seed=20)
        assert sharpe_difference_test(a, b, resamples=100, seed=20)["computable"]

    def test_a_strategy_that_never_moves_has_no_sharpe(self):
        b = noise(seed=21)
        flat = pd.Series(0.0, index=b.index)
        r = sharpe_difference_test(flat, b, resamples=100, seed=21)
        assert r["computable"] is False
        assert "strategy" in r["reason"]

    def test_a_benchmark_that_never_moves_says_so_instead(self):
        a = noise(seed=22)
        flat = pd.Series(0.0, index=a.index)
        r = sharpe_difference_test(a, flat, resamples=100, seed=22)
        assert r["computable"] is False
        assert "buy-and-hold" in r["reason"]

    def test_nan_bars_are_dropped_in_pairs(self):
        a, b = mixture(n=400, seed=23)
        a = a.copy()
        a.iloc[5:15] = np.nan
        r = sharpe_difference_test(a, b, resamples=100, seed=23)
        assert r["bars"] == 390
        # The benchmark's matching bars went with them, not just the strategy's.
        kept = b.to_numpy()[np.isfinite(a.to_numpy())]
        assert r["benchmark_sharpe"] == pytest.approx(
            kept.mean() / kept.std(ddof=0) * math.sqrt(TRADING_DAYS), abs=5e-5
        )

    def test_mismatched_series_are_refused(self):
        a, b = mixture(n=400, seed=24)
        with pytest.raises(ValueError, match="same bars"):
            sharpe_difference_test(a.iloc[:-1], b, resamples=100)
        shifted = pd.Series(b.to_numpy(), index=index(400).shift(1, freq="B"))
        with pytest.raises(ValueError, match="share an index"):
            sharpe_difference_test(a, shifted, resamples=100)

    def test_resamples_must_be_positive(self):
        a, b = mixture(n=400, seed=25)
        with pytest.raises(ValueError, match="resamples must be positive"):
            sharpe_difference_test(a, b, resamples=0)

    def test_the_block_says_what_was_tested(self):
        a, b = mixture(seed=26)
        r = sharpe_difference_test(a, b, resamples=200, seed=26)
        assert r["test"] == "ledoit_wolf_2008"
        assert r["benchmark"] == "buy_and_hold"
        assert r["alpha"] == ALPHA
        assert r["block_length"] >= 1
        assert "sqrt(252)" in r["sharpe_definition"]
        assert "Two-sided" in r["note"]
