"""The share link: its preview page and card (share.py, /api/share*).

Signed out and off unless SHARE_CARDS=1, so these check the switch, that the
preview quotes the same figures as POST /api/backtest, that the redirect and
the card URL carry only rebuilt parameters, and that a cache miss is metered.
"""

import io

import pytest
from PIL import Image

import main
import share
from test_routes import AUTH, _prices, api  # noqa: F401  (api is a fixture)

LINK = "ticker=aapl&start=2020-01-01&end=2022-06-30&strategy=macd&macd_fast=10"


@pytest.fixture
def on(api, monkeypatch):  # noqa: F811
    client, state = api
    monkeypatch.setenv("SHARE_CARDS", "1")
    share.cache.clear()
    main.share_limiter._hits.clear()
    calls = []

    def fetch(t, s, e):
        calls.append(t)
        return _prices()

    monkeypatch.setattr(main, "fetch_ohlcv", fetch)
    return client, state, calls


def test_off_unless_switched_on(api, monkeypatch):  # noqa: F811
    client, _ = api
    monkeypatch.delenv("SHARE_CARDS", raising=False)
    assert client.get(f"/api/share?{LINK}").status_code == 404
    assert client.get(f"/api/share/card.png?{LINK}").status_code == 404


def test_preview_quotes_the_backtest_and_points_at_the_card(on):
    client, _, _ = on
    r = client.get(f"/api/share?{LINK}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "public" in r.headers["cache-control"]
    page = r.text

    run = client.post("/api/backtest", json={
        "ticker": "AAPL", "start": "2020-01-01", "end": "2022-06-30", "strategy": "macd", "macd_fast": 10,
    }, headers=AUTH).json()["metrics"]
    assert f"Returned {run['total_return'] * 100:+,.0f}%" in page
    assert f"Sharpe {run['sharpe_ratio']:.2f}" in page

    assert '<meta property="og:title" content="MACD on AAPL, 2020 to 2022">' in page
    # Rebuilt from the validated request: upper-cased, defaults filled in, and
    # the ampersands escaped inside the attribute.
    query = "ticker=AAPL&amp;start=2020-01-01&amp;end=2022-06-30&amp;strategy=macd&amp;transaction_cost=0.001&amp;macd_fast=10&amp;macd_slow=26&amp;macd_signal=9&amp;sizing=fixed"
    assert f'property="og:image" content="http://localhost:5174/api/share/card.png?{query}"' in page
    assert f'url=/dashboard?{query}"' in page
    assert 'name="robots" content="noindex"' in page


def test_card_is_a_1200_by_630_png(on):
    client, _, _ = on
    r = client.get(f"/api/share/card.png?{LINK}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (1200, 630)


def test_page_and_card_compute_once(on):
    client, _, calls = on
    client.get(f"/api/share?{LINK}")
    client.get(f"/api/share/card.png?{LINK}")
    client.get(f"/api/share?{LINK}&utm_source=x")  # unknown keys do not split the cache
    assert calls == ["AAPL"]


@pytest.mark.parametrize("query", [
    "ticker=&start=2020-01-01&end=2022-06-30",  # invalid
    "mode=portfolio&tickers=AAPL,MSFT&start=2020-01-01&end=2022-06-30",  # no card for a basket
])
def test_a_link_without_a_card_still_opens_the_workspace(on, query):
    client, _, _ = on
    r = client.get(f"/api/share?{query}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith("/dashboard?")
    assert client.get(f"/api/share/card.png?{query}").status_code == 404


def test_a_bad_ticker_redirects_the_page_and_fails_the_card(on, monkeypatch):
    client, _, _ = on

    def unknown(t, s, e):
        raise ValueError("No data for ZZZZ")

    monkeypatch.setattr(main, "fetch_ohlcv", unknown)
    r = client.get("/api/share?ticker=ZZZZ&start=2020-01-01&end=2022-06-30", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard?ticker=ZZZZ&start=2020-01-01&end=2022-06-30"
    assert client.get("/api/share/card.png?ticker=ZZZZ&start=2020-01-01&end=2022-06-30").status_code == 400


def test_cache_misses_are_metered_per_address(on):
    client, _, _ = on
    statuses = [
        client.get(f"/api/share/card.png?{LINK}&macd_signal={n}").status_code
        for n in range(2, 2 + main.share_limiter.limit + 1)
    ]
    assert statuses[:-1] == [200] * main.share_limiter.limit
    assert statuses[-1] == 429
    # A link already computed is still served.
    assert client.get(f"/api/share/card.png?{LINK}&macd_signal=2").status_code == 200


def test_title_shrinks_to_fit_a_long_symbol():
    fig = {
        "ticker": "BAJAJ-AUTO.NS", "label": "Bollinger bands", "first": "2019-01-01", "last": "2024-12-31",
        "cost_bp": 10.0, "run": {"total_return": 0.1, "sharpe_ratio": 0.5, "max_drawdown": -0.2},
        "hold": {"total_return": 0.3, "sharpe_ratio": 0.7, "max_drawdown": -0.3},
        "equity": [1.0, 1.1], "held": [1.0, 1.3],
    }
    assert Image.open(io.BytesIO(share.card(fig))).size == (1200, 630)
