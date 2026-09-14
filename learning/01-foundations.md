# 01 — Foundations

Quant basics and the Python needed to compute them. Nothing here requires prior
finance knowledge. Every item names the file where Finertia does the thing.

Legend: **F** foundational · **I** intermediate · time is a rough study estimate.

---

## A. Quantitative finance fundamentals (~25h)

- [ ] **OHLCV market data** — F · 2h
  Every daily bar has Open, High, Low, Close, Volume. Finertia uses only Close.
  Code: `backend/data.py` → `fetch_ohlcv()`.
  Read: Investopedia "OHLC chart"; pandas indexing guide.

- [ ] **Daily returns — simple vs log** — F · 3h
  `r_t = close_t / close_{t-1} − 1` (`.pct_change()`). Finertia uses *simple*
  returns because a position × return is additive within a day. Log returns
  compound cleanly across time but make position maths awkward.
  Code: `backend/engine.py` → `compute_returns()`.
  Read: QuantDare "Log returns vs simple returns".

- [ ] **Momentum / rate of change** — F · 4h
  `ROC = close_t / close_{t−L} − 1`. Long if ROC > threshold and price above MA;
  short if ROC < −threshold; else flat.
  Code: `backend/signals.py` → `compute_momentum()`, `generate_signals()`.
  Read: Jegadeesh & Titman (1993) — the paper that made momentum a "factor".

- [ ] **Moving averages as a trend filter** — F · 2h
  SMA = mean of last N closes. Used as a *gate*, not a signal: only go long if
  `close > SMA`. Code: `backend/signals.py` → `compute_moving_average()`.

- [ ] **MACD** — I · 2h
  EMA(fast) − EMA(slow), signal line = EMA of that. Cross above → long.
  Code: `backend/signals.py`; params in `strategies.py`.

- [ ] **Bollinger bands / mean reversion** — I · 2h
  Band = SMA ± k·σ. Below lower band → long (expect reversion). The *opposite*
  bet to momentum — which is why the walk-forward result comparing them matters.
  Code: `backend/signals.py`.

- [ ] **Lookahead bias — the shift-by-one rule** — I · 2h
  A signal computed from today's close cannot be traded at today's close.
  `signal.shift(1)` applies today's decision to tomorrow's return. Forgetting this
  is the single most common way a backtest lies.
  Code: end of `generate_signals()`: `raw_signal.shift(1).fillna(0)`.

- [ ] **Equity curve** — F · 3h
  `(1 + r).cumprod()` starting at 1.0. Benchmark (buy-and-hold) is the same
  formula on raw returns. Code: `engine.py` → `apply_positions()`, `compute_benchmark()`.

- [ ] **Drawdown and max drawdown** — I · 2h
  `dd = (equity − equity.cummax()) / equity.cummax()`, always ≤ 0. Max DD = `dd.min()`.
  Code: `engine.py` (series), `metrics.py` (scalar).

- [ ] **Sharpe and Calmar** — I · 3h
  Sharpe = annualised return / annualised vol, annualised with √252.
  Calmar = annualised return / |max DD|.
  Code: `metrics.py` → `compute_metrics()`.
  Gotcha you will meet in file 03: Sharpe *must be de-annualised* before any
  significance test that counts daily bars.

- [ ] **Win rate and profit factor** — I · 2h
  Both computed on *non-zero* return days only, otherwise flat days dilute them.
  Code: `metrics.py`.

- [ ] **Transaction costs charged on turnover** — I · 2h
  Cost = `|Δposition| × cost_rate`, not a flat fee per change. A −1 → +1 flip
  correctly pays 2×; fractional vol-target sizing is not billed a full round trip
  every bar. Code: `engine.py` → `apply_positions()`.

- [ ] **Risk overlays: stops and vol targeting** — I · 3h
  Stop-loss / take-profit are path-dependent (a loop, evaluated at the close; a
  stopped trade does not re-enter until the signal changes). Vol targeting sizes
  position = `target_vol / trailing_realised_vol`, window shifted 1 bar, capped by
  `max_leverage`. Code: `backend/risk.py`; applied stops → sizing in `main.py`.

- [ ] **Multi-asset portfolios** — I · 3h
  2–10 legs, equal or inverse-vol weights, `max_weight` cap that pushes freed
  weight outward and repeats (clip-then-renormalise is a trap). Alignment is an
  *inner join*: forward-filling invents flat days and flatters every risk metric.
  Diversification ratio = weighted avg vol / portfolio vol.
  Code: `backend/portfolio.py`.

- [ ] **Survivorship bias** — I · 1h
  yfinance only returns tickers that still exist. Any long backtest on a
  surviving name is flattered. Not fixable on free data; Finertia discloses it
  under the results. Code: `DashboardPage.jsx` (disclosure copy).

## B. Python for financial data (~15h)

- [ ] **pandas Series / DataFrame** — F · 5h
  A price series is a Series indexed by date. Master `.pct_change()`, `.rolling()`,
  `.shift()`, `.cumprod()`, `.cummax()` — those five do ~80% of the engine.
  Read: "10 minutes to pandas".

- [ ] **Vectorised numpy — no loops** — F · 3h
  `np.sqrt(252)`, `np.std`, `np.mean` on whole arrays. If you are looping over rows
  to do arithmetic, there is a pandas/numpy call for it. The one legitimate loop
  in the codebase is the stop-loss path in `risk.py` (it is path-dependent).

- [ ] **yfinance** — F · 2h
  `yf.download(ticker, start, end)`; ≥0.2 returns MultiIndex columns which
  `data.py` flattens. Rate-limited and flaky — see planning/BACKLOG for the
  persistent-cache item.

- [ ] **In-memory caching** — I · 1h
  Module-level dict keyed `(ticker, start, end)`. Lives per process; Cloud Run at
  `min-instances 0` means it is cold on every scale-from-zero.
  Code: `data.py` → `_cache`.

- [ ] **Pydantic models** — F · 3h
  Typed request bodies → free 422 validation. `backend/schemas.py` is deliberately
  Firebase-free so it is testable without credentials. `RISK_KEYS` there is the
  single source of truth for splitting a stored run's param map.

- [ ] **python-dotenv / env vars** — F · 30m
  `.env` for local, real env on Cloud Run. Never hardcode credentials.

- [ ] **pytest for pure functions** — F · 3h
  `cd backend && pytest tests/ -q`. 535 tests, no credentials, no network.
  Learn *mutation checking*: delete the admin check and exactly the 2 admin tests
  should fail. If nothing fails, the test is decorative.

---

Next: [02-stack.md](02-stack.md)
