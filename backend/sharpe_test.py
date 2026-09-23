"""Is the strategy's Sharpe *significantly* above buy-and-hold's?

Every backtest page prints two Sharpe ratios next to each other — the
strategy's and the benchmark's — and leaves the reader to decide whether the
gap means anything. Two numbers side by side invite exactly one comparison and
give no way to make it: 1.21 against 0.64 looks decisive until you notice the
two series share most of their bars and that the difference has a standard
error of 0.5. This module puts a p-value beside the pair.

The test is Ledoit and Wolf (2008), "Robust performance hypothesis testing
with the Sharpe ratio". The null is that the two Sharpe ratios are equal. What
makes it the right tool rather than a two-sample t-test:

  Dependent samples. The strategy trades the benchmark's own asset, so on any
  bar it is holding, its return IS the benchmark's return times a position.
  The two series are strongly correlated and the difference of their Sharpes
  has a much smaller standard error than two independent estimates would
  suggest. Treating them as independent throws away the pairing and makes the
  test far too conservative.

  Non-iid returns. Sharpe's own standard error under iid normality (Lo 2002,
  already used in deflated.py) assumes away the two features every daily
  return series has: autocorrelation and volatility clustering. Ledoit-Wolf
  replaces that with a HAC (heteroskedasticity and autocorrelation consistent)
  estimate of the long-run variance, which is agnostic about both.

  Small samples. The HAC statistic is asymptotically normal, and at a few
  hundred bars "asymptotically" is doing real work — the normal p-value is
  anticonservative. Ledoit-Wolf's remedy is a studentised bootstrap: resample
  the pair, recompute the statistic AND its standard error on each resample,
  and read the p-value off that distribution instead of off the normal. That
  bootstrap p-value is the headline here; the normal one is reported beside it
  so the gap between them is visible.

How the statistic is built
--------------------------
With a = strategy returns and b = benchmark returns on the same bars, the
Sharpe difference is a smooth function of four moments:

    Δ = f(μa, μb, γa, γb) = μa/√(γa − μa²) − μb/√(γb − μb²)

where γ is the second raw moment. The delta method turns the covariance of
those four moments into the variance of Δ:

    s²(Δ) = ∇f' Ψ ∇f / T

Ψ is the long-run covariance matrix of y_t = (a_t, b_t, a_t², b_t²). Because
∇f is a fixed vector, ∇f'Ψ∇f is just the long-run variance of the SCALAR
series u_t = ∇f'(y_t − ȳ) — so the whole HAC step is one-dimensional, which is
both cheaper and much easier to test than a 4×4 kernel estimate.

The kernel is Bartlett, with Andrews' (1991) automatic bandwidth from an AR(1)
fit to u. Bartlett is chosen over Parzen or QS for one property that matters
more here than efficiency: its long-run variance estimate is guaranteed
non-negative, so the test can never return an imaginary standard error on a
real return series. The bandwidth is estimated once, on the original sample,
and reused inside the bootstrap — the resamples are built from the original's
own blocks, so re-estimating on each would add noise without adding
information.

The resampler is the stationary bootstrap already used for the confidence
intervals (bootstrap.py), with the same block length chosen from both the
returns and their squares. Both series are resampled with the SAME index draw:
the pairing is the whole point, and drawing them separately would destroy the
correlation that makes this test worth running.

What is compared, exactly
-------------------------
Every bar in the backtest window, both series, no trimming — including the
strategy's warm-up, where it sits flat while the benchmark moves. That is
deliberate. The two Sharpe ratios printed on the page are computed over the
whole window, and a p-value that quietly tested a different period would not
belong beside them. If the warm-up is long enough to matter, it is a real cost
of the rule and it should be in both the number and the test.

One caveat the caller has to pass on: the Sharpe in here is the textbook one,
mean over standard deviation, annualised by √252. The dashboard's headline
Sharpe is the *geometric* variant, annualised return over annualised
volatility (metrics.py). The gap is not cosmetic — compounding loses about
half a variance to volatility drag, and on the canonical runs the arithmetic
figure sits 0.05 to 0.19 ABOVE the headline one (AAPL 2018→24 momentum: 0.59
here, 0.48 on the card). It always leans the same way, so if anything the
tested pair flatters the strategy. Show the pair that was tested next to the
p-value, and say which one it is.

Does it actually work
---------------------
Size and power were simulated rather than assumed, the way bootstrap.py's
coverage was. 500 paths of 1250 bars, GARCH(1,1) marginals, 1000 resamples.
The null is the mixture a = mu + w(b - mu) + sqrt(1-w^2)(c - mu), which has
the benchmark's own mean and variance and therefore exactly its Sharpe, while
correlating with it at w. (The tempting alternative — "hold the benchmark's
asset on a fraction f of the bars" — is not a null at all: such a strategy's
population Sharpe is sqrt(f) times the benchmark's, and no amount of leverage
changes that.)

    null, correlation with benchmark    reject @5%   reject @10%
    w = 0.9  (a strategy on its bars)      5.2%         10.8%
    w = 0.7                                6.8%         11.8%
    w = 0.0  (an unrelated asset)          8.8%         15.8%
    w = 0.7, 252 bars                      5.8%         10.0%

    alternative (1250 bars)             true gap    reject @5%
    +5%/yr mean                         +0.47 SR       27.8%
    +10%/yr mean                        +0.92 SR       74.4%
    +20%/yr mean                        +1.78 SR       98.8%

Mildly anticonservative, and most so in the case this module is least likely
to meet — a "benchmark" with no bars in common with the strategy. On the
realistic end, w = 0.9, it lands on nominal. Read 0.04 as "probably real" and
not as "1 in 25"; the bootstrap CIs carry the same caveat, for the same
reason.

The power column is the more useful half. A strategy needs roughly a full
point of Sharpe over five years before this test will call it, which is the
honest cost of five years being 1250 bars — and it is worth knowing before
reading a p of 0.3 as evidence of no edge.

One finding worth carrying: the automatic bandwidth comes out at a single lag
on the simulated pairs, and between 0 and 8 on the real ones. The influence
function is dominated by the gradient on the means, of order 1/sigma, while
the gradient on the second moments is of order mu/sigma^3 — some thirty times
smaller at daily frequency. So u is essentially the difference of the two
demeaned return series, and volatility clustering, which is what makes each
series persistent on its own, mostly cancels in that difference. What does not
cancel is a strategy that stays in a position for weeks: then the difference
IS autocorrelated, and the real runs where the bandwidth reaches 7 or 8 lags
are exactly the slow-turnover ones. The HAC term earns its place on those.

What it does not do. This is full-period, in-sample inference on one strategy
against one benchmark. It says nothing about the grid the parameters came from
— that is snooping.py's Reality Check and SPA — and nothing about whether the
edge persists, which is what walk-forward and the rolling folds are for. A
significant p-value here on a cell picked out of a hundred is still a
selection artefact; the checks are meant to be read together.
"""

import math

import numpy as np
import pandas as pd

from bootstrap import (
    TRADING_DAYS,
    choose_block_length,
    stationary_bootstrap_indices,
)

# Below this the HAC bandwidth rule and the bootstrap are both estimating more
# than the sample can support — half a trading year is the floor, and even at
# that length the p-value is a wide instrument. A year is where it settles.
MIN_BARS = 126

DEFAULT_RESAMPLES = 1000

# Resamples are built in chunks so the (resamples x bars) matrices stay in
# cache-friendly sizes rather than allocating hundreds of MB at once.
CHUNK = 250

# Andrews (1991) Bartlett constant: S_T = 1.1447 (alpha(1) T)^(1/3).
ANDREWS_BARTLETT = 1.1447

# An AR(1) coefficient arbitrarily close to 1 sends the bandwidth formula to
# infinity. Real return series never sit there; a degenerate resample can.
MAX_RHO = 0.97

ALPHA = 0.05


def _moments(a: np.ndarray, b: np.ndarray, axis: int = -1) -> tuple:
    """The four moments the Sharpe difference is a function of."""
    mu_a = a.mean(axis=axis)
    mu_b = b.mean(axis=axis)
    g_a = (a ** 2).mean(axis=axis)
    g_b = (b ** 2).mean(axis=axis)
    return mu_a, mu_b, g_a, g_b


def _difference(mu_a, mu_b, g_a, g_b):
    """Δ = SRa − SRb, per bar, from the four moments.

    Variances are taken as γ − μ², which is the sample variance with a divisor
    of T rather than T−1. The delta-method gradient below is the derivative of
    exactly this expression, so the two have to use the same convention.
    """
    var_a = g_a - mu_a ** 2
    var_b = g_b - mu_b ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return mu_a / np.sqrt(var_a) - mu_b / np.sqrt(var_b)


def _gradient(mu_a, mu_b, g_a, g_b) -> tuple:
    """∇f at the sample moments — Ledoit-Wolf (2008) eq. (9).

    ∂f/∂μa =  γa / (γa − μa²)^{3/2}
    ∂f/∂μb = −γb / (γb − μb²)^{3/2}
    ∂f/∂γa = −μa / (2 (γa − μa²)^{3/2})
    ∂f/∂γb =  μb / (2 (γb − μb²)^{3/2})
    """
    var_a = g_a - mu_a ** 2
    var_b = g_b - mu_b ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        pa = var_a ** 1.5
        pb = var_b ** 1.5
        return (g_a / pa, -g_b / pb, -mu_a / (2 * pa), mu_b / (2 * pb))


def _influence(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The scalar series u_t = ∇f'(y_t − ȳ) whose long-run variance is s²·T.

    Works on a single pair (1-D) or on a stack of resampled pairs (2-D, one
    pair per row); the moments are taken along the last axis either way.
    """
    mu_a, mu_b, g_a, g_b = _moments(a, b)
    d_mu_a, d_mu_b, d_g_a, d_g_b = _gradient(mu_a, mu_b, g_a, g_b)
    return (
        d_mu_a[..., None] * (a - mu_a[..., None])
        + d_mu_b[..., None] * (b - mu_b[..., None])
        + d_g_a[..., None] * (a ** 2 - g_a[..., None])
        + d_g_b[..., None] * (b ** 2 - g_b[..., None])
    )


def andrews_bandwidth(u: np.ndarray) -> float:
    """Automatic Bartlett bandwidth from an AR(1) approximation to u.

    Andrews (1991) table I: for the Bartlett kernel the MSE-optimal bandwidth
    is 1.1447 (α(1) T)^{1/3}, and for a single AR(1) series with coefficient ρ
    the plug-in α(1) collapses to 4ρ² / ((1−ρ)²(1+ρ)²) — the innovation
    variance cancels, so only the persistence matters.

    A series with no measurable persistence gives ρ = 0 and a bandwidth of 0,
    i.e. no lags at all, which is the right answer: the long-run variance of
    white noise is its variance.
    """
    n = len(u)
    if n < 3:
        return 0.0
    denom = float(np.sum(u[:-1] ** 2))
    if denom <= 0:
        return 0.0
    rho = float(np.sum(u[1:] * u[:-1]) / denom)
    rho = max(-MAX_RHO, min(MAX_RHO, rho))
    alpha = 4 * rho ** 2 / ((1 - rho) ** 2 * (1 + rho) ** 2)
    return ANDREWS_BARTLETT * (alpha * n) ** (1 / 3)


def _hac_variance(u: np.ndarray, lags: int) -> np.ndarray:
    """Bartlett-kernel long-run variance of u, along the last axis.

    γ0 + 2 Σ_{j=1..M} (1 − j/(M+1)) γj. The triangular weights are what make
    this non-negative for any series and any M, which is the reason Bartlett
    is used here rather than a kernel with a better convergence rate.
    """
    n = u.shape[-1]
    lrv = (u ** 2).mean(axis=-1)
    for j in range(1, min(lags, n - 1) + 1):
        cov = (u[..., j:] * u[..., :-j]).sum(axis=-1) / n
        lrv = lrv + 2 * (1 - j / (lags + 1)) * cov
    # Deliberately NOT clamped at zero. With these weights and this divisor the
    # estimator is a sum of squares and cannot go negative, so a clamp would
    # only ever hide a kernel that had stopped being Bartlett — which is the
    # single thing this function is chosen for.
    return lrv


def _normal_two_sided(z: float) -> float:
    """2(1 − Φ(|z|)) without scipy — Φ from the error function."""
    return float(math.erfc(abs(z) / math.sqrt(2)))


def _verdict(p_value: float, difference: float) -> str:
    if p_value >= ALPHA:
        return (
            "The gap between the two Sharpe ratios is inside what this much "
            "data can tell apart — it is not evidence of an edge."
        )
    if difference > 0:
        return (
            "The strategy's Sharpe is above buy-and-hold's by more than the "
            "noise in this sample can account for."
        )
    return (
        "The strategy's Sharpe is BELOW buy-and-hold's by more than the noise "
        "in this sample can account for."
    )


def sharpe_difference_test(
    strategy_return: pd.Series,
    benchmark_return: pd.Series,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int | None = None,
) -> dict:
    """Ledoit-Wolf test of SR(strategy) − SR(benchmark) on paired daily returns.

    Both series must share an index and cover the same bars; that pairing is
    what the test exploits. Returns a block with the two annualised Sharpe
    ratios, their difference, the HAC standard error, the normal p-value and
    the studentised-bootstrap p-value (the headline), or
    `{"computable": False, "reason": ...}` when the sample cannot support it.
    """
    if len(strategy_return) != len(benchmark_return):
        raise ValueError("the two return series must cover the same bars")
    if not strategy_return.index.equals(benchmark_return.index):
        raise ValueError("the two return series must share an index")
    if resamples < 1:
        raise ValueError("resamples must be positive")

    a = np.asarray(strategy_return, dtype=float)
    b = np.asarray(benchmark_return, dtype=float)
    finite = np.isfinite(a) & np.isfinite(b)
    a, b = a[finite], b[finite]
    n = len(a)

    if n < MIN_BARS:
        return {
            "computable": False,
            "reason": (
                f"{n} usable bars; the test needs at least {MIN_BARS} before "
                "its standard error means anything"
            ),
            "bars": n,
        }

    mu_a, mu_b, g_a, g_b = _moments(a, b)
    var_a, var_b = g_a - mu_a ** 2, g_b - mu_b ** 2
    if var_a <= 0 or var_b <= 0:
        which = "the strategy" if var_a <= 0 else "buy-and-hold"
        return {
            "computable": False,
            "reason": f"{which} never varies over this period, so it has no Sharpe ratio",
            "bars": n,
        }

    annualise = math.sqrt(TRADING_DAYS)
    sr_a = float(mu_a / math.sqrt(var_a)) * annualise
    sr_b = float(mu_b / math.sqrt(var_b)) * annualise
    difference = sr_a - sr_b

    u = _influence(a[None, :], b[None, :])[0]
    lags = int(min(andrews_bandwidth(u), n - 1))
    lrv = float(_hac_variance(u, lags))
    std_error = math.sqrt(lrv / n) * annualise if lrv > 0 else 0.0

    # Two series that are the same series have a difference of exactly zero and
    # no variance around it. That is not a failure of the test — it is the only
    # honest answer, p = 1, and it is the case a buy-and-hold "strategy" with
    # zero costs actually produces.
    if std_error <= 0 or not math.isfinite(std_error):
        if abs(difference) < 1e-12:
            return _result(
                n, sr_a, sr_b, 0.0, 0.0, lags, 0, 0,
                p_bootstrap=1.0, p_normal=1.0, statistic=0.0,
                note=(
                    "These two return series have the same Sharpe ratio by "
                    "construction — one is a fixed multiple of the other — so "
                    "there is no difference to test."
                ),
            )
        return {
            "computable": False,
            "reason": "the difference has no estimable standard error on this sample",
            "bars": n,
        }

    statistic = difference / std_error
    p_normal = _normal_two_sided(statistic)

    # Studentised bootstrap. Each resample draws ONE index path and applies it
    # to both series, preserving the bar-by-bar pairing, then recomputes both
    # the difference and its own standard error. Centring on the observed
    # difference is what makes the resampled statistic a draw from the null.
    block = choose_block_length(a)
    rng = np.random.default_rng(seed)
    exceed = 0
    drawn = 0
    target = abs(statistic)
    for start in range(0, resamples, CHUNK):
        size = min(CHUNK, resamples - start)
        idx = stationary_bootstrap_indices(n, block["block_length"], size, rng)
        ra, rb = a[idx], b[idx]
        m = _moments(ra, rb)
        diff_star = _difference(*m)
        se_star = np.sqrt(_hac_variance(_influence(ra, rb), lags) / n)
        with np.errstate(divide="ignore", invalid="ignore"):
            t_star = (diff_star - difference / annualise) / se_star
        # A resample with no estimable standard error cannot be compared with
        # the observed statistic, so it is counted as an exceedance rather than
        # dropped — the conservative direction, and it keeps the denominator
        # equal to the number of resamples actually requested.
        bad = ~np.isfinite(t_star)
        exceed += int(np.count_nonzero(bad)) + int(
            np.count_nonzero(np.abs(t_star[~bad]) >= target)
        )
        drawn += size

    p_bootstrap = (1 + exceed) / (drawn + 1)

    return _result(
        n, sr_a, sr_b, difference, std_error, lags,
        block["block_length"], drawn,
        p_bootstrap=p_bootstrap, p_normal=p_normal, statistic=statistic,
    )


def _result(
    bars, sr_a, sr_b, difference, std_error, lags, block_length, resamples,
    p_bootstrap, p_normal, statistic, note=None,
) -> dict:
    """One shape for every computable answer, so callers never branch on it."""
    return {
        "computable": True,
        "bars": int(bars),
        "strategy_sharpe": round(sr_a, 4),
        "benchmark_sharpe": round(sr_b, 4),
        "difference": round(difference, 4),
        "standard_error": round(std_error, 4),
        "statistic": round(statistic, 4),
        "p_value": round(p_bootstrap, 4),
        "p_value_normal": round(p_normal, 4),
        "significant": bool(p_bootstrap < ALPHA),
        "alpha": ALPHA,
        "hac_lags": int(lags),
        "block_length": int(block_length),
        "resamples": int(resamples),
        "test": "ledoit_wolf_2008",
        "benchmark": "buy_and_hold",
        "sharpe_definition": "mean / standard deviation of daily returns, x sqrt(252)",
        "verdict": note or _verdict(p_bootstrap, difference),
        "note": (
            "Two-sided: the null is that the two Sharpe ratios are equal, and a "
            "small p-value can mean either direction. The pair tested here is "
            "the arithmetic Sharpe; the headline figures on the page are the "
            "geometric variant, so they can differ slightly."
        ),
    }
