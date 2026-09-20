"""Whole-grid inference — does anything in the grid beat buy-and-hold, once
you account for having tried the whole grid?

Every other check in this folder reasons about the *winner*. The Deflated
Sharpe (deflated.py) asks whether the best cell clears the bar that selection
alone would clear; PBO (pbo.py) asks whether selecting on in-sample score is
better than picking at random. This module asks the question the way White
(2000) posed it: take every candidate at once, compare each with a benchmark,
and test the null that *none* of them is better — with the search itself
inside the bootstrap, so the maximum is compared with the distribution of a
maximum, not of a single draw.

Three readings of the same bootstrap, each answering a slightly different
question:

  Reality Check    White (2000). Statistic: the best mean excess return over
                   the benchmark, scaled by sqrt(T). Bootstrap the same
                   maximum with every candidate recentred to zero. The
                   p-value is the share of resampled maxima at or above the
                   observed one. Not studentised, so a candidate with a large
                   variance can dominate the maximum; and every candidate is
                   recentred to zero, so a grid padded with plainly bad cells
                   makes the test *less* likely to reject — the known
                   weakness Hansen fixed.

  SPA              Hansen (2005), "A Test for Superior Predictive Ability".
                   Studentised: each candidate's mean is divided by its own
                   bootstrap standard error, so the maximum is over t-ratios.
                   Poor candidates (t below -sqrt(2 log log T)) are left at
                   their negative sample mean instead of being recentred to
                   zero, so they cannot pad the null. Hansen also bounds the
                   consistent p-value from both sides — lower (every negative
                   mean kept) and upper (everything recentred, the RC
                   treatment) — and all three are reported.

  Romano-Wolf      Romano & Wolf (2005), stepdown. The two tests above say
                   whether *the best* survives. This says *which* candidates
                   do: rank by t-ratio, test the top against the maximum over
                   all, then the next against the maximum over the rest, and
                   so on, carrying the larger p forward so the sequence is
                   monotone. The result is one adjusted p-value per cell that
                   controls the family-wise error rate; the cells at or below
                   alpha are the ones that beat the benchmark after the search
                   is accounted for. §4 of open-questions.md asked for exactly
                   this — "which cells survive" rather than "does the best
                   cell survive".

What the comparison is. Each candidate's per-bar *excess* return over
buy-and-hold on the same bars, after transaction costs, over the full period
(the same matrix PBO uses, trimmed to the longest warm-up so no candidate
carries a flat run the others lack). The statistic is the mean excess return,
which is what the three papers test; a Sharpe version is possible but the
studentisation in SPA already brings the variance in. Buy-and-hold is the
benchmark because "beat the market" is the claim a user is implicitly making,
and because it is the one benchmark every grid shares.

What it does not do. This is full-period, in-sample inference with the
selection bias removed — it says whether the grid contains genuine
outperformance *over this period*, not whether it will persist; walk-forward
and the rolling folds answer persistence. And it inherits the bootstrap's
assumptions: stationarity within the resampling scheme, and a block length
that captures the dependence (chosen by Politis-White on the winner's excess
series, the same rule as bootstrap.py).

Pure numpy. The resampling comes from bootstrap.py so the block-length rule
and the stationary scheme are the ones every other interval on the page uses.
"""

from __future__ import annotations

import math

import numpy as np

from bootstrap import choose_block_length, stationary_bootstrap_indices
from deflated import TRADING_DAYS

# Fewer bars than this and the block bootstrap has nothing to resample from;
# matches the floor the confidence intervals use.
MIN_OBS = 60

# A candidate whose excess return has no bootstrap variance cannot be
# studentised. It is reported but excluded from the studentised tests.
_FLAT_TOL = 1e-12

DEFAULT_BOOTSTRAP = 1000
DEFAULT_ALPHA = 0.05


def _p(hits: np.ndarray) -> float:
    """(1 + #resamples at or beyond the observed) / (B + 1).

    The observed statistic counts as one draw from its own null, so a
    p-value is never exactly zero; with B = 1000 the floor is 0.001.
    """
    return float((1 + np.count_nonzero(hits)) / (len(hits) + 1))


def whole_grid_test(
    candidates: np.ndarray,
    benchmark: np.ndarray,
    labels: list[dict] | None = None,
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    alpha: float = DEFAULT_ALPHA,
    seed: int | None = None,
) -> dict:
    """Reality Check, SPA and Romano-Wolf stepdown over one candidate matrix.

    candidates  (T, N) per-bar net returns, one column per grid cell
    benchmark   (T,)   per-bar returns of the thing to beat, same bars
    labels      one dict per column, echoed back (the cell's parameters)
    """
    candidates = np.asarray(candidates, dtype=float)
    benchmark = np.asarray(benchmark, dtype=float)
    if candidates.ndim == 1:
        candidates = candidates[:, None]
    if candidates.ndim != 2:
        raise ValueError("candidates must be a (T, N) matrix")
    n_obs, n_cand = candidates.shape
    if benchmark.shape != (n_obs,):
        raise ValueError("benchmark must have one return per candidate bar")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between 0 and 1")
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100")
    labels = list(labels) if labels is not None else [{"index": k} for k in range(n_cand)]
    if len(labels) != n_cand:
        raise ValueError("one label per candidate column")

    if n_cand == 0:
        return {"computable": False, "reason": "No candidates to test."}
    if n_obs < MIN_OBS:
        return {
            "computable": False,
            "reason": f"Need at least {MIN_OBS} bars to bootstrap; this period has {n_obs}.",
        }
    if not (np.isfinite(candidates).all() and np.isfinite(benchmark).all()):
        return {"computable": False, "reason": "Non-finite returns in the candidate matrix."}

    # d_{k,t}: how much cell k made over the benchmark on bar t. Everything
    # below is a statement about the columns of d.
    d = candidates - benchmark[:, None]
    d_bar = d.mean(axis=0)
    root_t = math.sqrt(n_obs)
    best = int(np.argmax(d_bar))

    # Block length from the winner's excess series: it is the column whose
    # dependence structure drives the maximum, and using one length for every
    # column keeps the resample joint — the same index draw is applied to
    # every candidate, which is what makes the maximum's distribution right.
    block = choose_block_length(d[:, best])
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(n_obs, block["block_length"], n_bootstrap, rng)

    # Resampled means, (B, N). Column by column keeps peak memory at one
    # (B, T) gather rather than N of them.
    boot_means = np.empty((n_bootstrap, n_cand))
    for k in range(n_cand):
        boot_means[:, k] = d[idx, k].mean(axis=1)

    # sqrt(T) (d*_k - d_k): the centred bootstrap statistic, (B, N). Its
    # spread per column is the standard error SPA studentises with.
    centred = root_t * (boot_means - d_bar)
    omega = centred.std(axis=0)
    usable = omega > _FLAT_TOL

    # ── White's Reality Check ────────────────────────────────────────────
    rc_stat = root_t * d_bar[best]
    rc_dist = centred.max(axis=1)
    rc_p = _p(rc_dist >= rc_stat)

    # The best cell tested on its own, as if the grid had one entry. The gap
    # between this and the RC/SPA p-values is the size of the snooping.
    naive_p = _p(centred[:, best] >= rc_stat)

    # ── Hansen's SPA ─────────────────────────────────────────────────────
    t_ratio = np.full(n_cand, np.nan)
    t_ratio[usable] = root_t * d_bar[usable] / omega[usable]
    spa: dict
    if usable.any():
        spa_stat = max(0.0, float(np.nanmax(t_ratio)))
        # Hansen's threshold for "this candidate is poor enough to leave at
        # its own mean": t below -sqrt(2 log log T).
        threshold = math.sqrt(2.0 * math.log(math.log(n_obs)))
        mu_lower = np.minimum(d_bar, 0.0)
        mu_consistent = np.where(t_ratio <= -threshold, d_bar, 0.0)
        mu_upper = np.zeros(n_cand)

        def spa_p(mu: np.ndarray) -> float:
            z = (centred[:, usable] + root_t * mu[usable]) / omega[usable]
            dist = np.maximum(z.max(axis=1), 0.0)
            return _p(dist >= spa_stat)

        spa = {
            "statistic": round(spa_stat, 6),
            "p_value": round(spa_p(mu_consistent), 4),
            "p_value_lower": round(spa_p(mu_lower), 4),
            "p_value_upper": round(spa_p(mu_upper), 4),
            "poor_candidates_recentred": int(np.sum(t_ratio[usable] <= -threshold)),
        }
    else:
        spa = {"computable": False, "reason": "No candidate has a bootstrap variance to studentise with."}

    # ── Romano-Wolf stepdown ─────────────────────────────────────────────
    # Adjusted p-values by the stepdown recipe: sort by t-ratio, and at each
    # rank compare the observed t with the resampled maximum over that rank
    # and everything below it. Carrying max() forward makes the adjusted
    # p-values monotone in rank, which is what turns the sequence of tests
    # into a single family-wise-error-controlling procedure.
    adjusted = np.full(n_cand, np.nan)
    # Each cell's own studentised p, as if it were the only cell — the
    # per-cell counterpart of `p_value_naive` above, so the table can show
    # naive beside adjusted for every row, not just the winner.
    naive = np.full(n_cand, np.nan)
    if usable.any():
        for k in np.flatnonzero(usable):
            naive[k] = _p(centred[:, k] / omega[k] >= t_ratio[k])
        order = [k for k in np.argsort(-np.where(usable, t_ratio, -np.inf)) if usable[k]]
        z_all = centred[:, usable] / omega[usable]
        usable_pos = {k: i for i, k in enumerate(np.flatnonzero(usable))}
        running = 0.0
        for rank, k in enumerate(order):
            remaining = [usable_pos[j] for j in order[rank:]]
            dist = z_all[:, remaining].max(axis=1)
            p_raw = _p(dist >= t_ratio[k])
            running = max(running, p_raw)
            adjusted[k] = running

    beats = [int(k) for k in range(n_cand) if usable[k] and adjusted[k] <= alpha]
    beats.sort(key=lambda k: -t_ratio[k])

    cells = []
    for k in range(n_cand):
        cells.append(
            {
                "params": labels[k],
                "excess_return_annualised": round(float(d_bar[k] * TRADING_DAYS), 6),
                "t_ratio": None if not usable[k] else round(float(t_ratio[k]), 4),
                "p_naive": None if not usable[k] else round(float(naive[k]), 4),
                "p_adjusted": None if not usable[k] else round(float(adjusted[k]), 4),
                "beats_benchmark": bool(k in beats),
            }
        )
    cells.sort(key=lambda c: -(c["t_ratio"] if c["t_ratio"] is not None else -np.inf))

    p_headline = spa["p_value"] if "p_value" in spa else rc_p
    verdict = _verdict(p_headline, len(beats))

    return {
        "computable": True,
        "n_candidates": n_cand,
        "n_studentised": int(usable.sum()),
        "n_obs": n_obs,
        "n_bootstrap": n_bootstrap,
        "alpha": alpha,
        "block_length": block,
        "benchmark": "buy_and_hold",
        "statistic": "mean per-bar excess return over buy-and-hold, after costs, full period",
        "best": {
            "params": labels[best],
            "excess_return_annualised": round(float(d_bar[best] * TRADING_DAYS), 6),
            "t_ratio": None if not usable[best] else round(float(t_ratio[best]), 4),
            "p_value_naive": round(naive_p, 4),
        },
        "reality_check": {"statistic": round(float(rc_stat), 6), "p_value": round(rc_p, 4)},
        "spa": spa,
        "stepdown": {
            "alpha": alpha,
            "n_beating_benchmark": len(beats),
            "beating_benchmark": [labels[k] for k in beats],
        },
        "cells": cells,
        "verdict": verdict,
        "reading": _reading(n_cand, d_bar[best], naive_p, rc_p, spa, len(beats), alpha),
    }


def _verdict(p: float, n_beating: int) -> str:
    """One word for the whole grid, on the consistent SPA p-value."""
    if n_beating > 0 and p <= 0.05:
        return "grid_beats_benchmark"
    if p <= 0.10:
        return "weak_evidence"
    return "no_evidence"


def _reading(
    n_cand: int,
    best_excess: float,
    naive_p: float,
    rc_p: float,
    spa: dict,
    n_beating: int,
    alpha: float,
) -> str:
    """A sentence a reader can take away without the table."""
    excess = best_excess * TRADING_DAYS * 100
    lead = (
        f"The best of {n_cand} cells made {excess:+.1f}% a year over buy-and-hold. "
        f"Tested alone that reads p = {naive_p:.3f}; "
    )
    if "p_value" in spa:
        lead += (
            f"with the whole grid inside the bootstrap it is p = {rc_p:.3f} "
            f"(Reality Check) and p = {spa['p_value']:.3f} (SPA). "
        )
    else:
        lead += f"with the whole grid inside the bootstrap it is p = {rc_p:.3f} (Reality Check). "
    if n_beating == 0:
        lead += f"No cell beats buy-and-hold at the {int(alpha * 100)}% level once the search is accounted for."
    elif n_beating == 1:
        lead += f"One cell survives Romano-Wolf at {int(alpha * 100)}%."
    else:
        lead += f"{n_beating} cells survive Romano-Wolf at {int(alpha * 100)}%."
    return lead
