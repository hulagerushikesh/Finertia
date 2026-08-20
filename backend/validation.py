"""Overfitting checks — walk-forward validation and a signal permutation test.

Both answer questions a single backtest cannot:

  walk_forward()     Did these parameters work on data they were not chosen on?
  permutation_test() Is this Sharpe ratio better than random timing at the same exposure?

Pure pandas/numpy, consistent with the rest of the engine.
"""

import numpy as np
import pandas as pd

from deflated import deflated_sharpe_ratio
from pbo import combinatorial_pbo
from purge import purged_split
from engine import compute_returns
from metrics import compute_metrics
from strategies import build_positions, longest_window, param_grid


def _segment_net_return(
    position: pd.Series,
    returns: pd.Series,
    transaction_cost: float,
) -> pd.Series:
    """Net per-bar return for one slice, after turnover costs."""
    trade_occurred = position.diff().abs() > 0
    net_return = (position * returns) - trade_occurred * transaction_cost
    return net_return.fillna(0)


def _segment_metrics(
    position: pd.Series,
    returns: pd.Series,
    transaction_cost: float,
) -> dict:
    """Metrics for one slice of an already-computed position series."""
    net_return = _segment_net_return(position, returns, transaction_cost)

    equity_curve = (1 + net_return).cumprod()
    drawdown = (equity_curve - equity_curve.cummax()) / equity_curve.cummax()

    return compute_metrics(net_return, equity_curve, drawdown, position)


def walk_forward(
    close: pd.Series,
    transaction_cost: float,
    strategy: str = "momentum",
    base_params: dict | None = None,
    user_params: dict | None = None,
    split_ratio: float = 0.7,
    grid: list[dict] | None = None,
) -> dict:
    """Optimise parameters on the first split_ratio of the period, score on the rest.

    Works for any strategy in the registry. The out-of-sample metrics are the
    honest ones: those bars had no influence on which parameters were selected.

    Positions are always computed on the FULL series and sliced afterwards.
    Building signals from a slice instead would leave its first warm-up bars
    flat, which would understate the out-of-sample result rather than measure it.

    The two halves do not touch. A purge-and-embargo gap sits between them so
    the trade that straddles the split cannot earn in both — see `purge.py`.
    """
    base_params = base_params or {}
    n = len(close)
    split_at = int(n * split_ratio)
    if split_at < 30 or n - split_at < 30:
        raise ValueError(
            "Date range is too short to split — each half needs at least 30 bars. "
            "Use a longer period."
        )

    returns = compute_returns(close)

    # Selection stops short of the split and scoring starts after it, so the
    # position carried across the boundary is never counted by both halves.
    boundary = purged_split(n, split_at)
    is_end, oos_start = boundary["is_end"], boundary["oos_start"]
    is_slice = slice(0, is_end)
    oos_slice = slice(oos_start, n)

    combos = grid if grid is not None else param_grid(strategy)

    # --- sweep the grid on the in-sample half only -------------------------
    grid_results = []
    # Every candidate's full-period net return, kept for the PBO matrix below.
    # Collected here rather than recomputed because the sweep already builds
    # each position series — doing it again per split would mean 70x the work
    # for identical numbers.
    candidate_returns = []
    warmups = []
    for combo in combos:
        params = {**base_params, **combo}
        # A strategy needing more warm-up than the in-sample half can never fire.
        warmup = longest_window(strategy, params)
        if warmup >= is_end:
            continue
        pos = build_positions(close, strategy, params)
        m = _segment_metrics(pos.iloc[is_slice], returns.iloc[is_slice], transaction_cost)
        grid_results.append(
            {
                "params": combo,
                "sharpe_ratio": m["sharpe_ratio"],
                "total_return": m["total_return"],
            }
        )
        candidate_returns.append(
            _segment_net_return(pos, returns, transaction_cost).to_numpy()
        )
        warmups.append(warmup)

    if not grid_results:
        raise ValueError(
            "No parameter combination fits inside this date range — every option "
            "needs more history than the in-sample period provides."
        )

    best = max(grid_results, key=lambda r: r["sharpe_ratio"])

    # --- score the winner on data it never saw -----------------------------
    best_full = {**base_params, **best["params"]}
    best_pos = build_positions(close, strategy, best_full)
    best_is = _segment_metrics(best_pos.iloc[is_slice], returns.iloc[is_slice], transaction_cost)
    best_oos = _segment_metrics(best_pos.iloc[oos_slice], returns.iloc[oos_slice], transaction_cost)

    # --- the same treatment for whatever the user picked -------------------
    user_block = None
    if user_params:
        user_pos = build_positions(close, strategy, {**base_params, **user_params})
        user_block = {
            "params": user_params,
            "in_sample": _segment_metrics(user_pos.iloc[is_slice], returns.iloc[is_slice], transaction_cost),
            "out_of_sample": _segment_metrics(user_pos.iloc[oos_slice], returns.iloc[oos_slice], transaction_cost),
        }

    degradation = best_is["sharpe_ratio"] - best_oos["sharpe_ratio"]

    # Picking the highest Sharpe out of the grid is multiple testing, and the
    # maximum of N draws is inflated even when nothing in the grid has an edge.
    # Deflate the in-sample figure against the bar that selection alone would
    # clear. In-sample specifically: those are the bars the choice was made on,
    # so they are the ones carrying the bias.
    #
    # N is taken as the raw number of combinations, which treats neighbouring
    # parameter settings as independent when they plainly are not. Overstating
    # N raises the noise bar, so the error runs toward calling a real edge
    # insignificant rather than the reverse — the safe direction for a tool
    # whose whole job is to talk you out of a bad backtest.
    deflated = deflated_sharpe_ratio(
        trial_sharpes=[r["sharpe_ratio"] for r in grid_results],
        selected_returns=_segment_net_return(
            best_pos.iloc[is_slice], returns.iloc[is_slice], transaction_cost
        ).to_numpy(),
    )

    # Probability of Backtest Overfitting over the same candidate set.
    #
    # This asks a different question from the split above: not "did this one
    # winner survive into a later period", but "is picking the in-sample winner
    # better than picking at random, across every way of dividing this period".
    # Both are needed — CSCV is deliberately not chronological, so it cannot
    # see a regime break, and walk-forward only ever tries one split.
    #
    # Trimmed to the longest warm-up in the retained grid so no candidate
    # contributes a run of flat bars the others do not have.
    if len(candidate_returns) >= 2:
        trim = max(warmups)
        matrix = np.column_stack(candidate_returns)[trim:]
        overfitting = combinatorial_pbo(matrix)
    else:
        overfitting = {
            "computable": False,
            "reason": "Only one parameter combination fits this period, so there was no selection to test.",
        }

    return {
        "strategy": strategy,
        "split_date": str(close.index[split_at].date()),
        # Bars each half actually uses, which is the split minus the gap — not
        # the nominal ratio. Reporting the nominal figure would overstate how
        # much data backs either number.
        "in_sample_bars": is_end,
        "out_of_sample_bars": n - oos_start,
        "boundary": {
            **boundary,
            "in_sample_end_date": str(close.index[is_end - 1].date()),
            "out_of_sample_start_date": str(close.index[oos_start].date()),
        },
        "combinations_tested": len(grid_results),
        "best_params": best["params"],
        "best_in_sample": best_is,
        "best_out_of_sample": best_oos,
        "sharpe_degradation": round(degradation, 6),
        "deflated": deflated,
        "overfitting": overfitting,
        "verdict": _verdict(best_is["sharpe_ratio"], best_oos["sharpe_ratio"]),
        "user_params": user_block,
        "grid": sorted(grid_results, key=lambda r: r["sharpe_ratio"], reverse=True),
    }


def _verdict(is_sharpe: float, oos_sharpe: float) -> str:
    """Plain-language reading of the in-sample to out-of-sample drop."""
    if oos_sharpe <= 0:
        return "failed"
    if is_sharpe <= 0:
        return "inconclusive"
    retained = oos_sharpe / is_sharpe
    if retained >= 0.7:
        return "held_up"
    if retained >= 0.4:
        return "weakened"
    return "overfit"


def permutation_test(
    position: pd.Series,
    returns: pd.Series,
    transaction_cost: float,
    n_trials: int = 500,
    seed: int = 42,
) -> dict:
    """Compare the real Sharpe against Sharpes from randomly reordered positions.

    Shuffling preserves exactly how many long, short, and flat days there were —
    only *when* they happened changes. So this isolates signal timing: if the real
    result sits mid-pack among the shuffles, the edge came from market exposure
    rather than from the strategy picking moments.
    """
    if len(position) != len(returns):
        raise ValueError("position and returns must be the same length")

    real = _segment_metrics(position, returns, transaction_cost)
    real_sharpe = real["sharpe_ratio"]

    rng = np.random.default_rng(seed)
    pos_values = position.to_numpy()
    ret_values = returns.fillna(0).to_numpy()
    ann = np.sqrt(252)

    shuffled_sharpes = np.empty(n_trials)
    for i in range(n_trials):
        shuffled = rng.permutation(pos_values)
        trades = np.abs(np.diff(shuffled, prepend=shuffled[0])) > 0
        net = shuffled * ret_values - trades * transaction_cost
        sd = net.std()
        # Match compute_metrics: annualised return over annualised volatility.
        if sd == 0:
            shuffled_sharpes[i] = 0.0
            continue
        total = np.prod(1 + net) - 1
        n = len(net)
        if total <= -1:
            shuffled_sharpes[i] = 0.0
            continue
        annualised = (1 + total) ** (252 / n) - 1
        shuffled_sharpes[i] = annualised / (sd * ann)

    beaten = int((shuffled_sharpes < real_sharpe).sum())
    percentile = beaten / n_trials
    # One-sided p-value: how often random timing matched or beat the real result.
    p_value = float((shuffled_sharpes >= real_sharpe).sum() + 1) / (n_trials + 1)

    return {
        "real_sharpe": real_sharpe,
        "trials": n_trials,
        "percentile": round(percentile, 4),
        "p_value": round(p_value, 4),
        "random_sharpe_mean": round(float(shuffled_sharpes.mean()), 6),
        "random_sharpe_std": round(float(shuffled_sharpes.std()), 6),
        "random_sharpe_p95": round(float(np.percentile(shuffled_sharpes, 95)), 6),
        "significant": bool(p_value < 0.05),
        "verdict": (
            "signal_timing_matters"
            if p_value < 0.05
            else "indistinguishable_from_random_timing"
        ),
    }
