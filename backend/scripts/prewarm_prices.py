"""Fill the Firestore price cache for the tickers the UI suggests.

    cd backend && .venv/bin/python scripts/prewarm_prices.py [--since 2015] [TICKER ...]

Runs against production Firestore using FIREBASE_SERVICE_ACCOUNT_JSON from
the environment (or backend/.env). One yfinance call per ticker, one batched
write per ticker. Prints how long a cold read takes before and after, which
is the number the cache exists to move.

Re-running is safe: every ticker is rewritten under a fresh batch id, which is
exactly what a refresh is supposed to do.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import data  # noqa: E402
from price_store import FirestorePriceStore  # noqa: E402

# Mirrors COMMON_TICKERS in frontend/src/components/ConfigPanel.jsx. Kept as a
# literal here rather than parsed out of the JSX so this script has no
# dependency on the frontend tree being checked out.
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT",
    "XOM", "JNJ", "KO", "DIS", "NFLX", "AMD", "INTC", "BA",
    "SPY", "QQQ", "IWM", "DIA", "GLD", "TLT",
    "BTC-USD", "ETH-USD", "^GSPC", "^IXIC",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*", default=DEFAULT_TICKERS)
    ap.add_argument("--since", type=int, default=2015, help="first year to cache")
    args = ap.parse_args()

    store = FirestorePriceStore()
    data.configure_store(store)
    end = f"{data._now().year}-12-31"
    start = f"{args.since}-01-01"

    ok, failed = [], []
    for t in args.tickers:
        data._cache.clear()
        t0 = time.perf_counter()
        try:
            df = data.fetch_ohlcv(t, start, end)
        except Exception as exc:  # noqa: BLE001 — report and continue
            failed.append((t, str(exc)))
            print(f"  {t:<8} FAILED  {exc}")
            continue
        warm = time.perf_counter() - t0
        data._cache.clear()
        t0 = time.perf_counter()
        df2 = data.fetch_ohlcv(t, start, end)
        cold_read = time.perf_counter() - t0
        ok.append(t)
        print(
            f"  {t:<8} {len(df):>5} bars  {df.attrs['data_source']:<8} {warm*1000:7.0f} ms"
            f"  -> {df2.attrs['data_source']:<6} {cold_read*1000:6.0f} ms"
        )

    print(f"\n{len(ok)} cached, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
