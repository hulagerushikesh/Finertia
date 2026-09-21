"""Validation for a basket — the same questions `/api/validate` asks of one
ticker, asked of the combined book.

Two things change when the object under test is a portfolio rather than a
position series, and both are decisions rather than mechanics:

1. **What is optimised.** One strategy, one parameter set, shared by every
   leg — that is how `/api/portfolio` runs — so the grid is swept on the
   *portfolio's* in-sample Sharpe, not on any leg's. A parameter set that
   flatters one leg and ruins another is judged on the net.

2. **What the permutation null is.** Shuffling a portfolio's timing could mean
   shuffling each leg's position series independently, or shuffling the weight
   path. These are different nulls. The one implemented here is the first —
   *no leg has timing skill* — with the weight path held fixed as data. It is
   the direct extension of the single-ticker test: a basket of strategies none
   of which can time its own market should not be able to time the book.
   Decided 21 Sep 2026 (open-questions §2).

Legs are built from the raw strategy signal, without the stop and sizing
overlays, exactly as `/api/validate` does for one ticker: the thing under test
is the rule, not the risk layer on top of it.

Reuses the single-ticker machinery where the maths is identical — the purged
split, the deflated Sharpe with its effective-N block, CSCV, and the whole-grid
test — so a portfolio verdict and a single-ticker verdict mean the same thing.
"""

import numpy as np
import pandas as pd

from deflated import TRADING_DAYS, deflated_sharpe_ratio
from metrics import compute_metrics
from pbo import combinatorial_pbo
from purge import purged_split
from snooping import whole_grid_test
from strategies import build_positions, longest_window, param_grid
from validation import _effective_trials, _segment_net_return, _verdict


# --------------------------------------------------------------------------
# Building the book
# --------------------------------------------------------------------------


def leg_positions(aligned: pd.DataFrame, strategy: str, params: dict) -> pd.DataFrame:
    """Raw signal per leg, same parameters everywhere, on the aligned closes."""
    return pd.DataFrame(
        {t: build_positions(aligned[t], strategy, params) for t in aligned.columns},
        index=aligned.index,
    )


def book_net_return(
    positions: pd.DataFrame,
    asset_returns: pd.DataFrame,
    weights: pd.DataFrame,
    transaction_cost: float,
) -> tuple[pd.Series, pd.Series]:
    """Weighted sum of each leg's net return, and the book's gross exposure.

    Each leg pays its own turnover cost before weighting, as `/api/portfolio`
    does. Exposure — Σ w·|position| — stands in for a position series when the
    metrics count trades: a change in the book's gross exposure is a trade.
    """
    legs = pd.DataFrame(
        {
            t: _segment_net_return(positions[t], asset_returns[t], transaction_cost)
            for t in positions.columns
        },
        index=positions.index,
    )
    w = weights.reindex(legs.index).fillna(0.0)
    net = (legs * w).sum(axis=1)
    exposure = (positions.abs() * w).sum(axis=1)
    return net, exposure


def _metrics(net: pd.Series, exposure: pd.Series) -> dict:
    equity = (1 + net).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()
    return compute_metrics(net, equity, drawdown, exposure)


def _sharpe(net: np.ndarray) -> float:
    """Annualised return over annualised volatility — `compute_metrics`' Sharpe,
    inlined for the permutation loop. Same conventions as `permutation_test`."""
    sd = net.std()
    if sd == 0:
        return 0.0
    total = np.prod(1 + net) - 1
    if total <= -1:
        return 0.0
    annualised = (1 + total) ** (TRADING_DAYS / len(net)) - 1
    return float(annualised / (sd * np.sqrt(TRADING_DAYS)))


# --------------------------------------------------------------------------
# Walk-forward on the combined book
# --------------------------------------------------------------------------


def portfolio_walk_forward(
    aligned: pd.DataFrame,
    weights: pd.DataFrame,
    transaction_cost: float,
    strategy: str = "momentum",
    base_params: dict | None = None,
    user_params: dict | None = None,
    split_ratio: float = 0.7,
    grid: list[dict] | None = None,
    seed: int = 0,
) -> dict:
    """Optimise one parameter set for the whole basket in-sample, score it out.

    Mirrors `validation.walk_forward` key for key so the frontend's verdict
    card reads either. Adds `legs`: the winner's in- and out-of-sample Sharpe
    per ticker, because a book that held up may have done so on one leg.
    """
    base_params = base_params or {}
    tickers = list(aligned.columns)
    n = len(aligned)
    split_at = int(n * split_ratio)
    if split_at < 30 or n - split_at < 30:
        raise ValueError(
            "Date range is too short to split — each half needs at least 30 bars. "
            "Use a longer period."
        )

    asset_returns = aligned.pct_change()
    boundary = purged_split(n, split_at)
    is_end, oos_start = boundary["is_end"], boundary["oos_start"]
    is_slice = slice(0, is_end)
    oos_slice = slice(oos_start, n)

    combos = grid if grid is not None else param_grid(strategy)

    def book(params: dict) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
        pos = leg_positions(aligned, strategy, params)
        net, exposure = book_net_return(pos, asset_returns, weights, transaction_cost)
        return net, exposure, pos

    grid_results = []
    candidate_returns = []
    warmups = []
    for combo in combos:
        params = {**base_params, **combo}
        warmup = longest_window(strategy, params)
        if warmup >= is_end:
            continue
        net, exposure, _ = book(params)
        m = _metrics(net.iloc[is_slice], exposure.iloc[is_slice])
        grid_results.append(
            {"params": combo, "sharpe_ratio": m["sharpe_ratio"], "total_return": m["total_return"]}
        )
        candidate_returns.append(net.to_numpy())
        warmups.append(warmup)

    if not grid_results:
        raise ValueError(
            "No parameter combination fits inside this date range — every option "
            "needs more history than the in-sample period provides."
        )

    best = max(grid_results, key=lambda r: r["sharpe_ratio"])
    best_full = {**base_params, **best["params"]}
    best_net, best_exposure, best_pos = book(best_full)
    best_is = _metrics(best_net.iloc[is_slice], best_exposure.iloc[is_slice])
    best_oos = _metrics(best_net.iloc[oos_slice], best_exposure.iloc[oos_slice])

    # The winner leg by leg: which ticker the out-of-sample number rests on.
    legs = {}
    for t in tickers:
        leg_net = _segment_net_return(best_pos[t], asset_returns[t], transaction_cost)
        legs[t] = {
            "in_sample_sharpe": _metrics(leg_net.iloc[is_slice], best_pos[t].iloc[is_slice])["sharpe_ratio"],
            "out_of_sample_sharpe": _metrics(leg_net.iloc[oos_slice], best_pos[t].iloc[oos_slice])["sharpe_ratio"],
            "mean_weight": round(float(weights[t].mean()), 4),
        }

    user_block = None
    if user_params:
        u_net, u_exposure, _ = book({**base_params, **user_params})
        user_block = {
            "params": user_params,
            "in_sample": _metrics(u_net.iloc[is_slice], u_exposure.iloc[is_slice]),
            "out_of_sample": _metrics(u_net.iloc[oos_slice], u_exposure.iloc[oos_slice]),
        }

    degradation = best_is["sharpe_ratio"] - best_oos["sharpe_ratio"]

    trial_sharpes = [r["sharpe_ratio"] for r in grid_results]
    selected_is = best_net.iloc[is_slice].to_numpy()
    deflated = deflated_sharpe_ratio(trial_sharpes=trial_sharpes, selected_returns=selected_is)
    deflated["effective_trials"] = _effective_trials(
        candidate_returns, is_end, max(warmups), trial_sharpes, selected_is, deflated,
    )

    trim = max(warmups)
    if len(candidate_returns) >= 2:
        overfitting = combinatorial_pbo(np.column_stack(candidate_returns)[trim:])
    else:
        overfitting = {
            "computable": False,
            "reason": "Only one parameter combination fits this period, so there was no selection to test.",
        }

    # The benchmark a basket has to beat is holding the basket: the same
    # weights applied to the assets themselves, no signal.
    held = (asset_returns.fillna(0.0) * weights.reindex(aligned.index).fillna(0.0)).sum(axis=1)
    snooping = whole_grid_test(
        np.column_stack(candidate_returns)[trim:],
        held.to_numpy()[trim:],
        labels=[r["params"] for r in grid_results],
        seed=seed,
    )
    snooping["benchmark"] = "buy_and_hold_basket"

    return {
        "strategy": strategy,
        "tickers": tickers,
        "split_date": str(aligned.index[split_at].date()),
        "in_sample_bars": is_end,
        "out_of_sample_bars": n - oos_start,
        "boundary": {
            **boundary,
            "in_sample_end_date": str(aligned.index[is_end - 1].date()),
            "out_of_sample_start_date": str(aligned.index[oos_start].date()),
        },
        "combinations_tested": len(grid_results),
        "best_params": best["params"],
        "best_in_sample": best_is,
        "best_out_of_sample": best_oos,
        "sharpe_degradation": round(degradation, 6),
        "legs": legs,
        "deflated": deflated,
        "overfitting": overfitting,
        "snooping": snooping,
        "verdict": _verdict(best_is["sharpe_ratio"], best_oos["sharpe_ratio"]),
        "user_params": user_block,
        "grid": sorted(grid_results, key=lambda r: r["sharpe_ratio"], reverse=True),
    }


# --------------------------------------------------------------------------
# Permutation test — every leg's timing shuffled independently
# --------------------------------------------------------------------------


def portfolio_permutation_test(
    positions: pd.DataFrame,
    asset_returns: pd.DataFrame,
    weights: pd.DataFrame,
    transaction_cost: float,
    n_trials: int = 500,
    seed: int = 42,
) -> dict:
    """Book Sharpe against books whose legs were each randomly re-timed.

    Each trial draws an independent permutation for every leg, so each leg
    keeps exactly its own count of long, short and flat days and only *when*
    changes; the weight path is untouched. Under this null no leg can time its
    market, and any book-level Sharpe is exposure plus the diversification the
    weights bought — which is why the null distribution is not centred where a
    single leg's would be. The per-leg block runs the ordinary single-ticker
    test on the same draws, so a significant book can be traced to the legs
    that carried it.
    """
    if not positions.index.equals(asset_returns.index):
        raise ValueError("positions and asset_returns must share an index")
    if not positions.columns.equals(asset_returns.columns):
        raise ValueError("positions and asset_returns must cover the same tickers")

    tickers = list(positions.columns)
    real_net, real_exposure = book_net_return(positions, asset_returns, weights, transaction_cost)
    real_sharpe = _metrics(real_net, real_exposure)["sharpe_ratio"]

    rng = np.random.default_rng(seed)
    pos = positions.to_numpy()
    ret = asset_returns.fillna(0).to_numpy()
    w = weights.reindex(positions.index).fillna(0.0).to_numpy()
    n_bars, n_legs = pos.shape

    real_leg_sharpes = np.array(
        [
            _sharpe(_segment_net_return(positions[t], asset_returns[t], transaction_cost).to_numpy())
            for t in tickers
        ]
    )

    book_sharpes = np.empty(n_trials)
    leg_sharpes = np.empty((n_trials, n_legs))
    for i in range(n_trials):
        shuffled = np.empty_like(pos)
        for k in range(n_legs):
            shuffled[:, k] = rng.permutation(pos[:, k])
        trades = np.abs(np.diff(shuffled, axis=0, prepend=shuffled[:1])) > 0
        leg_net = shuffled * ret - trades * transaction_cost
        book_sharpes[i] = _sharpe((leg_net * w).sum(axis=1))
        for k in range(n_legs):
            leg_sharpes[i, k] = _sharpe(leg_net[:, k])

    beaten = int((book_sharpes < real_sharpe).sum())
    p_value = float((book_sharpes >= real_sharpe).sum() + 1) / (n_trials + 1)
    legs = {}
    for k, t in enumerate(tickers):
        p_leg = float((leg_sharpes[:, k] >= real_leg_sharpes[k]).sum() + 1) / (n_trials + 1)
        legs[t] = {
            "real_sharpe": round(float(real_leg_sharpes[k]), 6),
            "random_sharpe_mean": round(float(leg_sharpes[:, k].mean()), 6),
            "p_value": round(p_leg, 4),
            "significant": bool(p_leg < 0.05),
        }

    return {
        "null": "each leg's timing shuffled independently; weights held fixed",
        "real_sharpe": real_sharpe,
        "trials": n_trials,
        "percentile": round(beaten / n_trials, 4),
        "p_value": round(p_value, 4),
        "random_sharpe_mean": round(float(book_sharpes.mean()), 6),
        "random_sharpe_std": round(float(book_sharpes.std()), 6),
        "random_sharpe_p95": round(float(np.percentile(book_sharpes, 95)), 6),
        "significant": bool(p_value < 0.05),
        "legs": legs,
        "legs_significant": sum(1 for v in legs.values() if v["significant"]),
        "verdict": (
            "signal_timing_matters" if p_value < 0.05 else "indistinguishable_from_random_timing"
        ),
    }
