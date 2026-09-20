# Finertia — Learning

Everything you need to understand this project, from "what is a stock price" up to
the papers the validation engine implements. Each topic points at the exact file in
the codebase that uses it, so you can read theory and code side by side.

## How to use this folder

Work top to bottom. Each file assumes the one before it. Tick a box when you can
explain the concept out loud without looking — not when you have read about it.

| File | What it covers | Level | Time |
|---|---|---|---|
| [01-foundations.md](01-foundations.md) | Prices, returns, signals, equity curves, drawdown, Sharpe; pandas/numpy needed to compute them | Basics | ~35h |
| [02-stack.md](02-stack.md) | FastAPI, Firebase, React, Recharts, SaaS patterns, the deployed architecture | Intermediate | ~60h |
| [03-validation-methods.md](03-validation-methods.md) | What Finertia does that most backtesters do not: walk-forward, permutation, DSR, PBO, purging, bootstrap CIs, rolling folds, regimes, whole-grid inference — with formulas, traps, and where each lives | Advanced | ~40h |
| [research/reading-list.md](research/reading-list.md) | Papers and books, in the order to read them | Research | ongoing |
| [research/open-questions.md](research/open-questions.md) | What is not solved yet — the research frontier of this project | Research | — |

Rough total: 8–12 weeks part-time for 01–03. The research folder has no end.

## The one idea to carry through all of it

> Any strategy can be tuned until its chart points up.

Every file here is in service of that sentence. The foundations tell you how a
backtest is computed; the validation methods tell you why a computed number is
usually a lie, and how to measure how much of a lie.

## Where the code is

```
backend/
  data.py        prices in (yfinance, through the cache tiers)
  price_store.py Firestore / in-memory price cache, whole-ticker batches
  signals.py     momentum / MACD / Bollinger → position series
  strategies.py  registry: build fn, warm-up, walk-forward grid per strategy
  engine.py      positions × returns → equity curve, drawdown, costs
  metrics.py     12 headline metrics
  risk.py        stop-loss / take-profit / vol targeting overlays
  portfolio.py   2–10 tickers, equal or inverse-vol weights
  analytics.py   monthly / annual / rolling-Sharpe views
  validation.py  walk-forward + signal permutation
  deflated.py    Deflated Sharpe Ratio (Bailey & López de Prado 2014)
  pbo.py         Probability of Backtest Overfitting via CSCV
  purge.py       purge + embargo at the walk-forward split
  bootstrap.py   stationary block bootstrap, BCa confidence intervals
  trials.py      effective number of trials (eigenvalue + clustering)
  rolling.py     anchored rolling walk-forward, one verdict per fold
  regimes.py     market volatility terciles, Sharpe per regime
  main.py        16 FastAPI routes; auth, quota, rate limit, error mapping
frontend/src/    React 18 + Vite + Tailwind + Recharts
```

Related: [../planning/](../planning/) for status and what is next;
[../planning/PROGRESS.md](../planning/PROGRESS.md) for how the project got here.
