# Reading list

Ordered. Tier 1 is what the code already implements — read those first because
you can check every claim against `backend/`. Tier 2 is what the open questions
need. Tier 3 is context.

## Tier 1 — implemented in Finertia

| # | Paper / book | Implements | Code |
|---|---|---|---|
| 1 | Jegadeesh & Titman (1993), *Returns to Buying Winners and Selling Losers*, J. Finance | why momentum is a thing at all | `signals.py` |
| 2 | Lo (2002), *The Statistics of Sharpe Ratios*, FAJ | Sharpe standard error under iid; the closed form DSR must reduce to | `deflated.py` (test pins to 1e-12) |
| 3 | Bailey & López de Prado (2012), *The Sharpe Ratio Efficient Frontier*, J. Risk | Probabilistic Sharpe Ratio (skew/kurtosis-adjusted) | `deflated.py` → `probabilistic_sharpe_ratio` |
| 4 | Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, J. Portfolio Mgmt | expected max of N trials; DSR | `deflated.py` → `expected_max_sharpe`, `deflated_sharpe_ratio` |
| 5 | Bailey, Borwein, López de Prado & Zhu (2014), *The Probability of Backtest Overfitting*, J. Computational Finance | CSCV, PBO, degradation, P(loss) | `pbo.py` |
| 6 | López de Prado (2018), *Advances in Financial Machine Learning*, Wiley — ch. 7 (purging/embargo), 11 (backtest dangers), 12 (CSCV), 14 (backtest statistics) | purge/embargo, the whole framing | `purge.py`, `validation.py` |
| 7 | Politis & Romano (1994), *The Stationary Bootstrap*, JASA | resampling under serial dependence | `bootstrap.py` → `stationary_bootstrap_indices` |
| 8 | Politis & White (2004), *Automatic Block-Length Selection for the Dependent Bootstrap*, Econometric Reviews; + Patton, Politis & White (2009) correction | automatic block length | `bootstrap.py` → `politis_white_block_length` |
| 9 | Künsch (1989), *The Jackknife and the Bootstrap for General Stationary Observations*, Annals of Stats | why delete-one-observation jackknife is invalid; block jackknife | `bootstrap.py` → `_block_jackknife` |
| 10 | Efron (1987), *Better Bootstrap Confidence Intervals*, JASA | BCa intervals | `bootstrap.py` → `_bca_interval` |
| 11 | Acklam, *An algorithm for computing the inverse normal cumulative distribution function* (2003, web note) | Φ⁻¹ without scipy | `deflated.py` → `_norm_ppf` |

## Tier 2 — needed for the open questions

| # | Paper | For |
|---|---|---|
| 12 | Harvey, Liu & Zhu (2016), *…and the Cross-Section of Expected Returns*, RFS | multiple-testing thresholds for the whole field; t-stat > 3 argument |
| 13 | Harvey & Liu (2015), *Backtesting*, J. Portfolio Mgmt | haircut Sharpe ratios — alternative to DSR |
| 14 | López de Prado & Lewis (2019), *Detection of False Investment Strategies Using Unsupervised Learning*, Quant. Finance | **effective number of trials via clustering** — the open r5 item |
| 15 | Nyholt (2004) / Li & Ji (2005), effective number of independent tests from a correlation matrix's eigenvalues | cheaper effective-N estimate to compare against 14 |
| 16 | White (2000), *A Reality Check for Data Snooping*, Econometrica; Hansen (2005), *A Test for Superior Predictive Ability*, JBES | bootstrap test across the whole grid at once — replaces permutation §2 with something that handles N candidates |
| 17 | Romano & Wolf (2005), *Stepwise Multiple Testing as Formalized Data Snooping*, Econometrica | FWER-controlled stepdown — which grid cells survive |
| 18 | Ledoit & Wolf (2008), *Robust Performance Hypothesis Testing with the Sharpe Ratio*, J. Empirical Finance | comparing two Sharpes (strategy vs benchmark) with a studentised bootstrap |
| 19 | Bailey & López de Prado (2014), *Stop-Outs Under Serial Correlation*, plus AFML ch. 15 | drawdown distribution — the metric whose CI coverage fails |
| 20 | Politis (2003), *The Impact of Bootstrap Methods on Time Series Analysis*, Statistical Science | survey; where the regime problem for vol CIs comes from |

## Tier 3 — context and the "why"

- Bailey, Borwein, López de Prado & Zhu (2014), *Pseudo-Mathematics and Financial Charlatanism*, Notices of the AMS — short, angry, the manifesto.
- Arnott, Harvey & Markowitz (2019), *A Backtesting Protocol in the Era of Machine Learning*, J. Financial Data Science — checklist form.
- Ilmanen (2011), *Expected Returns* — the factor landscape momentum sits in.
- Chan (2008), *Quantitative Trading* — practitioner baseline; good for what *not* to trust.
- Pardo (2008), *The Evaluation and Optimization of Trading Strategies* — the original walk-forward book.

## How to read a paper for this project

1. Find the formula the code claims to implement. Write it by hand.
2. Find the number the paper reports (3.26 at N=1000; Lo's SE). Reproduce it in
   a scratch script *without* looking at `backend/`.
3. Then open the module and diff your version against it.
4. If they disagree, one of you is wrong. Find out which, and add a test.
