"""Strategy registry — one place that knows how each strategy is parameterised.

Adding a strategy means adding one entry here plus its generator in signals.py.
Nothing in main.py, engine.py, or validation.py needs to change, because they
all go through `build_positions` and `longest_window`.
"""

import pandas as pd

from rules import build_rule_positions, rule_warmup
from signals import (
    generate_signals,
    generate_macd_signals,
    generate_bollinger_signals,
)


def _momentum(close: pd.Series, p: dict) -> pd.Series:
    return generate_signals(
        close,
        p.get("momentum_lookback", 20),
        p.get("ma_window", 50),
        p.get("momentum_threshold", 0.02),
    )


def _macd(close: pd.Series, p: dict) -> pd.Series:
    return generate_macd_signals(
        close,
        p.get("macd_fast", 12),
        p.get("macd_slow", 26),
        p.get("macd_signal", 9),
    )


def _bollinger(close: pd.Series, p: dict) -> pd.Series:
    return generate_bollinger_signals(
        close,
        p.get("bb_window", 20),
        p.get("bb_std", 2.0),
    )


STRATEGIES = {
    "momentum": {
        "label": "Momentum",
        "build": _momentum,
        # Bars of history the indicators need before they mean anything.
        "warmup": lambda p: max(p.get("momentum_lookback", 20), p.get("ma_window", 50)),
        # Grid swept by walk-forward validation.
        "grid": [
            {"momentum_lookback": lb, "ma_window": maw}
            for lb in (10, 20, 40, 60)
            for maw in (20, 50, 100, 200)
        ],
    },
    "macd": {
        "label": "MACD",
        "build": _macd,
        "warmup": lambda p: p.get("macd_slow", 26) + p.get("macd_signal", 9),
        "grid": [
            {"macd_fast": f, "macd_slow": s, "macd_signal": 9}
            for f, s in ((8, 17), (12, 26), (16, 34), (19, 39))
        ],
    },
    "bollinger": {
        "label": "Bollinger",
        "build": _bollinger,
        "warmup": lambda p: p.get("bb_window", 20),
        "grid": [
            {"bb_window": w, "bb_std": sd}
            for w in (10, 20, 30, 50)
            for sd in (1.5, 2.0, 2.5)
        ],
    },
}

STRATEGY_NAMES = tuple(STRATEGIES)

# A user's own rule (rules.py), run by the same engine. Deliberately not in
# STRATEGIES: that tuple is the built-in list the studies, the strategy pages
# and /api/strategies iterate.
#
# Its grid is the rule itself and nothing else: one candidate. Validation then
# asks the questions that still make sense of a fixed rule — does it hold up
# after the split, in every rolling fold, against random timing, against
# buy-and-hold — and has no in-sample search to correct for. Searching
# variations of the user's rule would be validating a rule they did not write.
RULE_STRATEGY = "rules"
_RULES = {
    "label": "Your own rule",
    "build": lambda close, p: build_rule_positions(close, p["rule"]),
    "warmup": lambda p: rule_warmup(p["rule"]),
    "grid": ({},),
}


def _get(strategy: str) -> dict:
    if strategy == RULE_STRATEGY:
        return _RULES
    try:
        return STRATEGIES[strategy]
    except KeyError:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Choose one of: {', '.join(STRATEGY_NAMES)}."
        ) from None


def build_positions(close: pd.Series, strategy: str, params: dict) -> pd.Series:
    """Position series (+1/-1/0) for any registered strategy, already lag-shifted."""
    return _get(strategy)["build"](close, params or {})


def longest_window(strategy: str, params: dict) -> int:
    """Bars of warm-up the strategy needs before it can emit a real signal."""
    return int(_get(strategy)["warmup"](params or {}))


def param_grid(strategy: str) -> list[dict]:
    """Parameter combinations for walk-forward validation to sweep."""
    return list(_get(strategy)["grid"])
