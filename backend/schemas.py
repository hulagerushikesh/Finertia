"""Request models and their validation rules.

Deliberately free of any Firebase or FastAPI-app dependency, so the validation
logic can be imported and tested without credentials.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from strategies import STRATEGY_NAMES, longest_window

# Which fields each strategy actually consumes. Everything else on the model
# keeps its default and is ignored for that strategy.
STRATEGY_FIELDS = {
    "momentum": ("momentum_lookback", "ma_window", "momentum_threshold"),
    "macd": ("macd_fast", "macd_slow", "macd_signal"),
    "bollinger": ("bb_window", "bb_std"),
}

TRADING_DAYS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365

# Fields that belong to the risk overlays rather than to a strategy. A run
# document stores strategy params and overlay params in one flat map, so this
# is what /api/compare splits them back apart with — single source of truth, so
# adding an overlay field cannot leave the two halves disagreeing.
RISK_KEYS = ("stop_loss", "take_profit", "sizing", "target_vol", "vol_window", "max_leverage")


class BacktestRequest(BaseModel):
    """Parameters for a backtest run.

    Every strategy's parameters live on one flat model. Only those belonging to
    the selected strategy are read.
    """

    ticker: str
    start: str
    end: str
    strategy: str = "momentum"
    transaction_cost: float = Field(0.001, ge=0.0, le=0.1)

    # Momentum
    momentum_lookback: int = Field(20, ge=5, le=200)
    ma_window: int = Field(50, ge=5, le=300)
    momentum_threshold: float = Field(0.02, ge=0.0, le=1.0)

    # MACD
    macd_fast: int = Field(12, ge=2, le=100)
    macd_slow: int = Field(26, ge=3, le=200)
    macd_signal: int = Field(9, ge=2, le=100)

    # Bollinger
    bb_window: int = Field(20, ge=5, le=200)
    bb_std: float = Field(2.0, ge=0.5, le=4.0)

    # Risk overlays — independent of the strategy, so every one of them gets
    # stops and sizing without knowing they exist.
    stop_loss: Optional[float] = Field(None, gt=0, le=0.9)
    take_profit: Optional[float] = Field(None, gt=0, le=5.0)
    sizing: str = "fixed"
    target_vol: float = Field(0.15, gt=0, le=2.0)
    vol_window: int = Field(20, ge=2, le=250)
    max_leverage: float = Field(2.0, gt=0, le=5.0)

    def risk_params(self) -> dict:
        """The overlay settings, separated from the signal parameters."""
        return {k: getattr(self, k) for k in RISK_KEYS}

    def warmup_bars(self) -> int:
        """Bars needed before the config can produce a real, sized position.

        Volatility targeting needs its own trailing window on top of whatever
        the indicator needs — without counting it, a range long enough for the
        signal but not the sizing returns an all-flat backtest with no
        explanation.
        """
        warmup = longest_window(self.strategy, self.strategy_params())
        if self.sizing == "vol_target":
            warmup = max(warmup, self.vol_window)
        return warmup

    @field_validator("sizing")
    @classmethod
    def _validate_sizing(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ("fixed", "vol_target"):
            raise ValueError("sizing must be 'fixed' or 'vol_target'")
        return cleaned

    def strategy_params(self) -> dict:
        """Only the parameters the selected strategy actually consumes."""
        return {k: getattr(self, k) for k in STRATEGY_FIELDS.get(self.strategy, ())}

    @field_validator("strategy")
    @classmethod
    def _validate_strategy(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in STRATEGY_NAMES:
            raise ValueError(
                f"Unknown strategy '{v}'. Choose one of: {', '.join(STRATEGY_NAMES)}."
            )
        return cleaned

    @field_validator("ticker")
    @classmethod
    def _validate_ticker(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Ticker is required")
        if len(cleaned) > 12:
            raise ValueError("Ticker must be 12 characters or fewer")
        if not all(c.isalnum() or c in ".-^=" for c in cleaned):
            raise ValueError("Ticker may only contain letters, digits, and . - ^ =")
        return cleaned

    @field_validator("start", "end")
    @classmethod
    def _validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v.strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"'{v}' is not a valid date — use YYYY-MM-DD") from None
        return v.strip()

    @model_validator(mode="after")
    def _validate_range(self) -> "BacktestRequest":
        start_d = datetime.strptime(self.start, "%Y-%m-%d").date()
        end_d = datetime.strptime(self.end, "%Y-%m-%d").date()

        if start_d >= end_d:
            raise ValueError("Start date must be before end date")
        if end_d > date.today():
            raise ValueError("End date cannot be in the future")

        if self.strategy == "macd" and self.macd_fast >= self.macd_slow:
            raise ValueError("MACD fast period must be shorter than the slow period")

        # Indicators need a full window of history before they emit a real
        # signal, so a range shorter than the warm-up gives an all-flat backtest.
        if (
            self.stop_loss is not None
            and self.take_profit is not None
            and self.take_profit <= self.stop_loss
        ):
            raise ValueError(
                "Take-profit must be further from entry than the stop-loss, "
                "otherwise every trade closes at a profit target it reaches first by chance."
            )

        calendar_days = (end_d - start_d).days
        approx_trading_days = int(calendar_days * TRADING_DAYS_PER_YEAR / CALENDAR_DAYS_PER_YEAR)
        signal_warmup = longest_window(self.strategy, self.strategy_params())
        warmup = self.warmup_bars()
        if warmup >= approx_trading_days:
            # Name whichever component is actually binding — "this config needs
            # 200 bars" leaves the user guessing which knob to turn.
            driver = (
                f"the {self.strategy} strategy needs {signal_warmup} bars"
                if signal_warmup >= warmup
                else f"volatility targeting needs {self.vol_window} bars"
            )
            raise ValueError(
                f"Date range is too short: ~{approx_trading_days} trading days available, "
                f"but {driver} to warm up. Widen the date range, reduce the "
                "indicator windows, or shorten the volatility window."
            )
        return self


class ValidateRequest(BacktestRequest):
    """A backtest config plus the knobs for the overfitting checks."""

    split_ratio: float = Field(0.7, ge=0.5, le=0.9)
    permutation_trials: int = Field(500, ge=100, le=2000)


class PortfolioRequest(BacktestRequest):
    """One strategy run across several tickers and combined into a portfolio.

    Inherits every strategy and risk rule from BacktestRequest so a portfolio
    leg is validated exactly like a single-ticker run. The inherited `ticker`
    field is populated from the first entry of `tickers` before validation, so
    the parent's date/warm-up checks have something to work with.
    """

    tickers: list[str] = Field(..., min_length=2, max_length=10)
    weighting: str = "equal"
    weight_window: int = Field(60, ge=2, le=250)
    max_weight: float = Field(1.0, gt=0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def _seed_ticker(cls, data):
        if isinstance(data, dict) and data.get("tickers"):
            first = next((t for t in data["tickers"] if str(t).strip()), None)
            if first:
                data = {**data, "ticker": first}
        return data

    @field_validator("tickers")
    @classmethod
    def _clean_tickers(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().upper() for t in v if t and t.strip()]
        if len(cleaned) < 2:
            raise ValueError("A portfolio needs at least two tickers")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError(
                "The same ticker appears more than once — that is a bigger "
                "position in one name, not a second holding."
            )
        for symbol in cleaned:
            if len(symbol) > 12 or not all(c.isalnum() or c in ".-^=" for c in symbol):
                raise ValueError(f"'{symbol}' is not a valid ticker")
        return cleaned

    @field_validator("weighting")
    @classmethod
    def _validate_weighting(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ("equal", "inverse_vol"):
            raise ValueError("weighting must be 'equal' or 'inverse_vol'")
        return cleaned

    @model_validator(mode="after")
    def _validate_portfolio(self) -> "PortfolioRequest":
        n = len(self.tickers)
        if self.max_weight * n < 1.0:
            raise ValueError(
                f"A cap of {self.max_weight} cannot fill a book of {n} tickers — "
                f"it must be at least {1 / n:.3f}."
            )
        return self

    def warmup_bars(self) -> int:
        """Portfolio warm-up also has to cover the weighting window."""
        warmup = super().warmup_bars()
        if self.weighting == "inverse_vol":
            warmup = max(warmup, self.weight_window)
        return warmup


class CompareRequest(BaseModel):
    """Run ids to overlay against each other.

    Capped at four because the comparison chart stops being readable beyond that,
    and each id costs one market-data fetch plus a full recompute.
    """

    run_ids: list[str] = Field(..., min_length=2, max_length=4)

    @field_validator("run_ids")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) < 2:
            raise ValueError("Select at least two runs to compare")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("The same run was selected more than once")
        return cleaned


class UserPatch(BaseModel):
    """Allowed fields for admin user patch."""

    isActive: Optional[bool] = None
    role: Optional[str] = None
