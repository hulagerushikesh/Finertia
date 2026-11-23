# Backlog

Everything not in the current milestone. "Evidence" = what would prove it done.

## Search (proposed 21 Nov, waits on the author — see SEO-PLAN.md)

- [x] G1 request indexing, done 21 Nov by the author: W1 article queued; `/` already indexed; `/writeup`, `/writeup/nifty-50`, `/demo`, `/learn` requested or already indexed. 22 Nov: all 11 `/learn/*` articles requested; Search Console says "URL is not on Google" (not yet indexed). The W6 request once came back "Indexing request rejected" with no reason captured; a Googlebot-smartphone render of the page was clean (200, self-canonical, no noindex, no errors, 1,300 words). Author's call: revisit only if reach has not moved by ~29 Nov
- [ ] Google steps G2–G5 (weekly Pages and Performance reads, Bing import, link from hulage.in). G4 done 22 Nov by the author: imported from Search Console, `finertia.hulage.in` listed in Bing Webmaster Tools, sitemap submitted (Bing says data takes up to 48 h). Open: G5 link from hulage.in, G2/G3 weekly reads. Evidence: Bing shows the sitemap; hulage.in links to Finertia
- [ ] Articles W1–W6 under `/learn`, one a week (W1 live 21 Nov, PR #198; W2 live 21 Nov, PR #199; W3 Bollinger live 21 Nov, PR #201; W4 backtesting guide live 21 Nov, PR #203; W5 MACD live 22 Nov, PR #204; W6 costs live 22 Nov, PR #205 — all six live; next is the 8-week read, mid-Jan 2027). Evidence: each live, pre-rendered, in the sitemap; impressions read after 8 weeks

## Small and unblocked

- [x] ~~Narrow the `gh` token~~ — closed 22 Nov by the author's choice: the broad token stays, on the rule that only Finertia is touched and other repos need the author's approval first
- [x] Remaining frontend advisories (21, 24 Oct) — done 22 Nov: firebase 10 → 12.19 (fixes undici; 13 was not needed and wants Node ≥ 24.12), grpc-js forced to 1.14.7 by an `overrides` entry (firestore still pins ~1.9; Node-side only), vite 5 → 7.3, plugin-react 4 → 5, vitest 2 → 4.1.12. Node pinned to 22.x (`engines` + `.nvmrc`; CI was already 22). `npm audit` 0, 384 tests, build and bundle budget pass (entry 210.6 of 210.9 kB — firebase 12 added ~2 kB). Local Node 20.12 is now too old to run the tests
- [x] Tab double-fire on `@radix-ui/react-tabs` ≥ 1.2 — fixed 22 Nov: `handleValidate` now holds a ref (`validatingNow`) so a second call in the same event returns. Checked: on tabs 1.2.1 the two DashboardPage tests failed without the guard and all 384 pass with it; on the shipped 1.1.21 all 384 pass. The lockfile stays on 1.1.21 (1.2.1 adds ~4 kB to the total bundle)
- [x] Project venv → M9 phase 0, done 14 Sep
- [x] Bundle-size CI check — `frontend/scripts/check-bundle.mjs` + `bundle-budget.json`, gzip entry + total, limits ~10% over the 19 Sep build; CI step "Bundle budget" (19 Sep)
- [x] Backend deploy reminder — `backend-drift.yml` diffs `backend/` against the `backend-deployed` tag on every push to main and comments on the merged PR; deploy.yml moves the tag, manual deploys move it per README (19 Sep)
- [x] Rotate the Cloud Run runtime SA to a dedicated one — `finertia-api-runtime`, zero project roles, `secretAccessor` on `finertia-sa` only; default compute SA's secret grant removed; rev 00008 (20 Sep)
- [x] Deploy workflow runnable — WIF pool/provider `github` (this repo, `main` only), `finertia-deployer` SA with deploy-only roles, both repo secrets; `.github/scripts/setup-wif.sh`; first workflow deploy rev `00011-cwn`, tag moved by the workflow (28 Sep)

## Research (after effective N)

- [x] Portfolio-level validation — null decided (each leg re-timed independently, weights fixed; DECISIONS 21 Sep); `portfolio_validation.py` + `POST /api/portfolio/validate`, 21 tests, 4 mutations caught (21 Sep)
- [x] Show the validation tab in portfolio mode, reading `/api/portfolio/validate` — same verdict card, per-name tables in walk-forward and timing, basket wording (21 Sep)
- [ ] Weight-path permutation null for inverse-vol baskets (the other half of open-questions §2) — only if anyone asks
- [x] Regime-aware walk-forward — anchored rolling folds + realised-vol regime label, both 16 Sep (`rolling.py`, `regimes.py`, §3). Trend label beside vol added 21 Sep (`label_trend`, ±1σ t-stat, vol × trend grid; DECISIONS 21 Sep) — on the regime table in the UI since PR #46 (direction table + vol × direction grid)
- [x] Whole-grid inference: White Reality Check / Hansen SPA / Romano-Wolf stepdown (§4) — `backend/snooping.py`, in every `/api/validate` as `walk_forward.snooping`; 17 tests, 6 mutations (20 Sep)
- [x] Surface the `snooping` block in `ValidationPanel` — sixth verdict-card check "Whole grid", a "The whole grid against holding" section with the four p-values and the per-cell stepdown table, glossary entry (21 Sep). Not in `/demo`: that page is a frozen `/api/backtest` payload and carries no validation block at all; putting one there is a separate decision
- [x] Max-drawdown interval with honest coverage (§5) — the band was never too narrow (98% of the true central-95% range); BCa's `z0` was correcting a bias that belongs to the block scheme, not the estimator, and is mostly noise (sd 0.44–0.63). Suppressed for `max_drawdown` and `calmar_ratio`, acceleration kept: 79% → 95.0%, confirmed on three generators. 6 tests, 6 mutations, 1 survivor closed (DECISIONS 23 Sep)
- [x] Vol-scaled transaction-cost model (§7) — **not shipped, and that is the finding.** The coefficient is unidentifiable from daily OHLCV (high-low spread estimators report a vol slope of 0.23-1.07 on a CONSTANT true spread — they return their own noise floor, which scales with vol; real tickers give 0.73-1.03, inside that range), and holding total cost paid fixed, the model's shape moves Sharpe by ≤0.015 against 0.16-0.32 per 10bps of level. Shipped the level instead: `costs.py` gives the breakeven cost and the headroom over the user's assumption, on every `/api/backtest` as `cost_sensitivity`. 15 tests, 9 mutations, 7 caught and both survivors measured (DECISIONS 24 Sep)
- [x] Show `cost_sensitivity` on the results card — `CostSensitivity.jsx` under the headline metrics on Dashboard and Demo: breakeven cost, headroom multiple, and the metrics at 0x/0.5x/1x/2x/5x with the user's own assumption picked out. No "safe" threshold — colour marks only that the strategy is already past breakeven (PR #54, 24 Sep)
- [x] `cost_sensitivity` for portfolios — the book IS affine in cost the same way a leg is (weights come off close returns, positions off closes; nothing upstream reads the cost), checked against the real `combine` to 2e-17 on both weighting schemes rather than assumed. Same bisection, on every `/api/portfolio`; the existing card renders it unchanged. 5 tests, 5 mutations, 4 caught and the survivor shown unobservable (25 Sep)
- [x] Ledoit-Wolf test for strategy-vs-benchmark Sharpe difference — the "does it beat buy-and-hold" question with a p-value; `sharpe_test.py`, paired HAC + studentised bootstrap, two-sided, on every `/api/backtest` and `/api/portfolio` as `benchmark_test`; 32 tests, 7 of 8 mutations caught and the survivor documented; size and power measured (DECISIONS 23 Sep); on the UI since PR #49
- [x] Show `benchmark_test` on the results card — `BenchmarkTest.jsx` under the headline metrics on Dashboard and Demo, its own arithmetic Sharpe pair with the standard error beside the gap, colour only on a called difference (PR #49, 23 Sep). Renders once rev 00010 ships the block

## Product (parked — Phase 4 picked "portfolio"; reopen only on the reversal conditions in DECISIONS.md)

- [ ] Wire Stripe: keys + `STRIPE_WEBHOOK_SECRET` on Cloud Run; never without the secret
- [x] Sentry DSN — on, backend and browser, errors only, uid only (M11 #3, 13 Oct)
- [x] Support inbox that a human reads — `support@hulage.in` to the author (M12 #7, 13 Oct)
- [x] Admin stats via aggregation queries instead of collection scans — `admin_queries.py` (M11 #6, 13 Oct)
- [ ] Email notifications for long validation runs
- [ ] Intraday bars (needs a paid data source)

## Portfolio / write-up (Phase 4 picked "portfolio", 15 Sep)

- [x] 1,500-word write-up — drafted as `planning/write-up.md`: both windows, the per-check disagreement, bootstrap intervals on the OOS Sharpes
- [x] Put the write-up on hulage.in (or a `/writeup` route) and link it from the README and the landing page — shipped 7 Oct at `/writeup` (#61), before the result (DECISIONS 7 Oct)
- [x] Short demo GIF of `/demo` → validation tab for the README — `docs/demo.gif` (#63)

## Docs

- [x] README "Deploy" section rewritten for Vercel + Cloud Run (13 Sep)
- [x] README route and test counts — 16 routes, 603 tests (19 Sep)
- [x] Retire the stale artifacts in artifacts.md — five republished with a retirement banner (checklist, product brief, learning path, progress tracker, 20 Aug orphan ledger); execution plan already deleted (20 Sep)

## Done (moved from earlier lists, kept for the record)

- [x] S1 smoke test on live · [x] Docker image built · [x] GCP billing · [x] `VITE_SUPPORT_EMAIL` · [x] GitHub secret scanning + push protection · [x] walk-forward finding in README · [x] DSR · [x] PBO · [x] purge/embargo · [x] bootstrap CIs · [x] `.gcloudignore` · [x] requirements pinned
