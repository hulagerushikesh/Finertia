"""Check every figure planning/research/nifty-write-up.md quotes, and redraw its chart.

    cd backend && .venv/bin/python scripts/reproduce_nifty.py

Reads the study's saved results (nifty-funnel, nifty-grid and nifty-perm .json), so it
runs in a second. Re-running the study itself from fresh prices is the job of
`nifty_study.py --check` and `nifty_grid.py --check`. Prints each quoted
figure beside the saved value, exits 1 if any no longer matches at the
precision quoted, and rewrites nifty-grid.svg. When the write-up changes a
number, change it in EXPECTED too.
"""

import json
import statistics
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2] / "planning" / "research"
FUNNEL = json.loads((RESEARCH / "nifty-funnel.json").read_text())
GRID = json.loads((RESEARCH / "nifty-grid.json").read_text())
PERM = json.loads((RESEARCH / "nifty-perm.json").read_text())


def rows(universe="start_2011", cost="default"):
    return FUNNEL["universes"][universe][cost]["rows"]


def funnel(universe="start_2011", cost="default"):
    return FUNNEL["universes"][universe][cost]["funnel"]


def row(symbol, strategy):
    return next(r for r in rows() if r["symbol"] == symbol and r["strategy"] == strategy)


def median(key, universe="start_2011", every=1):
    return statistics.median(r[key] for r in rows(universe)[::every])


def survivors(universe="start_2011"):
    return sorted(f"{r['symbol']} {r['strategy']}" for r in rows(universe) if r["survives"])


def perm_passes(cost):
    return sum(r["permutation_p"] < 0.05 for r in rows(cost=cost))


PTS = GRID["points"]
PICK = GRID["pick"]
SURVIVORS = ["RCOM.NS macd", "RCOM.NS momentum", "RELINFRA.NS macd", "RPOWER.NS macd"]

# (label, saved value, as quoted). Numbers compare at the quoted precision,
# so "0.16" matches 0.1589 and "0.159" would not.
EXPECTED = [
    ("missing from Yahoo", len(FUNNEL["missing_from_yahoo"]), "7"),
    ("2011 pairs tested", funnel()["tested"], "129"),
    ("2011 beat in-sample", funnel()["beat_in_sample"], "50"),
    ("2011 ahead out of sample", funnel()["ahead_out_of_sample"], "7"),
    ("2011 survive", funnel()["survives"], "4"),
    ("2011 survive, half cost", funnel(cost="half")["survives"], "4"),
    ("2011 survive, double cost", funnel(cost="double")["survives"], "3"),
    ("median in-sample Sharpe", median("is_sharpe"), "0.09"),
    ("median out-of-sample Sharpe", median("oos_sharpe"), "-0.18"),
    ("median hold, unseen years", median("bh_oos_sharpe", every=3), "0.59"),
    ("median hold, tuning years, 2011", median("bh_is_sharpe", every=3), "0.28"),
    ("median hold, tuning years, today", median("bh_is_sharpe", "today", every=3), "0.51"),
    ("survivors are the four named", survivors() == SURVIVORS, "True"),
    *[
        (f"{s} {k}", row(s, st)[k], q)
        for s, st, vals in [
            ("RCOM.NS", "momentum", ("0.898", "1.824", "-0.506", "-0.452")),
            ("RCOM.NS", "macd", ("0.932", "3.041", "-0.506", "-0.452")),
            ("RELINFRA.NS", "macd", ("1.268", "0.445", "-0.390", "0.366")),
            ("RPOWER.NS", "macd", ("1.621", "0.955", "-0.462", "0.505")),
        ]
        for k, q in zip(("is_sharpe", "oos_sharpe", "bh_is_sharpe", "bh_oos_sharpe"), vals)
    ],
    ("today tested", funnel("today")["tested"], "150"),
    ("today beat in-sample", funnel("today")["beat_in_sample"], "33"),
    ("today ahead out of sample", funnel("today")["ahead_out_of_sample"], "4"),
    ("today survivor is Adani momentum", survivors("today") == ["ADANIENT.NS momentum"], "True"),
    ("timing test passes, half cost", perm_passes("half"), "37"),
    ("timing test passes, default cost", perm_passes("default"), "60"),
    ("timing test passes, double cost", perm_passes("double"), "107"),
    ("grid stock", GRID["symbol"], "RELIANCE.NS"),
    ("grid combinations", GRID["combinations"], "834"),
    ("grid hold, tuning years", GRID["bh_is_sharpe"], "0.553"),
    ("grid hold, unseen years", GRID["bh_oos_sharpe"], "0.544"),
    ("grid cells ahead of hold, tuning years", sum(p["is_sharpe"] > GRID["bh_is_sharpe"] for p in PTS), "0"),
    ("grid cells ahead of hold, unseen years", sum(p["oos_sharpe"] > GRID["bh_oos_sharpe"] for p in PTS), "0"),
    ("pick", f"{PICK['strategy']} {PICK['params']['bb_window']} {PICK['params']['bb_std']}", "bollinger 40 3.0"),
    ("pick in-sample", PICK["is_sharpe"], "0.342"),
    ("pick out-of-sample", PICK["oos_sharpe"], "-0.463"),
    ("pick rank out of sample", PICK["oos_rank_of_834"], "623"),
    ("median grid out-of-sample", GRID["median_oos_sharpe"], "-0.294"),
    ("in/out correlation", statistics.correlation([p["is_sharpe"] for p in PTS], [p["oos_sharpe"] for p in PTS]), "0.32"),
    ("pick Deflated Sharpe", PICK["deflated_sharpe"], "0.16"),
    ("Bollinger PBO", GRID["per_strategy"]["bollinger"]["pbo"], "0.34"),
    ("whole-grid cells beating hold", sum(s["grid_cells_beating_bh"] for s in GRID["per_strategy"].values()), "0"),
    ("pick timing p", PICK["permutation_p"], "0.046"),
    ("small grid pick", GRID["small_grid_same_strategy"]["best_params"], "{'bb_window': 50, 'bb_std': 2.5}"),
    ("small grid in-sample", GRID["small_grid_same_strategy"]["is_sharpe"], "-0.086"),
    *[
        (f"re-run {u} {c} {k}", PERM["universes"][u][c]["passing_timing_test"][k], q)
        for u, k, vals in [
            ("start_2011", "defaults_day_shuffle", ("37", "60", "107")),
            ("start_2011", "pick_day_shuffle", ("58", "92", "109")),
            ("start_2011", "pick_run_shuffle", ("26", "25", "21")),
            ("today", "pick_run_shuffle", ("19", "17", "11")),
        ]
        for c, q in zip(("half", "default", "double"), vals)
    ],
    ("re-run survivors, default", sorted(PERM["universes"]["start_2011"]["default"]["survivors_after"]) == SURVIVORS, "True"),
    ("re-run survive, double", PERM["universes"]["start_2011"]["double"]["survives_after"], "3"),
]


def matches(value, quoted):
    if isinstance(value, float):
        places = len(quoted.split(".")[1]) if "." in quoted else 0
        return f"{value:.{places}f}" == quoted.replace("−", "-")
    return str(value) == quoted


def chart():
    """Every combination's tuning-years Sharpe (across) against its unseen-years one (up)."""
    w, h, pad = 640, 440, 52
    xs = [p["is_sharpe"] for p in PTS] + [GRID["bh_is_sharpe"]]
    ys = [p["oos_sharpe"] for p in PTS] + [GRID["bh_oos_sharpe"]]
    x0, x1, y0, y1 = min(xs) - 0.05, max(xs) + 0.05, min(ys) - 0.05, max(ys) + 0.05
    sx = lambda v: pad + (v - x0) / (x1 - x0) * (w - 2 * pad)  # noqa: E731
    sy = lambda v: h - pad - (v - y0) / (y1 - y0) * (h - 2 * pad)  # noqa: E731
    colour = {"momentum": "#2a6fdb", "macd": "#d9822b", "bollinger": "#2e9e6b"}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="system-ui, sans-serif" font-size="12">',
        f'<rect width="{w}" height="{h}" fill="#fff"/>',
        f'<line x1="{sx(GRID["bh_is_sharpe"]):.1f}" y1="{pad}" x2="{sx(GRID["bh_is_sharpe"]):.1f}" y2="{h - pad}" stroke="#888" stroke-dasharray="4 4"/>',
        f'<line x1="{pad}" y1="{sy(GRID["bh_oos_sharpe"]):.1f}" x2="{w - pad}" y2="{sy(GRID["bh_oos_sharpe"]):.1f}" stroke="#888" stroke-dasharray="4 4"/>',
        f'<text x="{sx(GRID["bh_is_sharpe"]) - 6:.1f}" y="{sy(GRID["bh_oos_sharpe"]) + 16:.1f}" text-anchor="end" fill="#555">holding the stock (dashed lines)</text>',
        f'<rect x="{pad}" y="{pad}" width="{w - 2 * pad}" height="{h - 2 * pad}" fill="none" stroke="#ccc"/>',
    ]
    for p in PTS:
        out.append(f'<circle cx="{sx(p["is_sharpe"]):.1f}" cy="{sy(p["oos_sharpe"]):.1f}" r="2.6" fill="{colour[p["strategy"]]}" fill-opacity="0.55"/>')
    out.append(f'<circle cx="{sx(PICK["is_sharpe"]):.1f}" cy="{sy(PICK["oos_sharpe"]):.1f}" r="7" fill="none" stroke="#c0392b" stroke-width="2"/>')
    out.append(f'<text x="{sx(PICK["is_sharpe"]) + 4:.1f}" y="{sy(PICK["oos_sharpe"]) + 24:.1f}" text-anchor="end" fill="#c0392b" stroke="#fff" stroke-width="3" paint-order="stroke">best on the tuning years</text>')
    for i, (name, c) in enumerate(colour.items()):
        out.append(f'<circle cx="{pad + 12 + i * 100}" cy="{pad - 22}" r="4" fill="{c}"/><text x="{pad + 20 + i * 100}" y="{pad - 18}">{name}</text>')
    out.append(f'<text x="{w / 2}" y="{h - 14}" text-anchor="middle">Sharpe on the tuning years, 2011–2021</text>')
    out.append(f'<text transform="translate(16 {h / 2}) rotate(-90)" text-anchor="middle">Sharpe on the unseen years, 2021–2025</text>')
    for v in (-1.0, -0.5, 0.0, 0.5):
        if x0 <= v <= x1:
            out.append(f'<text x="{sx(v):.1f}" y="{h - pad + 16}" text-anchor="middle" fill="#555">{v:g}</text>')
        if y0 <= v <= y1:
            out.append(f'<text x="{pad - 6}" y="{sy(v) + 4:.1f}" text-anchor="end" fill="#555">{v:g}</text>')
    out.append("</svg>")
    (RESEARCH / "nifty-grid.svg").write_text("\n".join(out) + "\n")


def main():
    wrong = 0
    for label, value, quoted in EXPECTED:
        ok = matches(value, quoted)
        wrong += not ok
        print(f"{'ok ' if ok else 'BAD'}  {label:42} quoted {quoted:>10}  saved {value}")
    chart()
    print(f"\n{len(EXPECTED) - wrong} of {len(EXPECTED)} figures match")
    sys.exit(1 if wrong else 0)


if __name__ == "__main__":
    main()
