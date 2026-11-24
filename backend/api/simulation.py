"""Price fetches and the simulation steps shared by several routes."""


import pandas as pd
from fastapi import HTTPException

from api import core
from api.core import (
    in_parallel,
)
from data import DataUnavailableError
from engine import apply_positions, compute_benchmark, compute_returns
from portfolio import (
    align_closes,
    equal_weights,
    inverse_vol_weights,
)
from risk import apply_stops, size_positions
from schemas import (
    BacktestRequest,
    PortfolioRequest,
)
from strategies import build_positions


def simulate(req: BacktestRequest):
    """Fetch the prices and run one backtest: signals, overlays, engine.

    Shared by POST /api/backtest and the share card, so a card can never show
    a different number from the run it links to. Returns (close, returns,
    engine output, buy-and-hold equity, data source).
    """
    # 1. Fetch data — a bad ticker or an empty range is the user's mistake, so
    # surface it as a 400 with the underlying reason rather than a 500.
    try:
        df = core.fetch_ohlcv(req.ticker, req.start, req.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    data_source = df.attrs.get("data_source", "yfinance")
    close = df["Close"]

    if len(close) < req.warmup_bars() + 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(close)} trading days returned for {req.ticker} in this range — "
                "not enough history for the chosen indicator and sizing windows."
            ),
        )

    # 2. Signals — direction only
    signals = build_positions(close, req.strategy, req.strategy_params())
    returns = compute_returns(close)

    # 3. Risk overlays. Order matters: stops decide whether the trade is still
    # open, sizing decides how large it is. Sizing first would scale a position
    # that the stop is about to close, and the stop's own P&L tracking would
    # then be measuring a moving target rather than the trade.
    signals = apply_stops(signals, returns, req.stop_loss, req.take_profit)
    signals = size_positions(
        signals,
        returns,
        sizing=req.sizing,
        target_vol=req.target_vol,
        vol_window=req.vol_window,
        max_leverage=req.max_leverage,
    )

    # 4. Engine
    engine_out = apply_positions(signals, returns, req.transaction_cost)
    benchmark = compute_benchmark(close)
    return close, returns, engine_out, benchmark, data_source


def fetch_aligned(req: PortfolioRequest) -> tuple[pd.DataFrame, dict, str]:
    """Fetch every leg, align on shared days, reject a book too short to warm up.

    Every leg is fetched before anything is computed — one bad ticker should
    fail the request outright rather than silently yielding a smaller
    portfolio than the user asked for.
    """
    def fetch(symbol):
        try:
            return core.fetch_ohlcv(symbol, req.start, req.end)
        except (ValueError, DataUnavailableError) as exc:
            return exc

    # The legs' price reads are independent round trips, so they go out
    # together. Errors are reported in the order the user listed the tickers.
    frames = in_parallel(*[lambda s=symbol: fetch(s) for symbol in req.tickers])
    closes = {}
    sources = set()
    for symbol, df in zip(req.tickers, frames):
        if isinstance(df, ValueError):
            raise HTTPException(status_code=400, detail=f"{symbol}: {df}") from df
        if isinstance(df, DataUnavailableError):
            raise HTTPException(status_code=503, detail=f"{symbol}: {df}") from df
        closes[symbol] = df["Close"]
        sources.add(df.attrs.get("data_source", "yfinance"))
    # One stale leg makes the whole portfolio stale — that is the flag that matters.
    data_source = "cache-stale" if "cache-stale" in sources else "mixed" if len(sources) > 1 else next(iter(sources))

    try:
        aligned = align_closes(closes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(aligned) < req.warmup_bars() + 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(aligned)} trading days are shared by all "
                f"{len(req.tickers)} tickers — not enough for the chosen "
                "indicator and weighting windows."
            ),
        )
    return aligned, closes, data_source


def portfolio_weights(req: PortfolioRequest, aligned: pd.DataFrame) -> pd.DataFrame:
    """The weight path the request asked for, on the aligned index."""
    if req.weighting == "inverse_vol":
        # Weights follow the *assets'* volatility, not the strategy's, so a leg
        # that happens to sit flat does not get an unbounded weight.
        asset_returns = aligned.pct_change().fillna(0.0)
        try:
            return inverse_vol_weights(
                asset_returns, window=req.weight_window, max_weight=req.max_weight
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return equal_weights(list(aligned.columns), aligned.index)

