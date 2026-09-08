"""Tests for block bootstrap confidence intervals.

A bootstrap always returns an interval, and any interval looks plausible, so
these pin the properties that separate a correct one from a decorative one:
that the vectorised metrics are the same function the rest of the app reports,
that the block length reduces to the closed form it is known to reduce to, that
the resampler has the geometric block structure it claims, and that the seed is
stable across processes rather than merely within one.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bootstrap import (
    EXCLUDED,
    MIN_EXPECTED_BLOCKS,
    MIN_OBS,
    UNDERSTATED,
    _bca_interval,
    _block_jackknife,
    bootstrap_metrics,
    choose_block_length,
    metrics_matrix,
    politis_white_block_length,
    stable_seed,
    stationary_bootstrap_indices,
)
from metrics import compute_metrics


def _noise(n=600, seed=0, mu=0.0005, sigma=0.011):
    return np.random.default_rng(seed).normal(mu, sigma, n)


def _ar1(n, rho, seed, sigma=0.011):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = rho * x[i - 1] + e[i]
    return x


def _garch(n, seed, omega=2e-6, alpha=0.09, beta=0.89):
    """Uncorrelated returns with clustered volatility — the shape a real
    strategy return series has, and the case the second block-length arm exists
    for."""
    rng = np.random.default_rng(seed)
    var = omega / (1 - alpha - beta)
    out = np.zeros(n)
    for i in range(n):
        out[i] = rng.normal(0.0, np.sqrt(var))
        var = omega + alpha * out[i] ** 2 + beta * var
    return out


# ---------------------------------------------------------------------------
# The vectorised metrics must BE the reported metrics
# ---------------------------------------------------------------------------

def test_matrix_agrees_with_compute_metrics():
    """The whole point of an interval is that it wraps the number printed beside
    it. If these two ever drift, the band describes a statistic nobody is
    looking at, which is worse than showing no band at all.

    Tolerance is 1e-6 because compute_metrics rounds its output to six decimals;
    that rounding, not the arithmetic, is the floor here.
    """
    returns = pd.Series(_noise(800, seed=4))
    equity = (1 + returns).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()
    reference = compute_metrics(returns, equity, drawdown, pd.Series(np.ones(len(returns))))

    mine = metrics_matrix(returns.to_numpy().reshape(1, -1))
    for name, values in mine.items():
        assert float(values[0]) == pytest.approx(reference[name], abs=1e-6), name


def test_every_bootstrapped_metric_exists_in_compute_metrics():
    """Guards against an interval being offered for a metric the app never shows."""
    returns = pd.Series(_noise(300, seed=5))
    equity = (1 + returns).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()
    reference = compute_metrics(returns, equity, drawdown, pd.Series(np.ones(len(returns))))
    for name in metrics_matrix(returns.to_numpy().reshape(1, -1)):
        assert name in reference


def test_rows_are_independent():
    """A vectorised reduction that leaks across rows would make every replicate
    look like its neighbour and shrink the interval toward nothing."""
    a, b = _noise(300, seed=6), _noise(300, seed=7)
    together = metrics_matrix(np.vstack([a, b]))
    apart_a = metrics_matrix(a.reshape(1, -1))
    apart_b = metrics_matrix(b.reshape(1, -1))
    for name in together:
        assert together[name][0] == pytest.approx(apart_a[name][0])
        assert together[name][1] == pytest.approx(apart_b[name][0])


def test_annualised_return_is_pinned_at_total_loss_when_equity_goes_negative():
    """A levered bar worse than -100% puts the base of the annualisation below
    zero, where there is no real answer. Total loss is the only sensible value,
    and the alternative is a complex number.

    Checked against compute_metrics rather than only asserted here: this case is
    the one place the two implementations could plausibly disagree, since each
    has to make the same arbitrary-looking choice independently.
    """
    wiped = pd.Series([0.0, -1.5, 0.1, 0.05, 0.02])
    equity = (1 + wiped).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()
    reference = compute_metrics(wiped, equity, drawdown, pd.Series(np.ones(len(wiped))))

    out = metrics_matrix(wiped.to_numpy().reshape(1, -1))
    assert out["annualized_return"][0] == -1.0
    assert out["annualized_return"][0] == reference["annualized_return"]


# ---------------------------------------------------------------------------
# Block length
# ---------------------------------------------------------------------------

def test_white_noise_wants_no_block():
    """Independent data should get an ordinary iid bootstrap. Forcing a longer
    block on it only adds variance to the estimate."""
    for seed in range(5):
        assert politis_white_block_length(_noise(1200, seed=seed)) < 2.0


@pytest.mark.parametrize("rho", [0.2, 0.5, 0.8])
def test_matches_the_ar1_closed_form(rho):
    """Politis-White reduces to (2r / (1 - r^2))^(2/3) * n^(1/3) for an AR(1).
    That is the check that the flat-top weights, the doubling for negative lags
    and the exponents are all right — several plausible wrong versions of this
    formula still return a sensible-looking number.

    The estimator runs slightly low in finite samples because the taper truncates
    the ACF tail, so the tolerance is one-sided and generous below.
    """
    n = 2000
    estimate = np.mean([politis_white_block_length(_ar1(n, rho, seed=s)) for s in range(6)])
    closed_form = (2 * rho / (1 - rho ** 2)) ** (2 / 3) * n ** (1 / 3)
    assert 0.6 * closed_form <= estimate <= 1.25 * closed_form


def test_block_length_grows_with_dependence():
    lengths = [
        np.mean([politis_white_block_length(_ar1(1500, rho, seed=s)) for s in range(4)])
        for rho in (0.0, 0.3, 0.6, 0.85)
    ]
    assert lengths == sorted(lengths)


def test_volatility_clustering_drives_the_choice():
    """The reason there are two arms. A GARCH series is serially uncorrelated in
    the mean, so the returns arm sees nothing; the dependence that matters for a
    Sharpe or a drawdown lives in the second moment."""
    out = choose_block_length(_garch(1500, seed=8))
    assert out["from_returns"] < 3.0
    assert out["from_squared_returns"] > 10.0
    assert out["block_length"] == min(round(out["from_squared_returns"]), out["ceiling"])


def test_block_length_leaves_enough_blocks():
    """Past a point the resample is a reshuffle of a handful of chunks and every
    replicate looks the same."""
    for n in (200, 800, 3000):
        out = choose_block_length(_ar1(n, 0.95, seed=9))
        assert out["expected_blocks"] >= MIN_EXPECTED_BLOCKS - 1
        assert out["block_length"] <= max(2, n // MIN_EXPECTED_BLOCKS)


def test_capped_flag_is_reported_when_it_bites():
    out = choose_block_length(_ar1(300, 0.97, seed=10))
    assert out["capped"] == (out["block_length"] == out["ceiling"])


# ---------------------------------------------------------------------------
# The resampler
# ---------------------------------------------------------------------------

def test_indices_are_in_range_and_shaped():
    idx = stationary_bootstrap_indices(500, 10, 40, np.random.default_rng(11))
    assert idx.shape == (40, 500)
    assert idx.min() >= 0 and idx.max() < 500


@pytest.mark.parametrize("block_length", [2, 5, 20, 50])
def test_block_continuation_rate_matches_the_geometric_construction(block_length):
    """Blocks are geometric with mean L, so a step continues the previous block
    with probability 1 - 1/L. Measuring it catches an off-by-one in the
    probability, which no amount of eyeballing the output would."""
    n = 4000
    idx = stationary_bootstrap_indices(n, block_length, 30, np.random.default_rng(12))
    continued = (idx[:, 1:] == (idx[:, :-1] + 1) % n)
    # A "new block" can land on the continuing index by chance, at rate 1/n.
    assert continued.mean() == pytest.approx(1 - 1 / block_length, abs=0.02)


def test_block_length_one_is_an_iid_bootstrap():
    n = 2000
    idx = stationary_bootstrap_indices(n, 1, 20, np.random.default_rng(13))
    continued = (idx[:, 1:] == (idx[:, :-1] + 1) % n)
    assert continued.mean() < 0.01


def test_resampling_wraps_circularly():
    """Without the wrap the last bars would be drawn less often than the rest,
    quietly weighting the sample toward its own beginning."""
    n = 50
    idx = stationary_bootstrap_indices(n, 25, 200, np.random.default_rng(14))
    wrapped = (idx[:, 1:] == 0) & (idx[:, :-1] == n - 1)
    assert wrapped.any()


def test_resample_preserves_the_multiset_of_values():
    """Every drawn value must come from the original series — a bootstrap that
    invents observations is not a bootstrap."""
    data = _noise(300, seed=15)
    idx = stationary_bootstrap_indices(300, 8, 10, np.random.default_rng(16))
    assert np.isin(data[idx], data).all()


# ---------------------------------------------------------------------------
# Jackknife
# ---------------------------------------------------------------------------

def test_jackknife_samples_are_all_the_same_length():
    """They must be, or the annualisation exponent (252 / n) differs between
    them and part of the spread being measured is the spread of a different
    formula. np.array_split does not guarantee this and getting it wrong is
    silent — the first version of this module crashed on the stacking instead,
    which was luck."""
    n = 1003
    width = 7
    blocks = sorted({min(i * width, n - width) for i in range(int(np.ceil(n / width)))})
    lengths = {len(np.delete(np.arange(n), np.arange(s, s + width))) for s in blocks}
    assert lengths == {n - width}


def test_jackknife_deletions_cover_the_final_bar():
    """The last block is shifted back to end on the final bar. Leaving the tail
    in every sample would make the jackknife blind to it."""
    n, width = 1003, 7
    blocks = sorted({min(i * width, n - width) for i in range(int(np.ceil(n / width)))})
    covered = set()
    for s in blocks:
        covered.update(range(s, s + width))
    assert covered == set(range(n))


def test_jackknife_declines_when_there_are_too_few_blocks():
    assert _block_jackknife(_noise(40, seed=17), block_length=15) is None


def test_jackknife_returns_one_value_per_block():
    data = _noise(600, seed=18)
    out = _block_jackknife(data, block_length=20)
    assert out is not None
    assert len(out["sharpe_ratio"]) == 30


# ---------------------------------------------------------------------------
# Intervals
# ---------------------------------------------------------------------------

def test_interval_always_contains_the_point_estimate():
    for seed in range(4):
        out = bootstrap_metrics(_noise(500, seed=seed), n_resamples=300, seed=seed)
        for name, entry in out["metrics"].items():
            assert entry["low"] <= entry["point"] <= entry["high"], name


def test_bca_falls_back_to_percentile_when_it_is_undefined():
    """If the bootstrap distribution never straddles the observed value the bias
    correction is an infinite Normal quantile. Falling back is correct; raising
    or returning inf is not."""
    replicates = np.full(500, 2.0)
    out = _bca_interval(observed=1.0, replicates=replicates, jackknife=None, confidence=0.95)
    assert out["method"] == "percentile"
    assert np.isfinite(out["low"]) and np.isfinite(out["high"])


def test_degenerate_when_almost_every_replicate_is_unusable():
    out = _bca_interval(
        observed=1.0,
        replicates=np.full(10, np.nan),
        jackknife=None,
        confidence=0.95,
    )
    assert out["method"] == "degenerate"
    assert out["low"] == out["high"] == 1.0


def test_intervals_narrow_as_the_sample_grows():
    widths = []
    for n in (200, 800, 3200):
        out = bootstrap_metrics(_noise(n, seed=19), n_resamples=400, seed=1)
        entry = out["metrics"]["avg_daily_return"]
        widths.append(entry["high"] - entry["low"])
    assert widths[0] > widths[1] > widths[2]


def test_dependence_widens_the_interval():
    """A positively autocorrelated series carries less information per bar than
    an independent one of the same length, and the interval has to say so. This
    is the reason the bootstrap is blocked at all."""
    independent = bootstrap_metrics(_noise(1500, seed=20), n_resamples=500, seed=2)
    dependent = bootstrap_metrics(_ar1(1500, 0.6, seed=20) + 0.0005, n_resamples=500, seed=2)
    assert dependent["block"]["block_length"] > independent["block"]["block_length"]
    assert (
        dependent["metrics"]["avg_daily_return"]["std_error"]
        > independent["metrics"]["avg_daily_return"]["std_error"]
    )


# ---------------------------------------------------------------------------
# What the interval is FOR
# ---------------------------------------------------------------------------

def test_a_real_edge_excludes_the_null():
    strong = np.random.default_rng(21).normal(0.0012, 0.006, 1500)
    out = bootstrap_metrics(strong, n_resamples=600, seed=3)
    assert out["metrics"]["sharpe_ratio"]["excludes_null"] is True


def test_pure_noise_does_not_exclude_the_null():
    """The single most useful thing this module does: refuse to call a lucky
    backtest an edge. A zero-drift series can still show a positive Sharpe, and
    the interval is what says it means nothing."""
    misses = 0
    for seed in range(8):
        out = bootstrap_metrics(
            np.random.default_rng(100 + seed).normal(0.0, 0.011, 1200),
            n_resamples=500,
            seed=seed,
        )
        misses += out["metrics"]["sharpe_ratio"]["excludes_null"]
    # At a nominal 95% interval, ~1 in 20 will exclude zero by chance.
    assert misses <= 2


def test_null_values_are_metric_appropriate():
    """Zero is not the null for every metric. Profit factor's is 1.0, and
    volatility, drawdown and win rate have none at all — flagging a 47% win rate
    against 0.5 would teach the reader something false, since trend strategies
    win less than half their trades and still make money."""
    out = bootstrap_metrics(_noise(500, seed=22), n_resamples=300, seed=4)
    assert out["metrics"]["profit_factor"]["null_value"] == 1.0
    assert out["metrics"]["sharpe_ratio"]["null_value"] == 0.0
    for name in ("annualized_volatility", "max_drawdown", "win_rate"):
        assert out["metrics"][name]["null_value"] is None
        assert "excludes_null" not in out["metrics"][name]


def test_extremes_and_trade_count_get_no_interval():
    """A resample draws only from days that happened, so an interval for the
    worst day stops at the worst day already seen — it would understate tail
    risk exactly where it matters."""
    out = bootstrap_metrics(_noise(500, seed=23), n_resamples=300, seed=5)
    for name in ("best_day", "worst_day", "num_trades"):
        assert name not in out["metrics"]
        assert name in out["excluded"] and len(out["excluded"][name]) > 40


def test_measured_underreporting_is_flagged():
    """Both of these were measured at 70% and 79% coverage against a nominal
    95%, so they carry a warning rather than being quietly shown as equals."""
    out = bootstrap_metrics(_noise(500, seed=24), n_resamples=300, seed=6)
    flagged = {k for k, v in out["metrics"].items() if v["reliability"] == "understates"}
    assert flagged == set(UNDERSTATED)
    for name in flagged:
        assert out["metrics"][name]["reliability_note"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_seed_gives_the_same_interval():
    """A confidence interval that moves every time the page reloads is worse
    than none — it teaches the reader that the number is arbitrary."""
    data = _noise(600, seed=25)
    assert (
        bootstrap_metrics(data, n_resamples=300, seed=77)["metrics"]
        == bootstrap_metrics(data, n_resamples=300, seed=77)["metrics"]
    )


def test_different_seeds_give_different_intervals():
    data = _noise(600, seed=26)
    a = bootstrap_metrics(data, n_resamples=300, seed=1)["metrics"]["sharpe_ratio"]
    b = bootstrap_metrics(data, n_resamples=300, seed=2)["metrics"]["sharpe_ratio"]
    assert (a["low"], a["high"]) != (b["low"], b["high"])
    assert a["point"] == b["point"]


def test_stable_seed_survives_a_new_interpreter():
    """The reason this is hashlib and not the builtin `hash`: hash on a str is
    salted per process, so a seed built from it changes on every restart and the
    'deterministic' interval silently is not. Only a subprocess can catch it —
    within one interpreter the salt is fixed and a broken version passes.
    """
    backend = str(Path(__file__).resolve().parent.parent)
    code = (
        "import sys; sys.path.insert(0, %r); "
        "from bootstrap import stable_seed; print(stable_seed('AAPL', '2019-01-01', 42))"
        % backend
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, check=True,
            env={"PYTHONHASHSEED": "random", "PATH": ""},
        ).stdout.strip()
        for _ in range(3)
    }
    assert len(runs) == 1
    assert runs.pop() == str(stable_seed("AAPL", "2019-01-01", 42))


def test_stable_seed_separates_different_runs():
    assert stable_seed("AAPL", "2019-01-01") != stable_seed("MSFT", "2019-01-01")
    assert stable_seed("AAPL", "2019-01-01") != stable_seed("AAPL", "2019-01-02")


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def test_too_short_a_series_is_refused_with_a_reason():
    out = bootstrap_metrics(_noise(MIN_OBS - 1, seed=27))
    assert out["available"] is False
    assert str(MIN_OBS) in out["reason"]


def test_a_strategy_that_never_traded_is_refused():
    out = bootstrap_metrics(np.zeros(400))
    assert out["available"] is False
    assert "never took a position" in out["reason"]


def test_nans_are_treated_as_flat_days():
    data = _noise(400, seed=28)
    with_nan = data.copy()
    with_nan[5] = np.nan
    clean = data.copy()
    clean[5] = 0.0
    assert (
        bootstrap_metrics(with_nan, n_resamples=200, seed=8)["metrics"]
        == bootstrap_metrics(clean, n_resamples=200, seed=8)["metrics"]
    )


def test_accepts_a_pandas_series_identically_to_an_array():
    data = _noise(400, seed=29)
    assert (
        bootstrap_metrics(pd.Series(data), n_resamples=200, seed=9)["metrics"]
        == bootstrap_metrics(data, n_resamples=200, seed=9)["metrics"]
    )


@pytest.mark.parametrize("kwargs", [{"confidence": 1.0}, {"confidence": 0.2}, {"n_resamples": 50}])
def test_nonsense_arguments_raise(kwargs):
    with pytest.raises(ValueError):
        bootstrap_metrics(_noise(400, seed=30), **kwargs)


def test_reported_settings_describe_what_actually_ran():
    out = bootstrap_metrics(_noise(700, seed=31), n_resamples=500, confidence=0.9, seed=12)
    assert out["n_resamples"] == 500
    assert out["confidence"] == 0.9
    assert out["n_obs"] == 700
    assert out["seed"] == 12
    assert out["block"]["block_length"] >= 1


def test_a_narrower_confidence_level_gives_a_narrower_interval():
    data = _garch(900, seed=32) + 0.0005
    wide = bootstrap_metrics(data, n_resamples=600, confidence=0.99, seed=13)
    tight = bootstrap_metrics(data, n_resamples=600, confidence=0.80, seed=13)
    for name in ("sharpe_ratio", "avg_daily_return", "total_return"):
        w = wide["metrics"][name]
        t = tight["metrics"][name]
        assert (w["high"] - w["low"]) > (t["high"] - t["low"]), name


def test_excluded_and_understated_reasons_are_all_present():
    assert set(EXCLUDED) == {"best_day", "worst_day", "num_trades"}
    assert all(len(v) > 40 for v in EXCLUDED.values())
    assert all(len(v) > 40 for v in UNDERSTATED.values())
