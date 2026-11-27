"""User-defined rules: a strategy as data, not code (PRODUCT-PLAN Phase 2).

A rule is plain JSON, so it can be saved, shared, validated, cached and run by
the same engine as the three built-in strategies:

    {
      "direction": "long",                       # or "short"
      "entry": {"all": [                         # "all" (and) or "any" (or)
        {"left": {"ind": "rsi", "n": 14}, "op": "<", "right": {"value": 30}},
        {"left": {"ind": "close"}, "op": ">", "right": {"ind": "sma", "n": 200}}
      ]},
      "exit": {"any": [
        {"left": {"ind": "rsi", "n": 14}, "op": ">", "right": {"value": 70}}
      ]}
    }

The position is a simple state machine: flat until the entry fires, then held
until the exit fires. If both fire on the same bar the exit wins, the
conservative reading. Like every generator in signals.py the result is
shifted one bar, so a signal seen at a close is acted on at the next bar and
no rule can look ahead.

Indicators reuse signals.py where it already has them (moving average,
momentum, MACD, Bollinger), so a rule and a built-in strategy compute the same
number the same way. Nothing here imports the web layer or the database.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from signals import compute_bollinger, compute_macd, compute_momentum, compute_moving_average

# Bounds that keep a rule cheap and its warm-up sane.
MAX_CONDITIONS = 8
MIN_WINDOW, MAX_WINDOW = 2, 400
OPS = ("<", ">", "<=", ">=", "crosses_above", "crosses_below")

# name -> (parameters with defaults, bars of warm-up as a function of them)
INDICATORS = {
    "close": ({}, lambda p: 0),
    "sma": ({"n": 20}, lambda p: p["n"]),
    "ema": ({"n": 20}, lambda p: p["n"]),
    "rsi": ({"n": 14}, lambda p: p["n"] + 1),
    "momentum": ({"n": 20}, lambda p: p["n"]),
    "highest": ({"n": 20}, lambda p: p["n"]),
    "lowest": ({"n": 20}, lambda p: p["n"]),
    "macd": ({"fast": 12, "slow": 26}, lambda p: p["slow"]),
    "macd_signal": ({"fast": 12, "slow": 26, "signal": 9}, lambda p: p["slow"] + p["signal"]),
    "bb_upper": ({"n": 20, "k": 2.0}, lambda p: p["n"]),
    "bb_lower": ({"n": 20, "k": 2.0}, lambda p: p["n"]),
    "bb_middle": ({"n": 20}, lambda p: p["n"]),
}


class RuleError(ValueError):
    """A rule that cannot be run, with a message meant for the person who wrote it."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _operand(spec, where: str) -> dict:
    if not isinstance(spec, dict):
        raise RuleError(f"{where}: expected an indicator or a value.")
    if "value" in spec:
        if set(spec) != {"value"}:
            raise RuleError(f"{where}: a value takes nothing else.")
        v = spec["value"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v):
            raise RuleError(f"{where}: value must be a finite number.")
        return {"value": float(v)}
    name = spec.get("ind")
    if name not in INDICATORS:
        raise RuleError(f"{where}: unknown indicator {name!r}. Choose one of: {', '.join(INDICATORS)}.")
    defaults, _ = INDICATORS[name]
    extra = set(spec) - {"ind"} - set(defaults)
    if extra:
        raise RuleError(f"{where}: {name} does not take {', '.join(sorted(extra))}.")
    params = {**defaults, **{k: spec[k] for k in defaults if k in spec}}
    for key, val in params.items():
        if key == "k":
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not 0.1 <= val <= 5:
                raise RuleError(f"{where}: {name} k must be between 0.1 and 5.")
            params[key] = float(val)
        else:
            if isinstance(val, bool) or not isinstance(val, int) or not MIN_WINDOW <= val <= MAX_WINDOW:
                raise RuleError(f"{where}: {name} {key} must be a whole number from {MIN_WINDOW} to {MAX_WINDOW}.")
    if name.startswith("macd") and params["fast"] >= params["slow"]:
        raise RuleError(f"{where}: macd fast must be shorter than slow.")
    return {"ind": name, **params}


def _block(spec, where: str) -> dict:
    if not isinstance(spec, dict) or len(spec) != 1 or next(iter(spec)) not in ("all", "any"):
        raise RuleError(f"{where}: expected {{\"all\": [...]}} or {{\"any\": [...]}}.")
    mode, conds = next(iter(spec.items()))
    if not isinstance(conds, list) or not conds:
        raise RuleError(f"{where}: needs at least one condition.")
    if len(conds) > MAX_CONDITIONS:
        raise RuleError(f"{where}: at most {MAX_CONDITIONS} conditions.")
    out = []
    for i, c in enumerate(conds, 1):
        here = f"{where} condition {i}"
        if not isinstance(c, dict) or set(c) != {"left", "op", "right"}:
            raise RuleError(f"{here}: needs exactly left, op and right.")
        if c["op"] not in OPS:
            raise RuleError(f"{here}: op must be one of {', '.join(OPS)}.")
        left, right = _operand(c["left"], f"{here} left"), _operand(c["right"], f"{here} right")
        if "value" in left and "value" in right:
            raise RuleError(f"{here}: compares two fixed values, so it never changes.")
        out.append({"left": left, "op": c["op"], "right": right})
    return {mode: out}


def validate(rule) -> dict:
    """The rule in canonical form (defaults filled in), or RuleError."""
    if not isinstance(rule, dict):
        raise RuleError("A rule is an object with direction, entry and exit.")
    unknown = set(rule) - {"direction", "entry", "exit"}
    if unknown:
        raise RuleError(f"Unknown field(s): {', '.join(sorted(unknown))}.")
    direction = rule.get("direction", "long")
    if direction not in ("long", "short"):
        raise RuleError("direction must be long or short.")
    if "entry" not in rule or "exit" not in rule:
        raise RuleError("A rule needs both an entry and an exit.")
    return {"direction": direction, "entry": _block(rule["entry"], "entry"), "exit": _block(rule["exit"], "exit")}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _rsi(close: pd.Series, n: int) -> pd.Series:
    """RSI with Wilder's smoothing (1/n), run as an exponential average from
    the first bar. Charting packages seed it with a simple average of the
    first n bars instead; the seed's weight decays as (1 - 1/n)^t, so after a
    few times n bars (well inside any warm-up worth using) the two agree to
    rounding."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = gain / loss
    rsi = 100 - 100 / (1 + rs)
    # No losses in the window: RSI is 100 by definition, not NaN.
    return rsi.where(loss != 0, 100.0).where(gain.notna())


def _series(close: pd.Series, op: dict) -> pd.Series:
    if "value" in op:
        return pd.Series(op["value"], index=close.index, dtype=float)
    name = op["ind"]
    if name == "close":
        return close.astype(float)
    if name == "sma":
        return compute_moving_average(close, op["n"])
    if name == "ema":
        return close.ewm(span=op["n"], adjust=False, min_periods=op["n"]).mean()
    if name == "rsi":
        return _rsi(close, op["n"])
    if name == "momentum":
        return compute_momentum(close, op["n"])
    if name == "highest":
        return close.rolling(op["n"]).max()
    if name == "lowest":
        return close.rolling(op["n"]).min()
    if name in ("macd", "macd_signal"):
        line, signal, _ = compute_macd(close, op["fast"], op["slow"], op.get("signal", 9))
        out = line if name == "macd" else signal
        # The recursive EMA has a value from bar 0; it means nothing before warm-up.
        warm = op["slow"] + (op.get("signal", 0) if name == "macd_signal" else 0)
        return out.where(np.arange(len(close)) >= warm - 1)
    middle, upper, lower = compute_bollinger(close, op["n"], op.get("k", 2.0))
    return {"bb_upper": upper, "bb_lower": lower, "bb_middle": middle}[name]


def _condition(close: pd.Series, c: dict) -> pd.Series:
    a, b = _series(close, c["left"]), _series(close, c["right"])
    valid = a.notna() & b.notna()
    op = c["op"]
    if op == "<":
        hit = a < b
    elif op == ">":
        hit = a > b
    elif op == "<=":
        hit = a <= b
    elif op == ">=":
        hit = a >= b
    else:
        before = valid & valid.shift(1, fill_value=False)
        if op == "crosses_above":
            hit = (a > b) & (a.shift(1) <= b.shift(1)) & before
        else:
            hit = (a < b) & (a.shift(1) >= b.shift(1)) & before
    return (hit & valid).astype(bool)


def _block_hits(close: pd.Series, block: dict) -> pd.Series:
    mode, conds = next(iter(block.items()))
    hits = [_condition(close, c) for c in conds]
    out = hits[0]
    for h in hits[1:]:
        out = (out & h) if mode == "all" else (out | h)
    return out


def build_rule_positions(close: pd.Series, rule) -> pd.Series:
    """Positions (+1 long, -1 short, 0 flat) for a rule, shifted one bar."""
    rule = validate(rule)
    entry = _block_hits(close, rule["entry"])
    exit_ = _block_hits(close, rule["exit"])
    side = 1.0 if rule["direction"] == "long" else -1.0

    state = pd.Series(np.nan, index=close.index)
    state[entry] = side
    state[exit_] = 0.0  # the exit wins a tie
    raw = state.ffill().fillna(0.0)
    return raw.shift(1).fillna(0.0)


def _operands(rule: dict):
    for side in ("entry", "exit"):
        for c in next(iter(rule[side].values())):
            yield c["left"]
            yield c["right"]


def rule_warmup(rule) -> int:
    """Bars of history the rule's indicators need before they mean anything."""
    rule = validate(rule)
    need = 0
    for op in _operands(rule):
        if "ind" in op:
            _, warm = INDICATORS[op["ind"]]
            need = max(need, warm(op))
    # A cross compares with the bar before, and positions are shifted once.
    return need + 2
