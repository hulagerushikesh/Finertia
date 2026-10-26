"""Draw the link-preview card for each /stocks/<slug> page.

A shared stock page used the site's one og.png, so every preview looked the
same. This draws a 1200x630 card per stock from stockResults.json, the same
file the page reads, in share.py's palette and font: holding it and the three
strategies at their defaults, with each one's walk-forward verdict.

    cd backend && .venv/bin/python scripts/build_stock_cards.py           # rewrite every card
    cd backend && .venv/bin/python scripts/build_stock_cards.py --check   # exit 1 if a card is missing or stale

Re-run after build_stock_pages.py. The PNGs are committed under
frontend/public/og/, so the build needs no Python; pageMeta.js points each
stock page's og:image at its card, and stockMeta.test.js checks each exists.
"""

import io
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from share import FAINT, HEIGHT, INK, PAPER, PENCIL, RULE, WIDTH, _font  # noqa: E402

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
RESULTS = FRONTEND / "src" / "lib" / "stockResults.json"
OUT = FRONTEND / "public" / "og"

STRATEGY_LABEL = {"momentum": "Momentum", "macd": "MACD", "bollinger": "Bollinger bands"}
# StockPage.jsx VERDICT, which follows backend/validation.py `_verdict`.
VERDICT = {
    "held_up": "held up",
    "weakened": "weakened",
    "overfit": "overfit",
    "failed": "failed",
    "inconclusive": "inconclusive",
}


def years(start: str, end: str) -> str:
    """stockMeta.js STOCK_PERIOD.years: the end date is exclusive.

    "to", not the page's en dash: Pillow's bundled font has no dash or minus
    sign, so the card spells both in ASCII.
    """
    last = int(end[:4]) - 1 if end.endswith("-01-01") else int(end[:4])
    return f"{start[:4]} to {last}"


def label(s: dict) -> str:
    """stockMeta.js `label`: Reliance Industries (RELIANCE), but not Nifty 50 (^NSEI)."""
    sym = s["symbol"]
    if sym.startswith("^"):
        return s["name"]
    ticker = sym.removesuffix(".NS")
    return s["name"] if ticker in s["name"] else f"{s['name']} ({ticker})"


def percent(x: float) -> str:
    """stockMeta.js `percent`: 5.641 -> 564%.

    Halves round up, as JavaScript's Math.round does (Python's round would
    print 74% where the page prints 75% for 0.745).
    """
    n = math.floor(x * 100 + 0.5)
    return f"{'-' if n < 0 else ''}{abs(n):,}%"


def signed(x: float) -> str:
    s = f"{abs(x):.2f}"
    return f"-{s}" if x < 0 and float(s) != 0 else s


def card(s: dict, period: str) -> bytes:
    img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    d = ImageDraw.Draw(img)
    d.text((60, 44), "Finertia", font=_font(30), fill=PENCIL)
    d.text((WIDTH - 60, 44), f"Backtest, {period}", font=_font(26), fill=FAINT, anchor="ra")

    title = label(s)
    size = 60  # down to fit a long name: "Hindustan Unilever (HINDUNILVR)"
    while size > 36 and d.textlength(title, font=_font(size)) > WIDTH - 120:
        size -= 4
    d.text((60, 100 + (60 - size) // 2), title, font=_font(size), fill=INK)
    d.text((60, 178), "Three strategies against holding it, at default settings", font=_font(28), fill=FAINT)

    # The name's left edge, then the right edges of return, Sharpe and verdict.
    cols = (60, 660, 860, WIDTH - 60)
    y = 248
    for x, head in zip(cols[1:], ("Return", "Sharpe", "On unseen years")):
        d.text((x, y), head, font=_font(22), fill=FAINT, anchor="ra")
    y += 40
    hold = s["buy_and_hold"]
    rows = [("Holding it", hold["total_return"], hold["sharpe_ratio"], "", INK)]
    for name, x in s["strategies"].items():
        verdict = x["walk_forward"]["verdict"]
        rows.append((
            STRATEGY_LABEL[name],
            x["defaults"]["total_return"],
            x["defaults"]["sharpe_ratio"],
            VERDICT[verdict],
            PENCIL if verdict == "held_up" else INK,
        ))
    for i, (name, ret, sharpe, verdict, colour) in enumerate(rows):
        d.line((60, y, WIDTH - 60, y), fill=RULE, width=2)
        mid = y + 36
        d.text((cols[0], mid), name, font=_font(34), fill=INK, anchor="lm")
        d.text((cols[1], mid), percent(ret), font=_font(34), fill=INK, anchor="rm")
        d.text((cols[2], mid), signed(sharpe), font=_font(34), fill=INK, anchor="rm")
        d.text((cols[3], mid), verdict, font=_font(30), fill=colour, anchor="rm")
        y += 72

    d.text(
        (60, HEIGHT - 32),
        "Hypothetical results on past data. Not advice.  finertia.hulage.in",
        font=_font(20),
        fill=FAINT,
        anchor="ls",
    )
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def main(check: bool) -> int:
    data = json.loads(RESULTS.read_text())
    period = years(data["start"], data["end"])
    OUT.mkdir(parents=True, exist_ok=True)
    stale = []
    for slug, s in data["stocks"].items():
        path = OUT / f"stock-{slug}.png"
        png = card(s, period)
        if check:
            if not path.exists() or path.read_bytes() != png:
                stale.append(path.name)
        else:
            path.write_bytes(png)
    if check:
        for name in stale:
            print(f"stale or missing: {name}")
        print(f"{len(data['stocks']) - len(stale)} of {len(data['stocks'])} cards current")
        return 1 if stale else 0
    print(f"wrote {len(data['stocks'])} cards to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
