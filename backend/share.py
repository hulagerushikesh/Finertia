"""Share cards: the link preview for a shared backtest set-up.

A set-up link is /dashboard?<params>, which every crawler sees as the same
signed-in shell. A share link is /api/share?<params> instead: a tiny HTML page
whose Open Graph tags name this run's figures and point at a 1200x630 card
drawn here, and which sends a person straight on to /dashboard?<params>.

Served by the API through the site's /api rewrite, so the preview and the
card come from finertia.hulage.in with no function on Vercel. No account, no
Firestore read or write: the figures come from the same `_simulate` as
POST /api/backtest, so a card cannot disagree with the run it links to.

Off unless SHARE_CARDS=1 (a deployment setting, like the free validations),
so the tester round sees nothing new.
"""

import html
import io
import os
import threading
import time
from collections import OrderedDict
from urllib.parse import urlencode

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from metrics import compute_metrics

STRATEGY_LABEL = {"momentum": "Momentum", "macd": "MACD", "bollinger": "Bollinger bands"}

WIDTH, HEIGHT = 1200, 630
# frontend/src/index.css, light theme: background, foreground, faint, pencil.
PAPER = "#F0F8FF"
INK = "#374151"
FAINT = "#636A76"
PENCIL = "#047857"
RULE = "#D5DEE8"

# Prices for a range that has ended barely move, so an hour in this process
# and a day at the CDN is plenty; a cap keeps a crawl of odd links bounded.
_CACHE_SIZE = 128
_CACHE_TTL = 3600.0


def enabled() -> bool:
    return os.environ.get("SHARE_CARDS") == "1"


def canonical_query(req) -> str:
    """The request as frontend/src/utils/permalink.js writes it.

    Rebuilt from the validated request rather than echoed from the link, so
    the redirect and the card URL only ever carry known keys and clean values.
    """
    q = {
        "ticker": req.ticker,
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "transaction_cost": req.transaction_cost,
        **req.strategy_params(),
    }
    for key in ("stop_loss", "take_profit"):
        if getattr(req, key) is not None:
            q[key] = getattr(req, key)
    q["sizing"] = req.sizing
    if req.sizing == "vol_target":
        q.update(target_vol=req.target_vol, vol_window=req.vol_window, max_leverage=req.max_leverage)
    return urlencode({k: str(v) for k, v in q.items()})


def figures(req, close: pd.Series, engine_out: pd.DataFrame, benchmark: pd.Series) -> dict:
    """What the card and the preview text quote: the run against holding."""
    net = engine_out["net_return"].fillna(0)
    equity = engine_out["equity_curve"].fillna(1)
    drawdown = engine_out["drawdown"].fillna(0)
    run = compute_metrics(net, equity, drawdown, engine_out["position"])

    # Holding it, through the same metrics code (build_stock_pages.py does the same).
    held = benchmark.fillna(1)
    hold = compute_metrics(
        held.pct_change().fillna(0), held, held / held.cummax() - 1, pd.Series(1.0, index=held.index)
    )
    # A few hundred points draw the same line as a few thousand.
    step = max(1, len(equity) // 300)
    return {
        "ticker": req.ticker,
        "strategy": req.strategy,
        "label": STRATEGY_LABEL.get(req.strategy, req.strategy),
        "first": close.index[0].strftime("%Y-%m-%d"),
        "last": close.index[-1].strftime("%Y-%m-%d"),
        "cost_bp": round(req.transaction_cost * 10_000, 1),
        "run": {k: run[k] for k in ("total_return", "sharpe_ratio", "max_drawdown")},
        "hold": {k: hold[k] for k in ("total_return", "sharpe_ratio", "max_drawdown")},
        "equity": equity.iloc[::step].tolist() + [float(equity.iloc[-1])],
        "held": held.iloc[::step].tolist() + [float(held.iloc[-1])],
    }


class _Cache:
    """A small LRU with a TTL, safe across the threadpool's workers."""

    def __init__(self, size: int, ttl: float):
        self.size, self.ttl = size, ttl
        self._items: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            hit = self._items.get(key)
            if hit is None or time.time() - hit[0] > self.ttl:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return hit[1]

    def put(self, key, value):
        with self._lock:
            self._items[key] = (time.time(), value)
            self._items.move_to_end(key)
            while len(self._items) > self.size:
                self._items.popitem(last=False)

    def clear(self):
        with self._lock:
            self._items.clear()


cache = _Cache(_CACHE_SIZE, _CACHE_TTL)


def _pct(x: float) -> str:
    return f"{x * 100:+,.0f}%"


def _num(x: float) -> str:
    return f"{x:.2f}"


def summary(fig: dict) -> tuple[str, str]:
    """The preview's title and description."""
    title = f"{fig['label']} on {fig['ticker']}, {fig['first'][:4]} to {fig['last'][:4]}"
    run, hold = fig["run"], fig["hold"]
    desc = (
        f"Returned {_pct(run['total_return'])} against {_pct(hold['total_return'])} for holding it, "
        f"Sharpe {_num(run['sharpe_ratio'])} against {_num(hold['sharpe_ratio'])}, "
        f"{fig['cost_bp']:g} bp costs. A hypothetical backtest on past data, not advice."
    )
    return title, desc


def page(fig: dict, query: str, site: str) -> str:
    """The preview page: Open Graph tags for crawlers, a redirect for people."""
    title, desc = summary(fig)
    dashboard = f"/dashboard?{query}"
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · Finertia</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Finertia">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(f'{site}/api/share?{query}')}">
<meta property="og:image" content="{e(f'{site}/api/share/card.png?{query}')}">
<meta property="og:image:width" content="{WIDTH}">
<meta property="og:image:height" content="{HEIGHT}">
<meta property="og:image:alt" content="{e(title)}: the strategy's growth against holding the stock">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0; url={e(dashboard)}">
</head>
<body>
<p><a href="{e(dashboard)}">Open this set-up in Finertia</a></p>
</body>
</html>
"""


def _font(size: int):
    # Pillow's bundled FreeType font, so the slim image needs no font package.
    return ImageFont.load_default(size=size)


def _line(draw, values, box, lo, hi, colour, width):
    x0, y0, x1, y1 = box
    n = len(values) - 1 or 1
    span = (hi - lo) or 1.0
    pts = [(x0 + (x1 - x0) * i / n, y1 - (y1 - y0) * (v - lo) / span) for i, v in enumerate(values)]
    draw.line(pts, fill=colour, width=width, joint="curve")


def card(fig: dict) -> bytes:
    """The 1200x630 PNG: title, both growth lines, three figures against holding."""
    img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    d = ImageDraw.Draw(img)
    d.text((60, 44), "Finertia", font=_font(30), fill=PENCIL)
    d.text((WIDTH - 60, 44), "Backtest", font=_font(26), fill=FAINT, anchor="ra")
    title = f"{fig['label']} on {fig['ticker']}"
    size = 60  # down to fit a long symbol: "Bollinger bands on BAJAJ-AUTO.NS"
    while size > 36 and d.textlength(title, font=_font(size)) > WIDTH - 120:
        size -= 4
    d.text((60, 100 + (60 - size) // 2), title, font=_font(size), fill=INK)
    d.text(
        (60, 178),
        f"{fig['first']} to {fig['last']}  ·  {fig['cost_bp']:g} bp costs",
        font=_font(28),
        fill=FAINT,
    )

    # Growth of 1, strategy against holding, on one shared scale.
    box = (60, 250, 700, 520)
    d.rectangle(box, outline=RULE, width=2)
    inner = (box[0] + 12, box[1] + 12, box[2] - 12, box[3] - 12)
    lo = min(min(fig["equity"]), min(fig["held"]))
    hi = max(max(fig["equity"]), max(fig["held"]))
    _line(d, fig["held"], inner, lo, hi, FAINT, 3)
    _line(d, fig["equity"], inner, lo, hi, PENCIL, 5)
    d.line((60, 548, 90, 548), fill=PENCIL, width=5)
    d.text((100, 548), fig["label"], font=_font(22), fill=INK, anchor="lm")
    d.line((330, 548, 360, 548), fill=FAINT, width=3)
    d.text((370, 548), "Holding it", font=_font(22), fill=INK, anchor="lm")

    rows = [
        ("Return", _pct(fig["run"]["total_return"]), _pct(fig["hold"]["total_return"])),
        ("Sharpe", _num(fig["run"]["sharpe_ratio"]), _num(fig["hold"]["sharpe_ratio"])),
        ("Max drawdown", _pct(fig["run"]["max_drawdown"]), _pct(fig["hold"]["max_drawdown"])),
    ]
    # Label above, then the rule's figure and holding's beside it, so a long
    # figure (+17,815%) pushes nothing into anything.
    y = 250
    for name, run, hold in rows:
        d.text((760, y), name, font=_font(22), fill=FAINT)
        d.text((760, y + 28), run, font=_font(44), fill=INK)
        d.text((WIDTH - 60, y + 72), f"holding {hold}", font=_font(28), fill=FAINT, anchor="rs")
        y += 95

    d.text(
        (60, HEIGHT - 32),
        "Hypothetical result on past data. Not advice.  finertia.hulage.in",
        font=_font(20),
        fill=FAINT,
        anchor="ls",
    )
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
