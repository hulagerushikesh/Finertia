"""Freeze the /demo page's backtest payload into frontend/src/demoData.json.

/demo shows a real backtest without an account (AAPL momentum 2019-2024,
default parameters). This re-runs it through the real /api/backtest handler,
same in-process approach as freeze_demo_validation.py, and writes the response
with the per-bar series thinned so the page stays light.

    cd backend && .venv/bin/python scripts/freeze_demo_backtest.py

Thinning keeps every STRIDE-th bar **and the last one**. The hand-thinned file
this replaced (24 Sep) dropped the final bar, so the page's "turned $1 into…"
line, read off the curve's last point, disagreed with the headline metrics.
Re-run when the backtest response shape changes, then re-run
freeze_demo_validation.py, which reads its config from this file.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reproduce_writeup  # noqa: E402,F401  (applies the auth/Firestore fakes)
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend/src/demoData.json"
STRIDE = 4

CONFIG = {
    "ticker": "AAPL",
    "start": "2019-01-01",
    "end": "2024-01-01",
    "strategy": "momentum",
    "transaction_cost": 0.001,
    "momentum_lookback": 20,
    "ma_window": 50,
    "momentum_threshold": 0.02,
}

# Per-bar series the page charts; everything else is kept whole.
THINNED = ("equity_curve", "drawdown", "rolling_sharpe")
# Per-trade detail the page never shows, and per-request fields that would
# change on every freeze for no reason.
DROPPED = ("trades", "runId", "duration_ms")


def thin(rows):
    keep = rows[::STRIDE]
    if rows and keep[-1] is not rows[-1]:
        keep.append(rows[-1])
    return keep


def run():
    client = TestClient(main.app, raise_server_exceptions=True)
    r = client.post("/api/backtest", json=CONFIG, headers={"Authorization": "Bearer x"})
    r.raise_for_status()
    data = r.json()
    # The response does not echo its request; the page (and
    # freeze_demo_validation.py) read the config from this file, so put it back.
    params = {k: CONFIG[k] for k in ("momentum_lookback", "ma_window", "momentum_threshold")}
    data = {
        **{k: CONFIG[k] for k in ("ticker", "start", "end", "strategy")},
        "params": params,
        "transaction_cost": CONFIG["transaction_cost"],
        "bars": len(data["equity_curve"]),
        **data,
    }
    for key in DROPPED:
        data.pop(key, None)
    for key in THINNED:
        if key in data:
            data[key] = thin(data[key])
    OUT.write_text(json.dumps(data, separators=(",", ":"), default=str) + "\n")

    last = data["equity_curve"][-1]
    print(
        f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} kB): "
        f"last bar {last['date']}, strategy {last['strategy']}, benchmark {last['benchmark']}, "
        f"total_return {data['metrics']['total_return']}"
    )


if __name__ == "__main__":
    run()
