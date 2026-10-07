"""Freeze the /demo page's validation payload into frontend/src/demoValidation.json.

/demo shows a real backtest without an account; this is the matching
/api/validate response for the same config (AAPL momentum 2019-2024, default
parameters), so a visitor can see the checks the product is built around.
Same in-process approach as reproduce_writeup.py — the real route handler,
only auth, Firestore and the rate limiters faked, fresh yfinance prices.

    cd backend && .venv/bin/python scripts/freeze_demo_validation.py

Re-run when the validation response shape changes; the demo page renders it
with the same ValidationPanel the dashboard uses.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reproduce_writeup  # noqa: E402,F401  (applies the auth/Firestore fakes)
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEMO = json.loads((ROOT / "frontend/src/demoData.json").read_text())
OUT = ROOT / "frontend/src/demoValidation.json"


def run():
    body = {
        "ticker": DEMO["ticker"],
        "start": DEMO["start"],
        "end": DEMO["end"],
        "strategy": DEMO["strategy"],
        "transaction_cost": DEMO["transaction_cost"],
        **DEMO["params"],
    }
    client = TestClient(main.app, raise_server_exceptions=True)
    r = client.post("/api/validate", json=body, headers={"Authorization": "Bearer x"})
    r.raise_for_status()
    data = r.json()
    OUT.write_text(json.dumps(data, separators=(",", ":"), default=str) + "\n")
    wf = data["walk_forward"]
    print(
        f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} kB): "
        f"verdict {wf['verdict']}, IS {wf['best_in_sample']['sharpe_ratio']:.3f}, "
        f"OOS {wf['best_out_of_sample']['sharpe_ratio']:.3f}, perm p {data['permutation']['p_value']}"
    )


if __name__ == "__main__":
    run()
