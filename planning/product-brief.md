# Product brief

_Positioning from the 7 Aug brief, updated 14 Sep for what is now built._

## One sentence

Finertia answers "if I had traded this strategy on this stock over this period,
what would have happened — and how much of that answer is luck?" in under ten
seconds, with every calculation readable as source.

## The problem

Someone has a trading idea. Every path to evidence is bad in its own way:

| Today | Why it fails |
|---|---|
| Excel | Hours per test; silently wrong on drawdown; no costs |
| Jupyter | Needs Python; nothing persists; lookahead bias by accident |
| TradingView | Closed source — cannot audit the arithmetic |
| QuantConnect / Backtrader | Days of onboarding before the first result |
| Give up and trade it | The most expensive option |

And every one of them, including the good ones, shows you a winner and lets
you believe it.

## What Finertia does instead

- Result in seconds, no install, no code
- Lookahead bias closed structurally (signals shift one bar, always)
- Costs on turnover by default; benchmarked against buy-and-hold on every run
- **Then it argues back**: walk-forward, signal permutation, deflated Sharpe,
  PBO, purged splits, and a confidence interval on every number it prints
- The maths is readable source, not a vendor claim

The demo leads with a strategy that *lost* to doing nothing, because that is
what the engine produced.

## Competitive position

| Tool | Setup | Auditable | Overfitting checks | Error bars | Price |
|---|---|---|---|---|---|
| Excel | hours | fragile | none | none | owned |
| Jupyter | Python | yes | DIY | DIY | free |
| TradingView | minutes | no | none | none | $15–60/mo |
| QuantConnect | days | partly | some | none | free–$60/mo |
| **Finertia** | open a URL | full source | WF + DSR + PBO + purge | on every metric | free (Pro built, unwired) |

## Who it is for

1. **Retail trader validating an idea** — "is this better than holding, and how bad does the worst stretch get?"
2. **Finance student** — change the lookback from 20 to 60 and *feel* the Sharpe move
3. **Quant interview candidate** — defend Sharpe, Calmar, DSR, lookahead out loud; the source is a worked reference
4. **Educator / content creator** — a chart and a link readers can poke at
5. **The author, as a portfolio artefact** — full-stack + quant statistics in one deployed URL

## Credibility gaps — then vs now

| Gap (Aug 7) | Now |
|---|---|
| No out-of-sample testing — highest impact | **Closed.** Walk-forward + purge/embargo + DSR + PBO |
| No statistical significance | **Closed.** Permutation test + bootstrap CIs on every metric |
| One strategy, one ticker | **Closed.** 3 strategies, risk overlays, 2–10-ticker portfolios |
| Survivorship bias in data | Disclosed in the UI; not fixable on free data |
| Admin stats scan collections | Still true; defer until it hurts |
| *(new)* Effective N overstated in DSR | Open — M9 phase 3 |
| *(new)* yfinance fragility | Open — M9 phase 2 |

## Direction

The Aug brief offered three paths (ship-then-deepen / quant-credibility-first /
education-first). Path A was taken and is complete: shipped 6 Sep, deepened
through 13 Sep. The remaining fork is **portfolio piece vs product** — decided
in M9 phase 4, recorded in DECISIONS.md.
