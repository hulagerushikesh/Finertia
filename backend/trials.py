"""How many independent strategies did the grid really test?

The Deflated Sharpe Ratio (deflated.py) raises the bar a winner has to clear
by the expected maximum of N zero-edge trials. It has been fed N = the raw
grid size. That is wrong in a known direction: a 20-day and a 25-day lookback
produce nearly the same return series, so the grid is not N independent
draws — it is fewer, and overstating N overstates the bar. Safe, but
unmeasured. This module measures it.

Two estimates, deliberately different in kind, both from the candidate
in-sample return matrix that the walk-forward sweep already builds:

  eigenvalue  — Li & Ji (2005), after Nyholt (2004). The correlation matrix
                of N identical series has one eigenvalue of N and N-1 zeros;
                N independent series have N eigenvalues of 1. Count how much
                of the spectrum sits at or above 1:
                    N_eff = sum_i [ 1(lambda_i >= 1) + (lambda_i - floor(lambda_i)) ]
                Cheap, closed-form, no tuning. Reads the structure but does
                not say which trials belong together.

  clustering  — López de Prado & Lewis (2019). Cluster candidates on the
                correlation distance d = sqrt((1 - rho) / 2), choose the
                number of clusters by silhouette, and treat each cluster as
                one trial. The Sharpe spread used for the noise bar is then
                the spread across clusters, each represented by the equal-
                weight average of its members. Says which trials are the
                same trial, which is what the paper is actually about.

Everything here is numpy. The agglomerative clustering and silhouette are
written out (average linkage, N is at most a few dozen) rather than imported,
for the same reason the Normal quantile is written out in deflated.py.
"""

from __future__ import annotations

import math

import numpy as np

# A candidate whose returns never vary has no correlation with anything. It
# is dropped from both estimates: it could not have won the sweep, so it is
# not a trial that selection could have exploited.
_FLAT_TOL = 1e-12

# Below this the pairwise distances are all effectively zero — every candidate
# is the same series — and there is exactly one trial.
_SAME_TOL = 1e-6

# When the silhouette search finds no structure, a grid whose widest pair is
# still this close (correlation above 0.875) is one trial, not N.
_ONE_BLOB_DIST = 0.25


def _clean(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop rows with non-finite values and flat columns. Returns the cleaned
    matrix and the original column index of each surviving column."""
    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2:
        raise ValueError("candidate matrix must be 2-D (bars x candidates)")
    m = m[np.all(np.isfinite(m), axis=1)]
    if m.shape[0] < 3:
        return m[:, :0], np.array([], dtype=int)
    scale = np.maximum(np.abs(m).max(axis=0), 1.0)
    keep = m.std(axis=0, ddof=1) > scale * _FLAT_TOL
    return m[:, keep], np.flatnonzero(keep)


def _correlation(m: np.ndarray) -> np.ndarray:
    c = np.corrcoef(m, rowvar=False)
    c = np.atleast_2d(c)
    # Floating error can push a perfect correlation to 1 + 1e-16.
    return np.clip(c, -1.0, 1.0)


def effective_trials_eigen(matrix: np.ndarray) -> dict:
    """Li & Ji (2005) effective number of independent tests."""
    m, _ = _clean(matrix)
    n = m.shape[1]
    if n == 0:
        return {"computable": False, "reason": "No candidate traded."}
    if n == 1:
        return {"computable": True, "n_candidates": 1, "n_effective": 1.0}
    lam = np.linalg.eigvalsh(_correlation(m))
    # An exact multiple can come back as 5.9999999 on one BLAS and 6.0000001
    # on another; the fractional term would read the first as 0.9999999 and
    # count a phantom trial. Round to well inside float noise first.
    lam = np.round(np.abs(lam), 8)
    n_eff = float(np.sum((lam >= 1.0).astype(float) + (lam - np.floor(lam))))
    # Rounding can nudge the sum a hair past N; the estimate is bounded by
    # construction.
    n_eff = float(min(max(n_eff, 1.0), n))
    return {"computable": True, "n_candidates": int(n), "n_effective": round(n_eff, 4)}


# ── clustering ────────────────────────────────────────────────────────────────

def _average_linkage(dist: np.ndarray) -> list[list[int]]:
    """Merge order for agglomerative clustering with average linkage.

    Returns the partition after each merge, from N singletons down to one
    cluster — `partitions[k]` has N - k clusters.
    """
    n = dist.shape[0]
    clusters: list[list[int]] = [[i] for i in range(n)]
    history = [list(map(list, clusters))]
    while len(clusters) > 1:
        best = None
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                d = dist[np.ix_(clusters[a], clusters[b])].mean()
                if best is None or d < best[0]:
                    best = (d, a, b)
        _, a, b = best
        merged = clusters[a] + clusters[b]
        clusters = [c for i, c in enumerate(clusters) if i not in (a, b)] + [merged]
        history.append(list(map(list, clusters)))
    return history


def _silhouette(dist: np.ndarray, labels: np.ndarray) -> float:
    """Mean silhouette over all points. Singleton clusters score 0, as in
    Rousseeuw (1987)."""
    n = dist.shape[0]
    scores = np.zeros(n)
    for i in range(n):
        own = labels == labels[i]
        own[i] = False
        if not own.any():
            scores[i] = 0.0
            continue
        a = dist[i, own].mean()
        b = math.inf
        for lab in np.unique(labels):
            if lab == labels[i]:
                continue
            other = labels == lab
            b = min(b, dist[i, other].mean())
        scores[i] = 0.0 if max(a, b) == 0 else (b - a) / max(a, b)
    return float(scores.mean())


def effective_trials_clusters(matrix: np.ndarray) -> dict:
    """López de Prado & Lewis (2019): one trial per correlation cluster.

    Also returns, per cluster, the members and the per-observation Sharpe of
    the equal-weight average of their returns — the inputs the deflated
    Sharpe needs to use K clusters instead of N candidates.
    """
    m, kept = _clean(matrix)
    n = m.shape[1]
    if n == 0:
        return {"computable": False, "reason": "No candidate traded."}

    def original(groups: list[list[int]]) -> list[list[int]]:
        # Report membership in the caller's column numbering, not the cleaned one.
        return [sorted(int(kept[i]) for i in g) for g in groups]

    def cluster_sharpes(groups: list[list[int]]) -> list[float]:
        out = []
        for g in groups:
            r = m[:, g].mean(axis=1)
            s = r.std(ddof=1)
            out.append(float(r.mean() / s) if s > 0 else 0.0)
        return out

    if n == 1:
        return {
            "computable": True,
            "n_candidates": 1,
            "n_effective": 1,
            "silhouette": None,
            "clusters": original([[0]]),
            "cluster_sharpes": cluster_sharpes([[0]]),
        }

    corr = _correlation(m)
    dist = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)

    if dist.max() < _SAME_TOL:
        groups = [list(range(n))]
        return {
            "computable": True,
            "n_candidates": int(n),
            "n_effective": 1,
            "silhouette": None,
            "clusters": original(groups),
            "cluster_sharpes": cluster_sharpes(groups),
        }

    history = _average_linkage(dist)
    # Silhouette is defined for 2 <= K <= N-1. K = N (all singletons) scores
    # 0 by convention, K = 1 is undefined; both are handled by the branches
    # above and below rather than by the search.
    best_k, best_s, best_groups = None, -math.inf, None
    for groups in history:
        k = len(groups)
        if k < 2 or k > n - 1:
            continue
        labels = np.empty(n, dtype=int)
        for lab, g in enumerate(groups):
            labels[g] = lab
        s = _silhouette(dist, labels)
        if s > best_s:
            best_k, best_s, best_groups = k, s, groups

    # A silhouette near zero says the clusters are no tighter than the space
    # between them — but that is true both when every candidate is the same
    # series (all distances small) and when every candidate is independent
    # (all distances large). The absolute distance tells them apart: if no
    # pair is further than 0.25 (every correlation above 0.875) the grid is
    # one blob and one trial; otherwise it is N.
    if best_groups is None or best_s < 0.1:
        one_blob = dist.max() < _ONE_BLOB_DIST
        groups = [list(range(n))] if one_blob else [[i] for i in range(n)]
        return {
            "computable": True,
            "n_candidates": int(n),
            "n_effective": 1 if one_blob else int(n),
            "silhouette": None if best_groups is None else round(best_s, 4),
            "clusters": original(groups),
            "cluster_sharpes": cluster_sharpes(groups),
        }

    groups = [sorted(g) for g in best_groups]
    return {
        "computable": True,
        "n_candidates": int(n),
        "n_effective": int(best_k),
        "silhouette": round(best_s, 4),
        "clusters": original(groups),
        "cluster_sharpes": cluster_sharpes(groups),
    }
