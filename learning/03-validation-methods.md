# 03 — Validation methods: what makes a backtest number mean something

This is the research core of Finertia. Every method below is implemented from
the paper, in numpy, with no scipy and no library — and each one exists because
the previous one was found to be lying in a specific way. Read them in order;
that order *is* the story.

Prereqs: all of 01, plus Sharpe, drawdown, and `pytest` from 02.

---

## 0. The problem statement

`max(grid_results, key=sharpe)` — pick the best of N parameter combinations on
the data you have. That single line is:

1. **Overfitting** — the winner was chosen with knowledge of the whole period.
2. **Multiple testing** — the maximum of N draws is biased upward even when
   every draw has zero edge.
3. **Leakage** — a trade open across any split earns on both sides of it.
4. **A point estimate** — one number, no error bar, from one sample path.

Finertia attacks each in turn. Canonical demo: AAPL 2018–2024.

| Strategy | In-sample Sharpe | Out-of-sample | Verdict |
|---|---|---|---|
| Momentum | 0.889 | −0.242 | Failed |
| MACD | 0.554 | −0.281 | Failed |
| Bollinger | 0.553 | 1.367 | Held up |

The best in-sample result was the worst out-of-sample one.

---

## 1. Walk-forward validation  — `backend/validation.py` → `walk_forward()`

- [ ] **What**: split the period 70/30. Sweep the strategy's parameter grid on
  the first 70%, keep the best Sharpe, score *only* on the last 30%.
- [ ] **Verdict rule** (`_verdict`): OOS retains ≥ 70% of IS Sharpe → held up;
  otherwise failed/degraded.
- [ ] **Why it is not enough**: it tries one split. An edge confined to the
  first half passes; a regime break in the last 30% fails a real edge. And the
  IS number is still the max of N draws (→ §3).
- [ ] **Grid sizes**: momentum 16, MACD 4, Bollinger 12 combinations
  (`strategies.py` → `param_grid`).
- [ ] The candidate return matrix is built ONCE here and reused by §4 and §9.
  Re-running `build_positions` per split would be 70× the work.

Read: López de Prado, *Advances in Financial Machine Learning* (AFML), ch. 11–12.

## 2. Signal permutation test — `validation.py` → `permutation_test()`

- [ ] **What**: shuffle the position series 500 times, keeping the exposure
  distribution but destroying the *timing*. Report the percentile the real
  Sharpe lands in among the shuffles.
- [ ] **Interpretation**: p ≈ 0.5 → timing is indistinguishable from luck.
- [ ] **Limit**: defined on a single position series, which is why validation is
  hidden in portfolio mode (open question, see research/).

Read: White (2000) "A Reality Check for Data Snooping" for the general idea.

## 3. Deflated Sharpe Ratio — `backend/deflated.py`

Bailey & López de Prado (2014), "The Deflated Sharpe Ratio".

- [ ] **Expected max Sharpe of N zero-edge trials**
  `SR* = σ · [(1−γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))]`, γ = Euler–Mascheroni.
  Sanity: paper reports 3.26 at N = 1000 — a test pins it.
  Code: `expected_max_sharpe()`.
- [ ] **Probabilistic Sharpe Ratio** (Bailey & LdP 2012)
  `PSR = Φ[ (SR − SR*)·√(T−1) / √(1 − skew·SR + ((kurt−1)/4)·SR²) ]`
  Code: `probabilistic_sharpe_ratio()`.
- [ ] **DSR** = PSR evaluated against SR* instead of 0. Code: `deflated_sharpe_ratio()`.
- [ ] **Normal CDF via `math.erf`; inverse via Acklam's rational approximation
  (~1e-9)** — because scipy is deliberately absent. Code: `_norm_cdf`, `_norm_ppf`.

**Traps — each produces a plausible wrong number, not an error:**
- [ ] Kurtosis is **non-excess** (Normal = 3). Check: skew 0, kurt 3 must reduce
  the denominator to `√(1 + SR²/2)` — Lo (2002)'s standard error. Pinned to 1e-12.
- [ ] **De-annualise the Sharpe.** `metrics.py` returns an annualised Sharpe;
  T counts daily bars. Mixing them inflates by ~√252 and everything looks significant.
- [ ] `std == 0` does **not** catch a flat series (500 × 0.001 sums to std ≈ 4e-19
  → Sharpe 2e15). The guard is relative to the data's magnitude.
- [ ] A Sharpe means nothing for a mostly-flat series — one Bollinger setting
  fired on 3% of bars: skew 30, kurtosis 959. Refused as `unreliable`
  (< 30 active bars or kurt > 50).

**Result on a random walk by construction:** Momentum 55.7% → 19.4%;
Bollinger 83.7% → **1.8%**. Uncorrected, Bollinger read as an 84%-likely edge.

**N is measured, not assumed** (`backend/trials.py`, roadmap 5 of 5). Raw
grid size treats a 20-day and a 25-day lookback as independent trials. Two
estimates from the candidates' in-sample return matrix:
- [ ] **Eigenvalue count** — Li & Ji (2005): `N_eff = Σ [1(λ≥1) + frac(λ)]`
  over the correlation matrix's eigenvalues. Closed form; errs high on tight
  blocks (small eigenvalues each add a fraction).
- [ ] **Correlation clustering** — López de Prado & Lewis (2019): average-
  linkage on `d = √((1−ρ)/2)`, K by silhouette, one trial per cluster, spread
  across cluster representatives (only from K ≥ 3 — a std of two numbers is
  not an estimate). Silhouette < 0.1 → one blob if every ρ > 0.875, else N.
- [ ] **Headline = the larger estimate.** Lowering N flatters a result; when
  the two disagree the tool keeps the higher bar and shows the other as the
  lower bound. Pinned by test.
- [ ] AAPL 2018→2024-01-01: momentum 16 → 6 (clusters 3), MACD 4 → 2,
  Bollinger 12 → 7 (clusters 2); DSR moves +0.07…+0.12; no verdict changes.

Remaining limitation: the estimates disagree by 2–3× on this grid, with
silhouettes ~0.25 (weak structure). The truth is between them.

## 4. Probability of Backtest Overfitting via CSCV — `backend/pbo.py`

Bailey, Borwein, López de Prado & Zhu (2014), "The Probability of Backtest Overfitting".

- [ ] **What**: cut the period into S = 8 blocks; form all C(8,4) = 70 balanced
  train/test splits; on each, pick the best candidate on train and find its
  rank on test. `PBO` = share of splits where the train-winner lands below the
  test median. 0.5 = selection is no better than random.
- [ ] **Also reported**: `probability_of_loss` (winner has OOS Sharpe < 0) and
  `degradation_slope` (regress OOS on IS across candidates; negative = better
  in-sample predicted worse out-of-sample). PBO alone under-reports: on a random
  walk momentum scored a middling 0.41 while P(loss) = 0.90 and slope = −0.69.
- [ ] **Speed**: ~0.03s, because the candidate matrix from §1 is just row-sliced.
- [ ] **Traps**: a flat candidate must score −inf, not 0, or it outranks losing
  strategies and wins training. Ties: `worse + (tied+1)/2` so a total tie sits
  at the median.
- [ ] **Limitation, pinned by a test**: CSCV draws both halves from blocks
  across the whole period, so it *cannot see a regime break* — an edge confined
  to the first half still scores PBO 0.01. Walk-forward is chronological ("did
  it survive later"); CSCV is combinatorial ("is selecting on IS score better
  than random"). Complements, not substitutes.

## 5. Purge and embargo — `backend/purge.py` → `purged_split()`

AFML ch. 7.

- [ ] **The leak was not the warm-up window.** An MA reaching back across the
  split is legitimate — that is what you do live. The defect is the trade
  *straddling* the cut: opened in selection, still open in scoring, paid off one
  price move on both sides. Measured on 5y daily: the momentum grid's boundary
  position was held up to 33 bars and ran 12 more.
- [ ] **Gap** = 1% of the period (`EMBARGO_PCT`), floored at 5 bars
  (1% of 1y = 3 days < a holding period), capped at 25 (past a month it costs
  more OOS data than the bias it removes). Symmetric, so dead zone = 2·gap.
  Yields when honouring it would leave a half < 30 bars; sets `shortened`/`applied`.
- [ ] **It is not a deflator.** 4 tickers × 3 strategies: OOS Sharpe median
  moved +0.014, down in 5 of 12, up in 7; individual moves up to 0.7; the winner
  changed in 2. The case is structural (no bar counted twice), not "it makes
  numbers smaller".
- [ ] `in_sample_bars` / `out_of_sample_bars` report bars *actually used*, not
  the nominal 70/30 — pinned so nobody "fixes" it back.

## 6. Block-bootstrap confidence intervals — `backend/bootstrap.py`

On **every** `POST /api/backtest`, every plan, ~50ms. Deliberately not Pro-gated:
the free tier is exactly who takes a Sharpe at face value.

- [ ] **Stationary bootstrap** (Politis & Romano 1994): resample blocks of
  geometric random length so the resampled series stays stationary.
  Code: `stationary_bootstrap_indices()`, 1000 resamples.
- [ ] **Automatic block length** (Politis & White 2004; Patton, Politis & White
  2009): flat-top kernel spectral estimate. Code: `politis_white_block_length()`.
- [ ] **Chosen from TWO series, longer wins: returns AND squared returns.**
  A strategy return is position × price return; price returns are near-white,
  so the returns arm says ~1 even for a 30-bar holding period. Uncertainty in
  Sharpe/vol/drawdown lives in the second moment (volatility clustering is
  long-memory). Code: `choose_block_length()`.
  Failed first attempt: "first ACF lag inside 1.96/√n" *as* the block length —
  saturates on squared returns and returned a block a tenth of the sample.
- [ ] **BCa intervals** with a **delete-one-BLOCK jackknife** — delete-one-
  observation is invalid under serial dependence (Künsch 1989).
  Code: `_bca_interval()`, `_block_jackknife()`.
- [ ] **Measured coverage, not assumed**: 300 GARCH(1,1) paths, n = 1250,
  nominal 95% → 7 of 9 metrics 92.7–95.0%. Two fail and are FLAGGED in the
  response and the UI:
  - `annualized_volatility` 69.7% — reproduces 56% of true spread. Not fixable by
    tuning: half the variation in a 5y realised vol is which regime the period
    sat in, and no resample can recreate a regime it did not contain. Sharpe
    escapes because it is a ratio — regime level cancels.
  - `max_drawdown` 79.0% — a resample preserves order only inside a block.
- [ ] **Three metrics get no interval, on purpose**: `best_day` / `worst_day`
  (a resample draws only from days that happened — the interval would be bounded
  by the statistic it bounds, understating tail risk exactly where it matters)
  and `num_trades` (resampling moves returns, not the position path).
- [ ] **Seed = blake2b of the run's inputs, never builtin `hash`** — `hash(str)`
  is salted per process, so a "deterministic" interval would move on every
  restart. Only a *subprocess* test catches this.
- [ ] Band bounds are rounded harder than the point estimate (0dp for %):
  "+404.95%" claims precision the interval is denying.

**Headline**: AAPL momentum 2019–2024 Sharpe 0.3865, 95% CI −0.39 to 1.29.
Spans zero. Agrees independently with the walk-forward finding.

Latent bug found alongside: `compute_metrics` raised `TypeError` when a strategy
lost > 100% — `(1+total)**(252/n)` is complex for a negative base. Reachable
(max_leverage up to 5.0). Pinned at −1.0.

---

## 7. Rolling walk-forward — `backend/rolling.py` → `rolling_walk_forward()`

- [ ] **Why it exists**: §1 tries one split, and the split lands wherever 70%
  of the requested window falls. Measured 15 Sep 2026: AAPL 2018→2024-01-01
  says momentum fails and Bollinger holds; extend to 2025-01-01, the in-sample
  end moves Feb→Oct 2022, and it inverts. One split is one draw from a
  distribution of splits.
- [ ] **What**: anchored. First split at 40% of the period; what remains is
  tiled into K = 4 segments. Fold k sweeps the grid on `[0, split_k)` and
  scores the winner on `[split_k, split_k+1)` only. Anchored (expanding, not
  fixed-length) because that is what a live re-fit does — use all history.
- [ ] **Purge at every boundary**: `purged_split` sizes the gap on the whole
  series; the bars purged from fold k+1's in-sample end are the *last* bars of
  fold k's segment, so the straddling trade is scored once and never selected on.
- [ ] **Stitched curve**: the segments concatenated (embargo gaps excluded) are
  the out-of-sample record of the *procedure* — "re-fit periodically, trade
  the winner" — not of one parameter set. It gets `compute_metrics` and a §6
  bootstrap interval on its Sharpe.
- [ ] **Per fold**: best params, IS and OOS Sharpe, `_verdict`, plus the
  market's own return and realised vol over the segment, so a failed fold can
  be read against what the market did.
- [ ] **Parameter stability**: distinct winners across folds and the modal
  set's share. A winner that changes every re-fit was never one strategy —
  momentum on AAPL changed all four times.
- [ ] **Overall verdict**: `consistent` (every fold positive and the stitched
  Sharpe positive), `failed` (no fold positive), else `regime_dependent`.
  All three strategies on both AAPL windows read `regime_dependent`.
- [ ] **Cost**: positions per grid cell are built once on the full series and
  sliced per fold; K folds cost one sweep plus K×N metric evaluations.
- [ ] **What it does not do**: it does not *detect* regimes. Folds are calendar
  segments; the regime is read off `benchmark_return` and `realised_volatility`
  by the human. A vol-tercile label is the obvious next step
  (research/open-questions.md §3).
- [ ] Tests (`tests/test_rolling.py`, 18): geometry, anchoring, purge, "scores
  are full-series positions sliced", "winner chosen on IS only", synthetic
  trend → consistent, whipsaw → failed, trend-then-whipsaw → regime_dependent.
  Three mutations (select on OOS; drop the gap; fixed window) each fail
  exactly one test.

Read: Pardo, *The Evaluation and Optimization of Trading Strategies* (2008),
ch. 9–11 — the original walk-forward analysis; AFML ch. 12 for the anchored
vs rolling distinction and why purging still applies per fold.

## 8. Volatility regimes — `backend/regimes.py`

- [ ] **What**: trailing 21-bar standard deviation of the *market's* daily
  returns, annualised, one value per bar; cut into terciles of the period
  (`low` / `mid` / `high`). The strategy's net return is then grouped by
  label: Sharpe, arithmetic contribution, hit rate, time in market, and the
  market's own Sharpe on the same bars.
- [ ] **Why the market's vol, not the strategy's**: the regime is a property
  of the conditions, not of the trade. A flat strategy has zero variance and
  would collapse the labels. Pinned by test and a mutation.
- [ ] **Why trailing, not centred**: the window ends at the bar it labels. It
  is a description, not a signal, so lookahead is not the concern — but a
  centred window would label a bar by turbulence that arrived later, which
  is not what "the bar was in a high-vol regime" means. Mutation-checked.
- [ ] **Why period-relative terciles**: 20% vol is "high" in 2017 and "low"
  in 2020. The question is how *this* backtest's return is spread across
  *its* conditions. Thresholds are reported so "high" has a number.
- [ ] **Sharpe form**: mean/std × √252 on non-contiguous bars — the §1
  headline's compounded form would describe a trade nobody could make.
  Contributions are arithmetic and sum to the arithmetic total.
- [ ] **Where**: every `/api/backtest` (`regimes`) and the stitched
  out-of-sample record of §7 (`out_of_sample_stitched.regimes`). Below 63
  labelled bars the block reads `computable: false`.
- [ ] **What it says on AAPL**, out-of-sample: momentum Sharpe 2.26 in the
  calm third (market 2.49 — beta), −0.76 in the turbulent third (market
  +0.60 — whipsaw). Bollinger the mirror: −1.83 calm, +1.31 turbulent.
- [ ] **The second axis — trend (21 Sep)**: `label_trend` gives every bar
  the t-statistic of the market's trailing 60-day mean return,
  `sum(r) / (std(r) · √60)`; above +1 `up`, below −1 `down`, else `flat`.
  A fixed ±1σ cut, not a tercile, because "flat" has to mean flat
  (DECISIONS 21 Sep); scaled by the window's own vol so it is unit-free
  across tickers and harder to earn in turbulence. `trend_breakdown` is the
  same table by trend label; `joint_breakdown` crosses the two into a 3 × 3
  vol × trend grid, Sharpe per cell, cells under 21 bars reported by count
  only. Both ride along in every `regimes` block as `trend` and `joint`;
  `RegimeTable.jsx` shows them under the vol table as a direction table
  and a 3 × 3 grid with the best and worst cell marked.
- [ ] **What the grid says on AAPL** (2018→24, out-of-sample): the guess
  that momentum's calm edge was beta in disguise was wrong — calm-flat 2.40,
  calm-rising 2.29. What it does separate is the turbulent third: momentum
  −1.88 in turbulent-*flat* bars (199) and +1.29 in turbulent-rising (84).
  The loss the vol label pinned on "turbulence" is chop. Bollinger reads the
  same cell the other way, +2.19 turbulent-flat and −1.01 turbulent-rising;
  MACD earns in flat markets at any vol (2.65 / 3.38 calm / mid) and loses
  in rising ones. "Down" is 5% of AAPL's bars, 62 of 72 in the turbulent third
  — on a bull-market stock that cell is honest about being empty.
- [ ] Tests (`tests/test_regimes.py`, 14; `tests/test_trend_regimes.py`,
  21): tercile shares, unlabelled warm-up, thresholds match cut points, vol
  formula, block series → label, market-not-strategy labelling, shorter
  strategy series labelled on the full market, contributions sum, degrade on
  short input; z is the t-statistic, compounded window return, steady drift
  → up/down, zero drift mostly flat, same move is a trend in calm and noise
  in turbulence, zero variance → flat, labels sit on the σ cut, grid cells
  partition the bars, sparse cell has no Sharpe, calm-and-rising found when
  planted. Six mutations caught (drop √n, flip the cut, OR for AND in the
  grid, unscaled z, score sparse cells, centred window).

Read: Ang & Bekaert (2002), "International Asset Allocation with Regime
Shifts" — the two-state vol regime as the minimal model; AFML ch. 17 for
structural breaks as the harder version of the same question.

## 9. Whole-grid inference — `backend/snooping.py` → `whole_grid_test()`

- [ ] **The question**: §3 deflates the *winner*; §4 asks whether *selecting*
  works. This asks White's (2000) question: across every cell in the grid at
  once, is there evidence that *any* of them beats a benchmark — with the
  search inside the bootstrap, so the best is judged against the
  distribution of a best, not of a single draw.
- [ ] **The comparison**: each cell's per-bar net return minus buy-and-hold on
  the same bars, full period, trimmed to the longest warm-up (the same
  matrix §4 uses). Statistic = mean excess return. Buy-and-hold because
  "beats the market" is the claim a user is making, and it is the one
  benchmark every grid shares.
- [ ] **Reality Check** (White 2000): `T_RC = max_k √T·d̄_k`; bootstrap the
  same maximum with every cell recentred to its own mean; p = share of
  resampled maxima ≥ observed. Not studentised; and recentring *every* cell
  means junk cells inflate the null maximum — a bad grid makes rejection
  harder, which is backwards.
- [ ] **SPA** (Hansen 2005): studentise, `t_k = √T·d̄_k / ω̂_k` with ω̂ the
  bootstrap s.e.; and leave cells with `t_k ≤ −√(2 log log T)` at their
  negative mean instead of recentring, so they cannot pad the null. Three
  p-values: lower (every negative mean kept), consistent (the rule above),
  upper (everything recentred = White's treatment). Always
  `lower ≤ consistent ≤ upper`. When no cell has a positive mean the
  statistic clips to 0 and p is 1.000 — correct, and blunt.
- [ ] **Romano-Wolf stepdown** (2005): the answer to "which cells". Rank by
  t; test the top against the max over all, the next against the max over
  the rest, carrying `max()` forward so adjusted p is monotone in rank.
  Family-wise error at α; `cells[].p_adjusted ≤ α` are the survivors.
- [ ] **Resampling**: `stationary_bootstrap_indices` from §6 with the
  Politis-White block length chosen on the winner's excess series; ONE
  index draw applied to every column, which is what makes the maximum's
  distribution joint. B = 1000, `(1 + hits)/(B + 1)` so p never reads 0.
- [ ] **What it says on AAPL 2018→2024**: buy-and-hold made ~30%/yr, so every
  long-only cell trails it — momentum's best −6.4%/yr, RC p 0.89, SPA 1.0,
  0 of 16 survive; MACD 0 of 4; Bollinger 0 of 12. Five tickers × two
  windows × three grids: **0 survivors anywhere**. The snooping gap is
  visible even so — BABA Bollinger's best cell reads p 0.17 alone, 0.33
  inside its grid. And momentum on AAPL 2018→2025 is `held_up` on §1
  while trailing buy-and-hold by 9.6%/yr: "held up" is against zero, not
  against the market.
- [ ] **What it does not say**: full-period inference with the snooping
  removed — whether the grid *contains* outperformance over this period,
  not whether it persists (§1, §7). Long-only cells against a rising
  benchmark will rarely clear it; that is the finding, not a defect.
- [ ] Tests (`tests/test_snooping.py`, 17): shape contract; grid-of-one is
  the naive test; p floor; determinism; the snooping gap on a null grid;
  Hansen's ordering; junk padding hurts RC more than SPA; stepdown finds
  exactly one / exactly two planted cells with monotone adjusted p; FWER
  ≤ bound over 40 null grids; flat cell excluded from studentisation;
  consistent < upper with junk present; stepdown's second test is over
  the rest, not the whole grid; wiring into `walk_forward` (labels,
  seed). Six mutations each caught: no recentring, RC ignoring the grid,
  consistent = upper, non-monotone stepdown, single-step, no
  studentisation.

Read: White (2000) "A Reality Check for Data Snooping"; Hansen (2005) "A Test
for Superior Predictive Ability"; Romano & Wolf (2005) "Stepwise Multiple
Testing as Formalized Data Snooping".

## 10. The same questions, asked of a basket — `backend/portfolio_validation.py`

- [ ] **What changes**: nothing in the maths of §1, §3, §4, §5 or §9 — all of
  it is reused. Two *decisions* change, and each is a null hypothesis in
  disguise.
- [ ] **What is optimised**: `/api/portfolio` runs one strategy with one
  parameter set shared by every leg, so the grid is scored on the **book's**
  in-sample Sharpe. Per cell: leg positions → each leg's net return after its
  own costs → weighted sum. A cell that flatters one leg and ruins another is
  judged on the net. The whole-grid benchmark (§9) becomes *holding the basket
  at the same weights*. A `legs` block reports the winner's IS/OOS Sharpe per
  ticker, because a book that held up may have done so on one name.
- [ ] **What "random timing" means for a book** — the choice that had to be
  made before any code (open-questions §2). Two candidate nulls:
  1. *Shuffle each leg's position series independently, weights fixed.* Null =
     no leg can time its own market. The book under the null still has
     exposure and diversification, so its null distribution is **not** where a
     single leg's would be — which is the point: a basket of un-timed legs
     should not look timed. ← **implemented**.
  2. *Shuffle the weight path, keep the legs.* Null = the allocation rule adds
     nothing over a random one. A question about the weighting, not the
     signal; only meaningful when weighting ≠ equal. Not implemented.
- [ ] **Why independent, not one shared permutation**: with a shared draw two
  legs that are mirror images would cancel on every trial as they do in
  reality, the null would be pure cost drag, and a flat book would read as
  timing skill (`test_legs_are_shuffled_independently`; the shared-draw
  mutant survived the first draft of the suite, which is why that test reads
  the way it does).
- [ ] **Per-leg block**: the ordinary §2 test on each leg, from the same draws.
  A significant book can be traced to the legs that carried it.
- [ ] **Anchor**: a one-leg book with weight 1 reproduces `walk_forward()` and
  `permutation_test()` *bit for bit* (same seed, same draw order). That is
  what lets the verdict card mean the same thing on either universe.
- [ ] **Measured 21 Sep 2026, AAPL+MSFT+GOOGL 2018→2024 equal weight**:
  momentum fails (IS 0.42 → OOS −0.51; PBO 0.70; only AAPL beats random
  timing, p 0.022). Bollinger **holds up** (0.83 → 0.77; PBO 0.21; all three
  legs beat random timing, book p 0.002) — and the best grid cell trails
  holding the basket by 18.7 %/yr, SPA p 1.0. Timed, and not worth timing:
  the two-verdict case the card's new sentence was written for.
- [ ] **Not done**: rolling walk-forward (§7) and regimes (§8) for a book.
  The validation tab reads the basket route in portfolio mode (same verdict
  card, four checks instead of five since §7 is absent, per-name tables).

## 11. Is the Sharpe gap real? — `backend/sharpe_test.py`

- [ ] **The gap this fills**: every backtest page prints the strategy's Sharpe
  and, on the curve beside it, buy-and-hold's. Two numbers invite exactly one
  comparison and give no way to make it. §9 tests the whole grid against
  buy-and-hold on *mean return*; this tests the run in front of the user, on
  *Sharpe*, which is the number the page actually shows.
- [ ] **Method**: Ledoit & Wolf (2008), "Robust performance hypothesis testing
  with the Sharpe ratio". Δ = SRa − SRb is a smooth function of four moments
  (μa, μb, γa, γb); the delta method turns their long-run covariance into
  s²(Δ) = ∇f'Ψ∇f / T. Because ∇f is a fixed vector, ∇f'Ψ∇f is just the long-run
  variance of the **scalar** series u_t = ∇f'(y_t − ȳ) — so the HAC step is
  one-dimensional, which is both cheaper and far easier to test than a 4×4
  kernel estimate.
- [ ] **Why not a t-test**: the strategy trades the benchmark's own asset, so
  the two series share most of their bars. Treating them as independent throws
  the pairing away and the test becomes far too conservative. Measured: same
  two Sharpe ratios, correlated 0.95 vs correlated 0.0 — the paired standard
  error is under 40% of the unpaired one (`test_pairing_shrinks_the_error_bar`).
- [ ] **Kernel**: Bartlett, bandwidth from Andrews (1991)'s AR(1) plug-in. Not
  chosen for efficiency — Parzen and QS converge faster — but because the
  Bartlett estimate is a sum of squares and *cannot* come back negative. The
  clamp that would hide a broken kernel is deliberately absent, and the test
  for it is the alternating series where a rectangular kernel returns −1.
- [ ] **Two p-values, both reported**: the normal one off the HAC statistic,
  and the headline — Ledoit-Wolf's studentised bootstrap, which resamples the
  pair (one index draw, applied to *both* series) and recomputes the standard
  error on each resample. Resampler and block length are §6's.
- [ ] **Size and power, measured** (500 paths × 1250 bars, GARCH marginals; the
  null is a mixture carrying the benchmark's own mean and variance, so its
  Sharpe is equal by construction):

  | size — null, correlation with benchmark | rejects @5% |
  |---|---|
  | 0.9, a strategy trading the benchmark's own bars | 5.2% |
  | 0.7 | 6.8% |
  | 0.0, an unrelated asset | 8.8% |

  | power — alternative | true gap | rejects @5% |
  |---|---|---|
  | +5%/yr mean | +0.47 SR | 27.8% |
  | +10%/yr mean | +0.92 SR | 74.4% |
  | +20%/yr mean | +1.78 SR | 98.8% |

  Mildly anticonservative, worst in the case this module is least likely to
  meet. The power column is the more useful half: **a strategy needs about a
  full point of Sharpe over five years before this test will call it** — worth
  knowing before reading p = 0.3 as evidence of no edge.
- [ ] **Measured 23 Sep 2026, three strategies × four runs**: every strategy on
  AAPL, BABA and SPY trails buy-and-hold on Sharpe, and *not one of those gaps
  is distinguishable from noise* — the standard error is 0.5 to 0.7 over six
  years. The single significant result is AAPL 2015→2020 Bollinger: −1.45,
  p = 0.031, significantly **worse**. The honest summary of the canonical demo
  is not "momentum loses to holding AAPL" but "six years cannot tell, and the
  point estimate is a loss".
- [ ] **A caveat the UI has to carry**: this Sharpe is mean/σ×√252; the
  headline card's is geometric (annualised return / annualised vol). Volatility
  drag puts the arithmetic figure 0.05–0.19 *above* the headline one on these
  runs (AAPL momentum: 0.59 here, 0.48 on the card). Always the same direction,
  so the tested pair flatters the strategy; show the pair that was tested.
- [ ] **Mutation-checked, and one survivor recorded rather than hidden**: 7 of 8
  mutants die. The survivor is "draw each series its own bootstrap path" —
  measured at 200 null paths and 200 alternatives, size and power move by under
  a point, because a *studentised* statistic normalises by the resample's own
  standard error and so barely notices. The paired draw is kept (it is what the
  method specifies and it is free), but no test in the suite pins it, and
  pretending otherwise would be worse than saying so.

## How the eleven fit together

```
                 ┌─ §5 purge/embargo (no bar paid twice)
walk-forward ────┤
  (§1)           └─ §3 DSR   (was the IS winner better than max-of-N noise?)
rolling (§7) ────── the same, K times, walked forward: is the verdict a regime?
regimes (§8) ────── which third of the market's conditions carried the return —
                   and, crossed with trend, which cell of the 3 × 3?

CSCV (§4)  ─────── is *selecting on IS score* better than random at all?
snooping (§9) ──── does *anything* in the grid beat buy-and-hold, search included?
permutation (§2) ─ is the *timing* better than a shuffle?
bootstrap (§6) ─── how wide is the band around every number you printed?

basket (§10) ───── §1 + §3 + §4 + §9 on the book's returns; §2 with every leg
                   re-timed on its own, weights fixed
sharpe gap (§11) ─ is the Sharpe printed on the page above buy-and-hold's by
                   more than this many bars can tell? (paired, HAC, two-sided)
```

Each answers a different question. None replaces another. The UI shows all of
them (`ValidationPanel.jsx`: walk-forward → rolling → deflated → PBO → whole
grid → permutation; `MetricsGrid.jsx`: CI bands). In portfolio mode the same
panel reads `/api/portfolio/validate` — no rolling section, per-name tables.

## Test discipline that made this trustworthy

- Formulas verified against sources *outside* the codebase before use.
- Constants pinned to the papers (3.26; Lo 2002 to 1e-12).
- Coverage *measured* on synthetic GARCH paths, failures shipped as flags.
- Mutation-checked: delete the check, watch exactly the right tests fail.
- A negative control before believing a regression: the vol-scaled cost model
  died because the estimator that would have calibrated it reports the same
  slope on data where the effect is absent by construction (`costs.py`).
- 717 tests, `cd backend && .venv/bin/python -m pytest tests/ -q`, no credentials, no network.

Next: [research/reading-list.md](research/reading-list.md)
