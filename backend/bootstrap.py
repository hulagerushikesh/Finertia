"""Block bootstrap confidence intervals for every backtest metric.

A backtest reports a Sharpe of 1.2 the same way a ruler reports 30cm: as if the
number were the property of the strategy. It is not. It is one draw from one
sample path, and a different five years — or the same five years in a slightly
different order — would have produced a different number. Without a band around
it there is no way to tell a strategy with an edge from one that got a good run,
which is the single most common way a backtest misleads the person who ran it.

This module resamples the realised return series and recomputes every metric on
each resample, giving an interval instead of a point.

Why *block* and not plain iid resampling
----------------------------------------
Drawing individual days with replacement assumes the days are independent. They
are not, in two ways that matter here and pull in opposite directions:

  - Strategy returns are position x price return. Price returns are close to
    serially uncorrelated, so a naive ACF of the strategy's own returns often
    says "no dependence, block length 1" even when the strategy holds a trade
    for thirty bars.
  - Volatility clusters. The ACF of *squared* returns is strongly positive even
    when the ACF of returns is flat, and it is the second moment that drives the
    uncertainty in a Sharpe, a volatility and a drawdown.

So the block length is chosen from both series and the longer horizon wins. See
`choose_block_length`.

The resampler is the stationary bootstrap of Politis and Romano (1994): block
lengths are geometric with mean L rather than fixed at L, and the series wraps
circularly. Fixed-length blocks make the resampled series non-stationary — the
observations near a block boundary have different dependence properties from the
ones in the middle — and the geometric construction removes that artefact.

Intervals are BCa (bias-corrected and accelerated, Efron 1987), which corrects
both for a bootstrap distribution that is not centred on the observed statistic
and for a statistic whose variance changes with its own level — true of every
ratio here. The acceleration term needs a jackknife, and for dependent data the
delete-one-*observation* jackknife is invalid (Kuensch 1989); this uses a
delete-one-*block* jackknife, which is also ~L times cheaper.

Does it actually work
---------------------
Coverage was simulated rather than assumed: 300 independent GARCH(1,1) paths of
1250 bars, nominal 95% interval, target = the same statistic's population value
at that sample length. `boot se / true sd` is how much of the real sampling
spread the resample reproduces.

    metric                  coverage   boot se / true sd
    total_return               92.7%          101%
    annualized_return          92.7%           95%
    annualized_volatility      69.7%           56%   <- flagged
    sharpe_ratio               93.0%           95%
    max_drawdown               79.0%           84%   <- flagged
    calmar_ratio               95.0%          100%
    win_rate                   94.0%           95%
    profit_factor              92.7%           95%
    avg_daily_return           92.7%           95%

Seven of the nine land at 92.7-95.0%, mildly anticonservative in the way BCa
usually is at this sample size. Two do not, and the reasons are structural
rather than fixable by tuning -- see UNDERSTATED.

Pure numpy and stdlib, like the rest of the engine.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

# The project's only Normal CDF and quantile function. Reaching across for two
# module-private names is better than a second copy of Acklam's coefficients,
# which would be a genuine correctness risk if only one copy were ever fixed.
from deflated import _norm_cdf, _norm_ppf

TRADING_DAYS = 252

DEFAULT_RESAMPLES = 1000
DEFAULT_CONFIDENCE = 0.95

# Below this many bars the interval is wider than it is informative and the
# block structure has nothing to work with — roughly a quarter of a trading year.
MIN_OBS = 60

# Resamples are generated and reduced in chunks so peak memory stays flat. A
# (1000, 1250) float64 matrix is 10MB and three of them exist at once during the
# metric computation; the service runs with --memory 512Mi and --max-instances 2,
# so holding the whole thing would be a needless third of one instance's budget.
CHUNK = 250

# At least this many expected blocks, or the resample is a shuffle of a handful
# of chunks and every replicate looks like every other one.
MIN_EXPECTED_BLOCKS = 10


# ---------------------------------------------------------------------------
# Which metrics get an interval, and what "no effect" means for each
# ---------------------------------------------------------------------------
# The second element is the null value: the number the interval has to exclude
# before the metric is evidence of anything. It is deliberately None for three
# of them rather than defaulting to zero:
#
#   annualized_volatility — zero volatility is not a null hypothesis, it is a
#                           strategy that never traded.
#   max_drawdown          — same; every strategy that took a position has one.
#   win_rate              — 0.5 looks like the null and is not. A trend strategy
#                           wins 35% of the time and makes money, because the
#                           wins are larger. Flagging it against 0.5 would teach
#                           the reader the wrong lesson about their own results.
#
# profit_factor's null is 1.0, not 0 — it is a ratio of gains to losses.
BOOTSTRAPPED: tuple[tuple[str, float | None], ...] = (
    ("total_return", 0.0),
    ("annualized_return", 0.0),
    ("annualized_volatility", None),
    ("sharpe_ratio", 0.0),
    ("max_drawdown", None),
    ("calmar_ratio", 0.0),
    ("win_rate", None),
    ("profit_factor", 1.0),
    ("avg_daily_return", 0.0),
)

# Metrics deliberately left without an interval, with the reason kept next to
# them so it reaches the API response instead of living only in a comment.
EXCLUDED: dict[str, str] = {
    "best_day": (
        "A resample draws only from days that actually happened, so the interval "
        "can never reach past the best day already observed. It would be bounded "
        "by the statistic it is meant to bound."
    ),
    "worst_day": (
        "Same as best_day, and more dangerous: an interval for the worst day that "
        "stops at the worst day already seen understates tail risk exactly where "
        "it matters."
    ),
    "num_trades": (
        "The bootstrap resamples the return series, not the position path. Trades "
        "counted on a resample are block-boundary artefacts, not strategy behaviour."
    ),
}


# Metrics whose interval is measurably too narrow, with the measurement. Both
# are still shown -- a band that is known to be too narrow is more useful than
# no band, but only if it says so.
UNDERSTATED: dict[str, str] = {
    "annualized_volatility": (
        "Measured coverage 70% against a nominal 95%, reproducing 56% of the real "
        "sampling spread. Roughly half the variation in a five-year realised "
        "volatility comes from which volatility regime the period happened to sit "
        "in, and no resample of those same days can recreate a regime they did not "
        "contain. Forcing the block length from 25 to 250 bars moves the estimate "
        "from 0.0087 to 0.0104 against a true 0.0190, so this is not a tuning "
        "problem. The Sharpe escapes it because it is a ratio and the regime level "
        "largely cancels between numerator and denominator."
    ),
    "max_drawdown": (
        "Measured coverage 79% against a nominal 95%. A drawdown is built by the "
        "order of returns, and the resample only preserves order inside a block, so "
        "a decline that took longer than the block length to unfold cannot survive "
        "one. Read this interval as optimistic about long, slow declines."
    ),
}


def stable_seed(*parts: object) -> int:
    """Derive a reproducible 64-bit seed from the run's inputs.

    Deliberately hashlib and not the builtin `hash`: `hash` on a str is salted
    per interpreter process, so a seed built from it changes on every restart.
    The confidence interval would then move each time the page was reloaded,
    which is precisely the kind of instability that destroys trust in an
    uncertainty estimate.
    """
    joined = "|".join(repr(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(joined, digest_size=8).digest(), "big")


# ---------------------------------------------------------------------------
# Block length
# ---------------------------------------------------------------------------

def _autocorrelations(x: np.ndarray, max_lag: int) -> np.ndarray:
    """Sample autocorrelations rho(1..max_lag). rho(0) is 1 and is not returned."""
    centred = x - x.mean()
    denom = float(np.dot(centred, centred))
    if denom <= 0.0:
        return np.zeros(max_lag)
    return np.array([
        float(np.dot(centred[:-k], centred[k:])) / denom
        for k in range(1, max_lag + 1)
    ])


def _flat_top(t: np.ndarray) -> np.ndarray:
    """Politis-Romano flat-top lag window: 1 out to half the bandwidth, then a
    linear taper to zero. Flat near the origin so it does not shrink the short
    lags, which are the ones carrying the dependence."""
    a = np.abs(t)
    return np.where(a <= 0.5, 1.0, np.where(a <= 1.0, 2.0 * (1.0 - a), 0.0))


def politis_white_block_length(x: np.ndarray) -> float:
    """Automatic block length for the stationary bootstrap.

    Politis and White (2004), with the correction in Patton, Politis and White
    (2009). Minimises the asymptotic MSE of the bootstrap variance estimator:

        b_opt = ( 2 * G^2 / D )^(1/3) * n^(1/3)

        G = sum_k  lambda(k/M) * |k| * |rho(k)|
        D = 2 * ( sum_k lambda(k/M) * rho(k) )^2

    Checked against the closed form it is known to reduce to: for an AR(1) with
    coefficient r this gives (2r / (1 - r^2))^(2/3) * n^(1/3), and a test pins
    that. White noise gives G = 0 and therefore b = 0 -> block length 1, which
    is the right answer: independent data wants an ordinary iid bootstrap, and
    forcing a longer block on it only adds variance.

    The bandwidth M is chosen as twice the smallest lag beyond which the next
    K_N autocorrelations are all inside the 2*sqrt(log10(n)/n) band. That is the
    part my first attempt got wrong by using the band test directly as the block
    length: on squared returns the band is crossed for a hundred lags running,
    because volatility clustering is genuinely long-memory, so the rule
    saturated at its own cap and produced a block a tenth of the sample long.
    Here a wide M only means more lags enter a sum that is already weighted
    down by the taper.
    """
    n = len(x)
    if n < 16:
        return 1.0

    k_n = max(5, int(math.ceil(math.sqrt(math.log10(n)))))
    m_max = int(math.ceil(math.sqrt(n))) + k_n
    max_lag = min(n - 2, m_max + k_n)
    rho = _autocorrelations(x, max_lag)
    if not np.any(rho):
        return 1.0

    band = 2.0 * math.sqrt(math.log10(n) / n)
    m_hat = 0
    for lag in range(1, m_max + 1):
        window = rho[lag:lag + k_n]
        if len(window) < k_n:
            break
        if np.all(np.abs(window) < band):
            m_hat = lag
            break
    if m_hat == 0:
        m_hat = m_max

    bandwidth = min(2 * m_hat, max_lag)
    lags = np.arange(1, bandwidth + 1)
    weights = _flat_top(lags / bandwidth)
    r = rho[:bandwidth]

    # Both sums run over k = -M..M and rho is symmetric, so the positive-lag
    # sums are doubled; the k = 0 term is 0 in G and rho(0) = 1 in D.
    g_hat = 2.0 * float(np.sum(weights * lags * np.abs(r)))
    d_hat = 2.0 * (1.0 + 2.0 * float(np.sum(weights * r))) ** 2

    if g_hat <= 0.0 or d_hat <= 0.0:
        return 1.0
    return float((2.0 * g_hat ** 2 / d_hat) ** (1.0 / 3.0) * n ** (1.0 / 3.0))


def choose_block_length(returns: np.ndarray) -> dict:
    """Pick the expected block length, and show the working.

    Politis-White is run on two series, and the longer answer wins:

      returns          dependence in the returns themselves
      squared returns  volatility clustering

    The second arm exists because it is usually the binding one. A strategy
    return is position x price return; price returns are close to serially
    uncorrelated, so the first arm often reports "no dependence" even for a
    strategy that holds a trade for thirty bars. The uncertainty in a Sharpe, a
    volatility and a drawdown is driven by the second moment, and the ACF of
    squared returns sees it.
    """
    n = len(returns)

    from_returns = politis_white_block_length(returns)
    from_squared = politis_white_block_length(returns ** 2)

    # Patton's cap, plus a floor on how many blocks a resample must contain --
    # with fewer, every replicate is a reshuffle of the same handful of chunks
    # and the intervals collapse toward zero width.
    ceiling = max(2, min(int(math.ceil(3.0 * math.sqrt(n))), n // MIN_EXPECTED_BLOCKS))
    unclamped = max(from_returns, from_squared, 1.0)
    chosen = int(min(max(round(unclamped), 1), ceiling))

    return {
        "block_length": chosen,
        "from_returns": round(from_returns, 2),
        "from_squared_returns": round(from_squared, 2),
        "ceiling": int(ceiling),
        "capped": round(unclamped) > ceiling,
        "expected_blocks": round(n / chosen, 1),
    }


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------

def stationary_bootstrap_indices(
    n: int,
    block_length: float,
    size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix, shape (size, n).

    Each step either continues the previous block (index + 1, wrapping) or
    starts a new one at a uniformly random position, with probability 1/L of
    starting new. Block lengths are therefore geometric with mean L, and the
    resampled series is stationary — the property that fixed-length blocks lose.
    """
    if n < 1:
        raise ValueError("n must be positive")
    if block_length < 1:
        raise ValueError("block_length must be at least 1")

    p_new = 1.0 / block_length
    fresh = rng.integers(0, n, size=(size, n))
    start_new = rng.random((size, n)) < p_new

    idx = np.empty((size, n), dtype=np.int64)
    idx[:, 0] = fresh[:, 0]
    for t in range(1, n):
        idx[:, t] = np.where(start_new[:, t], fresh[:, t], idx[:, t - 1] + 1)
        # Wrap only where it is needed; the modulo on the whole column every
        # bar is the single most expensive line in this module otherwise.
        np.mod(idx[:, t], n, out=idx[:, t], where=idx[:, t] >= n)
    return idx


# ---------------------------------------------------------------------------
# Vectorised metrics
# ---------------------------------------------------------------------------

def metrics_matrix(returns: np.ndarray) -> dict[str, np.ndarray]:
    """Every bootstrapped metric, computed across the rows of a (B, n) matrix.

    Must agree with `metrics.compute_metrics` to floating-point tolerance — a
    test pins that on the identity resample. If the two ever drift, the interval
    stops describing the number printed beside it, which is worse than having no
    interval at all.
    """
    if returns.ndim != 2:
        raise ValueError("returns must be a 2-D (replicates, bars) array")
    n = returns.shape[1]
    if n < 2:
        raise ValueError("need at least 2 bars")

    equity = np.cumprod(1.0 + returns, axis=1)
    total_return = equity[:, -1] - 1.0

    # (1 + total)^(252/n) is a complex number when the base is negative, which
    # a levered path can reach. There is no real annualised return once equity
    # has gone through zero, so it is pinned at total loss.
    base = 1.0 + total_return
    annualized_return = np.where(
        base > 0.0,
        np.power(np.where(base > 0.0, base, 1.0), TRADING_DAYS / n) - 1.0,
        -1.0,
    )

    # ddof=1 to match pandas' Series.std default, which compute_metrics uses.
    annualized_volatility = returns.std(axis=1, ddof=1) * math.sqrt(TRADING_DAYS)

    sharpe_ratio = np.divide(
        annualized_return,
        annualized_volatility,
        out=np.zeros_like(annualized_return),
        where=annualized_volatility != 0.0,
    )

    running_max = np.maximum.accumulate(equity, axis=1)
    max_drawdown = ((equity - running_max) / running_max).min(axis=1)

    calmar_ratio = np.divide(
        annualized_return,
        np.abs(max_drawdown),
        out=np.zeros_like(annualized_return),
        where=max_drawdown != 0.0,
    )

    wins = (returns > 0.0).sum(axis=1)
    active = (returns != 0.0).sum(axis=1)
    win_rate = wins / np.maximum(active, 1)

    gains = np.where(returns > 0.0, returns, 0.0).sum(axis=1)
    losses = np.where(returns < 0.0, returns, 0.0).sum(axis=1)
    profit_factor = np.divide(
        gains,
        np.abs(losses),
        out=np.zeros_like(gains),
        where=losses != 0.0,
    )

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_daily_return": returns.mean(axis=1),
    }


# ---------------------------------------------------------------------------
# BCa
# ---------------------------------------------------------------------------

def _block_jackknife(returns: np.ndarray, block_length: int) -> dict[str, np.ndarray] | None:
    """Delete-one-block jackknife, the acceleration input for BCa.

    The delete-one-*observation* jackknife is not valid under serial dependence
    (Kuensch 1989) -- removing a single bar leaves the dependence on either side
    of the hole intact and understates how sensitive the statistic is. Deleting
    whole blocks is the dependent-data analogue.

    Two details that are easy to get wrong:

      Every sample must be the SAME length, or the annualisation exponent
      (252 / n) differs between them and the spread being measured is partly
      the spread of a different formula. np.array_split does not give equal
      blocks when the length is not divisible, so deletions are fixed-width and
      the last one is shifted back to end on the final bar -- it overlaps its
      neighbour by a few bars rather than leaving the tail permanently in every
      sample, which would make the jackknife blind to it.

      The deletion width is at least n/200, so a block length of 1 on
      independent data does not turn this into 1250 recomputations for a third
      moment that 200 estimates already pin down.
    """
    n = len(returns)
    width = max(block_length, int(math.ceil(n / 200)))
    n_blocks = int(math.ceil(n / width))
    if n_blocks < 4 or width >= n // 2:
        return None

    starts = sorted({min(i * width, n - width) for i in range(n_blocks)})
    samples = [np.delete(returns, np.arange(s, s + width)) for s in starts]
    return metrics_matrix(np.vstack(samples))


def _bca_interval(
    observed: float,
    replicates: np.ndarray,
    jackknife: np.ndarray | None,
    confidence: float,
) -> dict:
    """One BCa interval, falling back to percentile when BCa is undefined."""
    alpha = (1.0 - confidence) / 2.0
    finite = replicates[np.isfinite(replicates)]

    if len(finite) < 20:
        return {
            "low": float(observed),
            "high": float(observed),
            "std_error": 0.0,
            "method": "degenerate",
        }

    def percentile_interval() -> dict:
        return {
            "low": float(np.quantile(finite, alpha)),
            "high": float(np.quantile(finite, 1.0 - alpha)),
            "std_error": float(finite.std(ddof=1)),
            "method": "percentile",
        }

    # Bias correction: where the observed statistic sits in the bootstrap
    # distribution. At exactly 0 or 1 the Normal quantile is infinite, which
    # means the bootstrap never straddled the observed value and BCa has no
    # correction to make.
    share_below = float((finite < observed).mean())
    if share_below <= 0.0 or share_below >= 1.0:
        return percentile_interval()
    z0 = _norm_ppf(share_below)

    # Acceleration from the third moment of the jackknife values.
    if jackknife is None:
        acceleration = 0.0
    else:
        jack = jackknife[np.isfinite(jackknife)]
        if len(jack) < 4:
            acceleration = 0.0
        else:
            deviation = jack.mean() - jack
            sum_sq = float((deviation ** 2).sum())
            acceleration = (
                float((deviation ** 3).sum()) / (6.0 * sum_sq ** 1.5)
                if sum_sq > 0.0
                else 0.0
            )

    z_lo, z_hi = _norm_ppf(alpha), _norm_ppf(1.0 - alpha)

    def adjust(z: float) -> float | None:
        denom = 1.0 - acceleration * (z0 + z)
        if denom == 0.0:
            return None
        return _norm_cdf(z0 + (z0 + z) / denom)

    a_lo, a_hi = adjust(z_lo), adjust(z_hi)
    if a_lo is None or a_hi is None or not 0.0 < a_lo < a_hi < 1.0:
        return percentile_interval()

    return {
        "low": float(np.quantile(finite, a_lo)),
        "high": float(np.quantile(finite, a_hi)),
        "std_error": float(finite.std(ddof=1)),
        "method": "bca",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def bootstrap_metrics(
    net_return,
    *,
    n_resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
    seed: int = 0,
) -> dict:
    """Block bootstrap confidence intervals for a realised strategy return series.

    `net_return` is the per-bar net return the engine produced — the same series
    `metrics.compute_metrics` was given, so the intervals wrap the numbers the
    user is actually looking at.
    """
    if not 0.5 <= confidence < 1.0:
        raise ValueError("confidence must be in [0.5, 1.0)")
    if n_resamples < 100:
        raise ValueError("n_resamples must be at least 100")

    returns = np.asarray(
        net_return.to_numpy(dtype=float) if isinstance(net_return, pd.Series)
        else net_return,
        dtype=float,
    ).ravel()
    returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)
    n = len(returns)

    if n < MIN_OBS:
        return {
            "available": False,
            "reason": (
                f"{n} bars is too short to resample — intervals need at least "
                f"{MIN_OBS} to say anything the point estimate does not."
            ),
        }

    if not np.any(returns != 0.0):
        return {
            "available": False,
            "reason": "The strategy never took a position, so there is nothing to resample.",
        }

    block = choose_block_length(returns)
    block_length = block["block_length"]

    observed = {k: float(v[0]) for k, v in metrics_matrix(returns.reshape(1, n)).items()}

    rng = np.random.default_rng(seed)
    collected: dict[str, list[np.ndarray]] = {name: [] for name, _ in BOOTSTRAPPED}

    remaining = n_resamples
    while remaining > 0:
        size = min(CHUNK, remaining)
        idx = stationary_bootstrap_indices(n, block_length, size, rng)
        chunk_metrics = metrics_matrix(returns[idx])
        for name, _ in BOOTSTRAPPED:
            collected[name].append(chunk_metrics[name])
        remaining -= size

    replicates = {name: np.concatenate(parts) for name, parts in collected.items()}
    jackknife = _block_jackknife(returns, block_length)

    out: dict[str, dict] = {}
    for name, null_value in BOOTSTRAPPED:
        interval = _bca_interval(
            observed[name],
            replicates[name],
            jackknife[name] if jackknife is not None else None,
            confidence,
        )
        point = observed[name]
        # An interval that is not ordered around the point estimate is a bug
        # somewhere upstream, not a finding — widen rather than print a band
        # that excludes the number it belongs to.
        low = min(interval["low"], point)
        high = max(interval["high"], point)

        entry = {
            "point": round(point, 6),
            "low": round(low, 6),
            "high": round(high, 6),
            "std_error": round(interval["std_error"], 6),
            "method": interval["method"],
            "null_value": null_value,
            "reliability": "understates" if name in UNDERSTATED else "good",
        }
        if name in UNDERSTATED:
            entry["reliability_note"] = UNDERSTATED[name]
        if null_value is not None:
            # "Excludes the null" is the whole reason to show a band: an
            # interval on the Sharpe that contains zero means this backtest is
            # not evidence of an edge, however good the point estimate looks.
            entry["excludes_null"] = bool(low > null_value or high < null_value)
        out[name] = entry

    return {
        "available": True,
        "confidence": confidence,
        "n_resamples": n_resamples,
        "n_obs": n,
        "seed": seed,
        "method": "stationary block bootstrap (Politis-Romano), BCa intervals",
        "block": block,
        "metrics": out,
        "excluded": EXCLUDED,
        "caveats": [
            "Resampling reorders history. This measures how much of the result came "
            "from the order the returns arrived in -- not whether the strategy works "
            "on data it has never seen. Walk-forward is the test for that.",
            "Simulated coverage of the nominal 95% interval is 92.7-95.0% for seven "
            "of the nine metrics. Annualised volatility and max drawdown are "
            "measurably narrower than they should be and are marked as such.",
        ],
    }
