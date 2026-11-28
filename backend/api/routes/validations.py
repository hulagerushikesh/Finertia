"""Overfitting checks for one ticker and for a basket."""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from api import core
from api.core import (
    check_validation_allowed,
    enforce_quota,
    give_back_validation_slot,
    inject_user,
    take_validation_slot,
    validate_limiter,
    with_allowance,
)
from api.simulation import fetch_aligned, portfolio_weights
from bootstrap import stable_seed
from data import DataUnavailableError
from engine import compute_returns
from portfolio_validation import (
    leg_positions,
    portfolio_permutation_test,
    portfolio_walk_forward,
)
from rolling import rolling_walk_forward
from schemas import (
    PortfolioValidateRequest,
    ValidateRequest,
)
from strategies import build_positions, param_grid
from validation import permutation_test

router = APIRouter()


@router.post("/validate")
def validate_strategy(req: ValidateRequest, authorization: Optional[str] = Header(None)):
    """Run the two overfitting checks a single backtest cannot answer.

    Walk-forward asks whether parameters survive on data they were not chosen on.
    The permutation test asks whether signal timing beats random timing at the
    same market exposure. Results are diagnostic and not persisted.
    """
    # Tighter than the backtest budget: a validation run rebuilds positions once
    # per grid combination and then again for every permutation trial, so one
    # call is worth hundreds of backtests in CPU terms.
    user = inject_user(authorization, limit=(validate_limiter, "validation runs", 1))
    check_validation_allowed(user)
    enforce_quota(user)

    slot = take_validation_slot(user)
    try:
        result = _validate_single(req)
    except BaseException:
        give_back_validation_slot(user, slot)
        raise
    return with_allowance(result, slot)


def _validate_single(req) -> dict:
    """Walk-forward and the permutation test for one ticker; the work behind `/api/validate`."""
    start_time = time.time()

    try:
        df = core.fetch_ohlcv(req.ticker, req.start, req.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    data_source = df.attrs.get("data_source", "yfinance")
    close = df["Close"]

    params = req.strategy_params()
    # Score the user's own values for exactly the keys the grid sweeps, so the
    # comparison against the optimised set is like for like.
    swept_keys = param_grid(req.strategy)[0].keys()
    user_params = {k: params[k] for k in swept_keys if k in params}

    try:
        wf = core.walk_forward(
            close,
            transaction_cost=req.transaction_cost,
            strategy=req.strategy,
            base_params=params,
            user_params=user_params,
            split_ratio=req.split_ratio,
            seed=stable_seed(req.ticker.upper(), req.start, req.end, req.strategy, "snooping"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # The single split above is one draw. Walk it forward so the verdict is
    # reported per segment, with the market's own return beside each — the
    # only way to tell "no edge" from "no edge in the stretch the split
    # happened to score". Cheap: positions per grid cell are built once.
    try:
        rolling = rolling_walk_forward(
            close,
            transaction_cost=req.transaction_cost,
            strategy=req.strategy,
            base_params=params,
            n_folds=req.rolling_folds,
            seed=stable_seed(req.ticker.upper(), req.start, req.end, req.strategy, "rolling"),
        )
    except ValueError as exc:
        rolling = {"computable": False, "reason": str(exc)}

    positions = build_positions(close, req.strategy, params)
    returns = compute_returns(close)
    permutation = permutation_test(
        positions, returns, req.transaction_cost, n_trials=req.permutation_trials
    )

    return {
        "ticker": req.ticker,
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "bars": len(close),
        "walk_forward": wf,
        "rolling_walk_forward": rolling,
        "permutation": permutation,
        "data_source": data_source,
        "duration_ms": int((time.time() - start_time) * 1000),
    }


@router.post("/portfolio/validate")
def validate_portfolio(req: PortfolioValidateRequest, authorization: Optional[str] = Header(None)):
    """The overfitting checks, asked of the whole book.

    One parameter set is optimised on the basket's in-sample Sharpe and scored
    on the rest; the permutation test re-times every leg independently with
    the weight path held fixed (see `portfolio_validation.py` for why that is
    the null). Same plan gate and rate budget as `/api/validate`, plus the
    plan's portfolio-size cap. Diagnostic; not persisted.
    """
    user = inject_user(authorization, limit=(validate_limiter, "validation runs", 1))
    check_validation_allowed(user)
    allowed_size = core.max_portfolio_size(user["profile"])
    if len(req.tickers) > allowed_size:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Portfolios can hold up to {allowed_size} names; "
                f"you selected {len(req.tickers)}."
            ),
        )
    enforce_quota(user)

    slot = take_validation_slot(user)
    try:
        result = _validate_book(req)
    except BaseException:
        give_back_validation_slot(user, slot)
        raise
    return with_allowance(result, slot)


def _validate_book(req) -> dict:
    """The same checks for a basket; the work behind `/api/portfolio/validate`."""
    start_time = time.time()
    aligned, _, data_source = fetch_aligned(req)
    weights = portfolio_weights(req, aligned)

    params = req.strategy_params()
    swept_keys = param_grid(req.strategy)[0].keys()
    user_params = {k: params[k] for k in swept_keys if k in params}
    seed_key = ("|".join(req.tickers), req.start, req.end, req.strategy, req.weighting)

    try:
        wf = portfolio_walk_forward(
            aligned,
            weights,
            transaction_cost=req.leg_costs(),
            strategy=req.strategy,
            base_params=params,
            user_params=user_params,
            split_ratio=req.split_ratio,
            seed=stable_seed(*seed_key, "snooping"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    permutation = portfolio_permutation_test(
        leg_positions(aligned, req.strategy, params),
        aligned.pct_change(),
        weights,
        req.leg_costs(),
        n_trials=req.permutation_trials,
    )

    return {
        "tickers": req.tickers,
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "weighting": req.weighting,
        "bars": len(aligned),
        "walk_forward": wf,
        "permutation": permutation,
        "data_source": data_source,
        "duration_ms": int((time.time() - start_time) * 1000),
    }

