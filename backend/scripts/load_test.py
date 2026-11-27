"""Load test: how many backtests and validations one API process serves.

    cd backend && .venv/bin/python scripts/load_test.py                 # default plan
    cd backend && .venv/bin/python scripts/load_test.py --json out.json # also save the numbers

It starts the real app (main.app, every route, middleware and the engine) in a
separate process, the way one Cloud Run instance runs it: one uvicorn process,
blocking routes on its thread pool. Only the outside world is faked, so the
numbers measure our code and nothing else:

  - auth, Firestore and the rate-limit store are the offline fakes from
    offline_api.py (the account is an admin-granted unlimited one);
  - prices are synthetic, 10 years of business days per ticker, generated
    once per ticker and kept in memory. Yahoo is never called: hammering it
    from a load test would break its terms and measure Yahoo, not us.

So this is the ceiling with a warm price cache. A cold ticker adds a Yahoo
download (about 0.5-2 s) on top, once per ticker per instance.

The server is a child process so the load generator's own work does not
compete with it for the interpreter lock. Results depend on the machine: on
a laptop with several fast cores, expect more than one Cloud Run vCPU gives.
"""

import argparse
import asyncio
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# What each scenario sends, and how hard. (name, path, body builder, concurrency, requests)
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
STRATEGIES = ["momentum", "macd", "bollinger"]


def backtest_body(i):
    return {
        "ticker": TICKERS[i % len(TICKERS)],
        "strategy": STRATEGIES[i % len(STRATEGIES)],
        "start": "2016-01-01",
        "end": "2026-01-01",
    }


def unique_body(i):
    """A backtest no earlier request asked for: the result cache cannot help."""
    day = 1 + (i % 28)
    month = 1 + (i // 28) % 12
    year = 2016 + (i // 336)
    return {**backtest_body(i), "start": f"{year}-{month:02d}-{day:02d}"}


_unique_offset = [0]


def fresh_body(i):
    # Every scenario gets its own range of unique requests.
    return unique_body(_unique_offset[0] + i)


# (name, path, body builder, concurrency, requests). "backtest" repeats 24
# set-ups (8 tickers x 3 strategies), so after the first of each it is served
# from the result cache; "backtest-new" never repeats, the uncached cost.
PLAN = [
    ("backtest-new", "/api/v1/backtest", fresh_body, 1, 20),
    ("backtest-new", "/api/v1/backtest", fresh_body, 20, 100),
    ("backtest", "/api/v1/backtest", backtest_body, 1, 20),
    ("backtest", "/api/v1/backtest", backtest_body, 5, 50),
    ("backtest", "/api/v1/backtest", backtest_body, 20, 100),
    ("backtest", "/api/v1/backtest", backtest_body, 40, 120),
    ("validate", "/api/v1/validate", backtest_body, 1, 4),
    ("validate", "/api/v1/validate", backtest_body, 4, 8),
]


# ---------------------------------------------------------------------------
# Server side (child process)
# ---------------------------------------------------------------------------

def serve(port: int) -> None:
    # Limits high enough never to trip, set before the app reads them.
    os.environ.update({
        "RATE_LIMIT_STORE": "memory",
        "RATE_LIMIT_IP_PER_MIN": "1000000",
        "RATE_LIMIT_BACKTEST_PER_MIN": "1000000",
        "RATE_LIMIT_VALIDATE_PER_MIN": "1000000",
        "LOG_LEVEL": "WARNING",
    })
    sys.path.insert(0, str(HERE))
    import numpy as np
    import pandas as pd

    import offline_api  # noqa: F401  (fakes auth and Firestore, imports main)
    from api import core
    import main
    import uvicorn

    cache = {}

    def fake_prices(ticker, start, end):
        if ticker not in cache:
            seed = sum(map(ord, ticker))
            rng = np.random.default_rng(seed)
            idx = pd.bdate_range("2015-01-01", "2026-01-01")
            close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, len(idx))))
            cache[ticker] = pd.DataFrame(
                {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000},
                index=idx,
            )
        df = cache[ticker]
        out = df[(df.index >= pd.Timestamp(start)) & (df.index < pd.Timestamp(end))].copy()
        out.attrs["data_source"] = "memory"
        return out

    core.fetch_ohlcv = fake_prices
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning", access_log=False)


# ---------------------------------------------------------------------------
# Client side
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_ready(base: str, timeout: float = 60.0) -> None:
    import httpx
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient() as c:
        while time.monotonic() < deadline:
            try:
                if (await c.get(f"{base}/api/health")).status_code == 200:
                    return
            except httpx.TransportError:
                pass
            await asyncio.sleep(0.25)
    raise RuntimeError("the API did not start")


def _pct(values, p):
    if not values:
        return None
    ordered = sorted(values)
    k = min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))
    return ordered[k]


async def run_scenario(base, name, path, body, concurrency, total):
    import httpx
    latencies, errors = [], {}
    queue = asyncio.Queue()
    for i in range(total):
        queue.put_nowait(i)

    async def worker(client):
        while True:
            try:
                i = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            t0 = time.perf_counter()
            try:
                r = await client.post(f"{base}{path}", json=body(i), headers={"Authorization": "Bearer x"})
                code = r.status_code
            except httpx.HTTPError as exc:
                code = type(exc).__name__
            dt = time.perf_counter() - t0
            if code == 200:
                latencies.append(dt)
            else:
                errors[str(code)] = errors.get(str(code), 0) + 1

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=300, limits=limits) as client:
        # One untimed request per scenario so a first-call cost is not counted.
        # body(total) is outside the timed range, so for unique requests the
        # warm-up never pre-fills the cache for a timed one.
        await client.post(f"{base}{path}", json=body(total), headers={"Authorization": "Bearer x"})
        started = time.perf_counter()
        await asyncio.gather(*(worker(client) for _ in range(concurrency)))
        wall = time.perf_counter() - started

    ok = len(latencies)
    return {
        "scenario": name,
        "concurrency": concurrency,
        "requests": total,
        "ok": ok,
        "errors": errors,
        "throughput_per_s": round(ok / wall, 2) if wall else None,
        "p50_s": round(statistics.median(latencies), 3) if latencies else None,
        "p95_s": round(_pct(latencies, 95), 3) if latencies else None,
        "max_s": round(max(latencies), 3) if latencies else None,
    }


async def run_all(base):
    results = []
    for name, path, body, concurrency, total in PLAN:
        res = await run_scenario(base, name, path, body, concurrency, total)
        _unique_offset[0] += total + 1
        results.append(res)
        print(
            f"{res['scenario']:12} c={res['concurrency']:<3} n={res['requests']:<4} "
            f"ok={res['ok']:<4} {res['throughput_per_s']:>7} req/s  "
            f"p50 {res['p50_s']}s  p95 {res['p95_s']}s  max {res['max_s']}s  errors {res['errors'] or '-'}",
            flush=True,
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--serve", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--json", type=Path, help="write the results here as JSON")
    args = parser.parse_args()

    if args.serve:
        serve(args.serve)
        return

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, __file__, "--serve", str(port)], cwd=HERE.parent)
    try:
        asyncio.run(_wait_ready(base))
        results = asyncio.run(run_all(base))
    finally:
        server.terminate()
        server.wait(timeout=30)

    if args.json:
        args.json.write_text(json.dumps({
            "generated": time.strftime("%Y-%m-%d %H:%M"),
            "machine": f"{platform.system()} {platform.machine()}, {os.cpu_count()} logical CPUs",
            "python": platform.python_version(),
            "results": results,
        }, indent=1) + "\n")


if __name__ == "__main__":
    main()
