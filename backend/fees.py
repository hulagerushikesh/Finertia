"""What a trade really costs in each market, as one cost per side.

The engine charges `transaction_cost` on every unit of turnover (engine.py).
Until now that was one number the user typed, 10 basis points by default.
This module turns a market into that number, from the charges a retail
investor actually pays there, so "after costs" means those costs.

Every charge is a fraction of the value traded, on the buy side, the sell
side, or both. The engine needs one figure per side, and over a full round
trip (every buy is later sold) the average of the buy and sell rates is
exact: a round trip costs buy + sell = 2 × average. The breakdown is kept so
the page can say where the number comes from.

What is in, as of the dates below:

United States, a commission-free broker:
- commission: 0;
- SEC Section 31 fee: $20.60 per million on sales, effective 4 Apr 2026
  (SEC fee rate advisory for fiscal 2026, 27 Feb 2026);
- FINRA Trading Activity Fee: $0.000195 per share sold, at most $9.79 a
  trade (paused 1 Oct – 31 Dec 2026). Per share, not per dollar: on a $20
  stock it is 0.1 bp of the sale, on a $100 stock 0.02 bp. It is left out,
  and this sentence is why.

India, equity delivery with a zero-brokerage discount broker:
- brokerage: 0;
- securities transaction tax (STT): 0.1% on buys and on sales (unchanged by
  the 2026 Budget, which raised it on derivatives only);
- stamp duty: 0.015% on buys;
- NSE transaction charge: 0.00307% on both sides (the rate broker tables
  give after NSE's 27 Feb 2026 circular; 0.00297% before it);
- SEBI turnover fee: ₹10 per crore, 0.0001%, both sides;
- GST: 18% on brokerage, the exchange charge and the SEBI fee.
- Left out: depository (DP) charges, a flat ~₹15 per stock per sell day,
  which is a fraction only once a trade size is known.

Both markets add slippage: the gap between the price a backtest assumes and
the price an order gets — half the bid-ask spread plus any move while the
order fills. It is the user's estimate, 2 bps a side by default, which is
reasonable for large, liquid stocks and too low for small ones.

The same rates are applied to the whole history. Fees in 2016 were not the
2026 fees; using today's says what this strategy would cost to run now.

Short positions: Indian cash equities cannot be held short overnight, so a
rule that goes short under the India model is priced, but not something a
retail account could actually hold.
"""

from __future__ import annotations

AS_OF = "2026-11-28"
DEFAULT_SLIPPAGE_BPS = 2.0

# fraction of value traded: (buy side, sell side)
_US = {
    "commission": (0.0, 0.0),
    "sec_fee": (0.0, 20.60 / 1_000_000),
}

_EXCHANGE = 0.0000307
_SEBI = 0.000001
_INDIA = {
    "brokerage": (0.0, 0.0),
    "stt": (0.001, 0.001),
    "stamp_duty": (0.00015, 0.0),
    "exchange": (_EXCHANGE, _EXCHANGE),
    "sebi_fee": (_SEBI, _SEBI),
    "gst": (0.18 * (_EXCHANGE + _SEBI), 0.18 * (_EXCHANGE + _SEBI)),
}

MODELS = {
    "us": {"label": "United States", "charges": _US},
    "india": {"label": "India, delivery", "charges": _INDIA},
}

LABELS = {
    "commission": "Commission",
    "sec_fee": "SEC fee (sales)",
    "brokerage": "Brokerage",
    "stt": "Securities transaction tax",
    "stamp_duty": "Stamp duty (buys)",
    "exchange": "Exchange charge",
    "sebi_fee": "SEBI turnover fee",
    "gst": "GST on charges",
    "slippage": "Slippage (your estimate)",
}


# Where a Yahoo symbol trades, for the "auto" choice: NSE (.NS) and BSE (.BO)
# listings are Indian cash equities; everything else is priced as US.
INDIAN_SUFFIXES = (".NS", ".BO")


def market_for(ticker: str) -> str:
    """The cost model a symbol's own market implies."""
    return "india" if ticker.upper().endswith(INDIAN_SUFFIXES) else "us"


def breakdown(model: str, slippage_bps: float = DEFAULT_SLIPPAGE_BPS) -> dict:
    """Each charge's buy and sell rate, the totals, and the per-side figure
    the engine uses. Rates are fractions of the value traded."""
    if model not in MODELS:
        raise ValueError(f"Unknown cost model '{model}'. Choose one of: flat, auto, {', '.join(MODELS)}.")
    slip = slippage_bps / 10_000
    charges = {**MODELS[model]["charges"], "slippage": (slip, slip)}
    buy = sum(b for b, _ in charges.values())
    sell = sum(s for _, s in charges.values())
    return {
        "model": model,
        "label": MODELS[model]["label"],
        "as_of": AS_OF,
        "slippage_bps": slippage_bps,
        "charges": [
            {"id": k, "label": LABELS[k], "buy": round(b, 9), "sell": round(s, 9)}
            for k, (b, s) in charges.items()
        ],
        "buy": round(buy, 9),
        "sell": round(sell, 9),
        "round_trip": round(buy + sell, 9),
        "per_side": round((buy + sell) / 2, 9),
    }


def per_side(model: str, slippage_bps: float = DEFAULT_SLIPPAGE_BPS) -> float:
    return breakdown(model, slippage_bps)["per_side"]


def describe() -> dict:
    """Every model at the default slippage — the table the front end mirrors
    (frontend/src/lib/costModels.json, kept equal by a test)."""
    return {
        "as_of": AS_OF,
        "default_slippage_bps": DEFAULT_SLIPPAGE_BPS,
        "models": {m: breakdown(m, DEFAULT_SLIPPAGE_BPS) for m in MODELS},
    }
