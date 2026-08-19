"""Deflated Sharpe Ratio — correcting the walk-forward sweep for its own selection bias.

Walk-forward validation here sweeps a parameter grid on the in-sample half and
keeps the combination with the highest Sharpe. That step is multiple testing,
and the maximum of N draws is biased upward even when every strategy is
worthless: with N independent trials of a strategy whose true Sharpe is zero,
the expected *best* Sharpe is strictly positive and grows with N. So the
in-sample number walk-forward reports is inflated by construction, and the tool
built to detect overfitting had that bias sitting inside its own detector.

This module implements the correction from Bailey and Lopez de Prado (2014),
"The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting
and Non-Normality". Two pieces:

  expected_max_sharpe()        How high a Sharpe you would expect from the best
                               of N trials on pure noise. The bar the selected
                               strategy has to clear.

  probabilistic_sharpe_ratio() Probability the true Sharpe exceeds a threshold,
                               accounting for sample length and for skew and
                               fat tails, both of which inflate a naive Sharpe.

  deflated_sharpe_ratio()      PSR measured against that noise bar rather than
                               against zero.

Pure numpy and stdlib, like the rest of the engine — including the two Normal
distribution functions, since scipy is not a dependency and adding one for two
functions would break the project's central constraint.
"""

from __future__ import annotations

import math

import numpy as np

# Euler-Mascheroni constant, from the expected-maximum derivation in the paper.
EULER_MASCHERONI = 0.5772156649015329

# Bars per year, matching the annualisation in metrics.compute_metrics.
TRADING_DAYS = 252


def _norm_cdf(x: float) -> float:
    """Standard Normal CDF. erf is exact enough and is in the stdlib."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# Acklam's rational approximation to the inverse Normal CDF. Relative error is
# below 1.15e-9 across the whole domain, which is far past what a probability
# reported to four decimals can show.
_A = (-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
      1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00)
_B = (-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
      6.680131188771972e01, -1.328068155288572e01)
_C = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
      -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00)
_D = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
      3.754408661907416e00)
_P_LOW = 0.02425
_P_HIGH = 1.0 - _P_LOW


def _norm_ppf(p: float) -> float:
    """Inverse standard Normal CDF (the quantile function)."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"probability must be strictly between 0 and 1, got {p}")

    if p < _P_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
               ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)

    if p > _P_HIGH:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
                ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)

    q = p - 0.5
    r = q * q
    return (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / \
           (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)


def expected_max_sharpe(sharpe_std: float, n_trials: int) -> float:
    """Expected highest Sharpe from `n_trials` strategies that have no real edge.

    From the paper's Eq. (1):

        SR* = sigma * [ (1 - g) * Z^-1(1 - 1/N)  +  g * Z^-1(1 - 1/(N*e)) ]

    where sigma is the standard deviation of Sharpe ratios across the trials, g
    is the Euler-Mascheroni constant, and Z^-1 is the Normal quantile function.
    The mean across trials is taken as zero, which is the null being tested: no
    strategy in the grid has any edge.

    `sharpe_std` must be in the same units as the Sharpe it will be compared
    against — per-observation here, never annualised.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be at least 1")
    if sharpe_std <= 0 or not math.isfinite(sharpe_std):
        # Every trial scored identically, so selection had nothing to exploit
        # and there is no inflation to remove.
        return 0.0
    if n_trials == 1:
        # One trial is not a selection, so the bar is zero. Guarding here
        # because Z^-1(1 - 1/1) = Z^-1(0) is undefined.
        return 0.0

    max_z = (
        (1.0 - EULER_MASCHERONI) * _norm_ppf(1.0 - 1.0 / n_trials)
        + EULER_MASCHERONI * _norm_ppf(1.0 - 1.0 / (n_trials * math.e))
    )
    return float(sharpe_std * max_z)


def probabilistic_sharpe_ratio(
    sharpe: float,
    benchmark: float,
    n_obs: int,
    skew: float,
    kurtosis: float,
) -> float:
    """Probability the true Sharpe exceeds `benchmark`, given the sample.

        PSR = Z[ (SR - SR*) * sqrt(T - 1) / sqrt(1 - g3*SR + (g4 - 1)/4 * SR^2) ]

    `kurtosis` is NON-EXCESS: a Normal distribution has 3, not 0. Passing excess
    kurtosis makes the denominator too small and the probability too confident.
    Sanity check on the formula: Normal returns give skew 0 and kurtosis 3, so
    the denominator collapses to sqrt(1 + SR^2 / 2), which is the standard error
    from Lo (2002).

    `sharpe` and `benchmark` are per-observation, matching `n_obs`.
    """
    if n_obs < 2:
        raise ValueError("need at least 2 observations")

    variance = 1.0 - skew * sharpe + ((kurtosis - 1.0) / 4.0) * sharpe**2
    if variance <= 0 or not math.isfinite(variance):
        # Extreme skew/kurtosis can drive the estimated variance non-positive,
        # which means the sample is too badly behaved for this approximation to
        # say anything. Refusing is better than returning a confident number.
        return float("nan")

    z = (sharpe - benchmark) * math.sqrt(n_obs - 1) / math.sqrt(variance)
    return float(_norm_cdf(z))


def deflated_sharpe_ratio(
    trial_sharpes,
    selected_returns,
    annualized: bool = True,
) -> dict:
    """Probability the selected strategy's edge survives the selection that found it.

    `trial_sharpes` is every Sharpe from the parameter sweep, and
    `selected_returns` the per-bar net returns of the combination that won.

    Set `annualized=False` if the Sharpes are already per-observation. They are
    annualised everywhere else in this codebase, and feeding an annualised
    Sharpe into a formula whose T counts daily bars overstates the statistic by
    about sqrt(252), which would let almost anything look significant.
    """
    trials = np.asarray([s for s in trial_sharpes if s is not None and math.isfinite(s)],
                        dtype=float)
    returns = np.asarray(selected_returns, dtype=float)
    returns = returns[np.isfinite(returns)]

    n_trials = int(trials.size)
    n_obs = int(returns.size)

    if n_trials == 0 or n_obs < 2:
        return {
            "computable": False,
            "reason": "Not enough trials or return observations to deflate.",
        }

    # Two separate factors, deliberately not one variable. `annualized`
    # describes the units the caller's TRIAL Sharpes arrive in; it says nothing
    # about how results should be reported. Reporting always annualises, so the
    # figures sit beside every other Sharpe in the app whichever way the trials
    # came in.
    trial_scale = math.sqrt(TRADING_DAYS) if annualized else 1.0
    report_scale = math.sqrt(TRADING_DAYS)
    trials_per_obs = trials / trial_scale

    std = float(returns.std(ddof=1))

    # Relative tolerance, not `std == 0`.
    #
    # Summing 500 copies of 0.001 does not give exactly 500 * 0.001, so a
    # perfectly flat return series lands at std ~4e-19 rather than 0. An exact
    # comparison lets that through, and the implied Sharpe comes out around
    # 2e15 — a flat line reported as the most significant strategy ever
    # measured. Scale the threshold to the data so the check survives returns
    # quoted in any unit.
    magnitude = float(np.abs(returns).max())
    if std <= max(magnitude, 1.0) * 1e-12:
        return {
            "computable": False,
            "reason": "The selected strategy's returns never vary, so it has no Sharpe to deflate.",
        }

    sharpe_obs = float(returns.mean() / std)

    # How often the strategy was actually in the market.
    #
    # PSR corrects for skew and fat tails, but it is still a moment-based
    # approximation and it stops meaning anything when the series is mostly
    # zeros. A Bollinger setting that fires on 3% of bars produced skew 30 and
    # kurtosis 959 in testing — one live day among a thousand flat ones — and
    # the formula will happily return a confident-looking probability for it.
    # A Sharpe ratio is not a meaningful summary of a series like that, so the
    # honest answer is to decline rather than to dress it up.
    active_bars = int(np.count_nonzero(returns))
    active_fraction = active_bars / n_obs

    # Population moments (ddof=0) — these describe the observed sample's shape,
    # not an estimate of a wider population.
    centered = returns - returns.mean()
    skew = float((centered**3).mean() / std**3)
    kurtosis = float((centered**4).mean() / std**4)  # non-excess: Normal is 3

    # ddof=1 across trials: the grid is a sample of the strategies that could
    # have been tried, not the entire population of them.
    sharpe_std = float(trials_per_obs.std(ddof=1)) if n_trials > 1 else 0.0

    sr_star = expected_max_sharpe(sharpe_std, n_trials)
    dsr = probabilistic_sharpe_ratio(sharpe_obs, sr_star, n_obs, skew, kurtosis)
    psr_vs_zero = probabilistic_sharpe_ratio(sharpe_obs, 0.0, n_obs, skew, kurtosis)

    # Thresholds are judgement calls, stated openly rather than buried: real
    # daily equity returns run a kurtosis of roughly 5 to 10, so 50 is far
    # outside anything the approximation was built for, and 30 active bars is
    # the same floor walk_forward already uses for a usable sample.
    unreliable = None
    if active_bars < 30:
        unreliable = (
            f"The selected parameters were in the market on only {active_bars} "
            f"of {n_obs} bars, which is too few for a Sharpe ratio to describe."
        )
    elif kurtosis > 50:
        unreliable = (
            f"Returns are dominated by a handful of bars (kurtosis {kurtosis:.0f}, "
            f"active on {active_fraction:.0%} of the period), so the moment-based "
            "correction cannot be trusted here."
        )

    return {
        "computable": True,
        "n_trials": n_trials,
        "n_obs": n_obs,
        # Reported annualised so they sit beside every other Sharpe in the app.
        "selected_sharpe": round(sharpe_obs * report_scale, 6),
        "expected_max_sharpe": round(sr_star * report_scale, 6),
        "sharpe_std_across_trials": round(sharpe_std * report_scale, 6),
        "skew": round(skew, 6),
        "kurtosis": round(kurtosis, 6),
        "active_bars": active_bars,
        "active_fraction": round(active_fraction, 6),
        "psr_vs_zero": None if math.isnan(psr_vs_zero) else round(psr_vs_zero, 6),
        "deflated_sharpe_ratio": None if math.isnan(dsr) else round(dsr, 6),
        "clears_noise_bar": bool(sharpe_obs > sr_star),
        "unreliable": unreliable,
        "verdict": "inconclusive" if unreliable else _dsr_verdict(dsr, sharpe_obs, sr_star),
    }


def _dsr_verdict(dsr: float, sharpe_obs: float, sr_star: float) -> str:
    """Plain reading of the deflated probability.

    0.95 is the conventional threshold in the paper. `noise` is called out
    separately from `not_significant` because they fail differently: one did not
    even beat what random selection produces, the other beat it but not by
    enough to rule out luck.
    """
    if math.isnan(dsr):
        return "inconclusive"
    if sharpe_obs <= sr_star:
        return "noise"
    if dsr >= 0.95:
        return "significant"
    if dsr >= 0.90:
        return "marginal"
    return "not_significant"
