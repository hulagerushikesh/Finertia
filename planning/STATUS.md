# Status

_Current to `421eeb2` (main) · 7 Oct 2026._

## At a glance

| | |
|---|---|
| Live | https://finertia.hulage.in — Vercel (frontend) + Cloud Run `finertia-api` asia-south1 rev `00018-ml7` (7 Oct, built from `421eeb2` by the Deploy workflow; 00017 and 00018 serve the same code — 00018 only re-ran the workflow after #69; runs as `finertia-api-runtime`). Rev 00017 added the admin Pro grant (#68): `PATCH /api/admin/users/{uid}` accepts `plan`, stamped `planSource`. **`backend/` on `main` == prod == `backend-deployed` tag.** Rev 00010 ships the six backend PRs that had queued since rev 00009: basket validation (#41), trend label (#45), Sharpe-difference test (#48), drawdown-interval fix (#51), cost level (#52), portfolio cost sensitivity (#55) — so the portfolio-mode Validation tab, the regime direction section, the Sharpe p-value strip and the cost-tolerance strip now have their payloads. Frontend = the shadcn redesign since 17 Sep (PR #6), plus the 19 Sep UI batch (PRs #13, #14, #16, #17), the same-day simplification (PRs #19–#23), the 21–23 Sep research UIs (#46 direction table + vol × direction grid, #49 the Sharpe p-value strip) and the 24 Sep batch (#53 readable 422s + mode-toggle crash, #54 cost-tolerance strip) |
| Judged link | https://finertia.hulage.in/demo — Builders Pitch Fest 2026, BFSI, submitted 6 Sep; result pending |
| Tests | 723 backend (`cd backend && pytest tests/ -q`, re-run 28 Sep before the deploy), 20 Firestore-rule (`cd firestore-tests && npm test`) |
| CI | green on `main` (backend tests + frontend build + bundle budget + secret scan); `backend-drift.yml` comments on the merged PR when `backend/` is ahead of the `backend-deployed` tag |
| Commits | 182 on main (`git rev-list --count`, 7 Oct) · 68 PRs merged (`gh pr list --state merged`, 7 Oct) |
| API | 17 routes |
| Cost | ₹0 idle (`min-instances 0`, max 2, 512Mi) |
| Blocked on user | 3 — login smoke test **on production**: 28 Sep covered the portfolio results card (found PR #58); 7 Oct covered the regime direction table, History and Profile save (pass) and found the dead-end Pro-wall banner (PR #71); still unwalked: Register a throwaway, portfolio-mode Validation on a Pro account · **no admin account exists** — needed for Give Pro in phase 3 · `gh` fine-grained PAT |
| In flight | M10 phase 3 — [NEXT-MILESTONE.md](NEXT-MILESTONE.md). Phases 1–2 shipped 7 Oct: `/writeup` live with its own share card (#61, #62), `/demo` Validation tab + README GIF (#63). Phase 3 kit in [feedback.md](feedback.md) (#64): 5 outside sessions, start count **0** outside sign-ups / runs. Testers who need validation get Pro from Admin → Users (#68), counted as comped |
| Direction | **Portfolio piece + write-up** (decided 15 Sep, DECISIONS.md); write-up **published** at [/writeup](https://finertia.hulage.in/writeup) 7 Oct, every figure checked by `reproduce_writeup.py`. M10 phase 4 revisits the decision with outside-user evidence |

## Stages — verified vs built

Verified = proven by something that would fail if it broke. Built = written and
compiles, never exercised end to end.

| Stage | State | Evidence |
|---|---|---|
| S1 Connect — Firebase end to end | **Verified** | 3 real AAPL runs on the live site before submission; rules diffed byte-identical against the released ruleset |
| S2 Harden — guards, validators, error paths | **Verified** | Route tests mutation-checked; Docker image built 3× by Cloud Build |
| S3 Deploy — Vercel + Cloud Run | **Verified** | Live since 6 Sep; same-origin `/api/*` proxy; secret in Secret Manager, readable by the dedicated runtime SA only (20 Sep) |
| S4 Deepen — analytics, comparison, permalinks | **Verified** | Walked through on live |
| S5 Strategies — MACD, Bollinger, risk overlays, portfolios | **Verified** | Walked through on live; 535 tests |
| S6 Billing — plans, quota, Stripe | Built | `plans.py` tested; Stripe env-gated and unset in prod, never exercised |
| S7 Ops — rate limit, JSON logs, CI | **Verified** | CI green; deps pinned to prod 13 Sep |
| S8 Grow — demo, docs, support, SEO, email verification | **Verified** | All public routes walked before submission |

## Research roadmap — 5 of 5, plus six post-roadmap

| Item | State | Evidence |
|---|---|---|
| Deflated Sharpe Ratio | Done `4ad1b0c` | 36 tests; reproduces paper's 3.26; Lo (2002) to 1e-12 |
| PBO via CSCV | Done `52217af` | 21 tests; regime-blindness pinned by test |
| Purge + embargo | Done `e840a3c` | 20 tests; boundary trade measured at 33 bars |
| Block-bootstrap CIs | Done `7b178ca` PR #1 | 54 tests; coverage measured on 300 GARCH paths; serving since rev 00003 |
| Effective N of the grid | Done PR #8 | 15 tests; eigen + clusters, headline = larger; canonical AAPL 16→6 / 4→2 / 12→7; mutation-checked |
| Trend label beside vol (post-roadmap, open-questions §3) | Done 21 Sep | `label_trend` / `trend_breakdown` / `joint_breakdown` in `regimes.py`: ±1σ t-stat of the 60-day mean return (fixed cut, DECISIONS 21 Sep), 3 × 3 vol × trend grid in every `regimes` block; 21 tests, 6 mutations caught; AAPL OOS momentum calm-flat 2.40 vs calm-rising 2.29 (calm edge is not beta), turbulent-flat −1.88 vs turbulent-rising +1.29 (the loss is chop) |
| Sharpe vs buy-and-hold (post-roadmap, open-questions §8) | Done 23 Sep | `sharpe_test.py`: Ledoit-Wolf (2008) paired Sharpe-difference test — HAC (Bartlett, Andrews bandwidth) + studentised block bootstrap, two-sided, in every `/api/backtest` and `/api/portfolio` as `benchmark_test`; 32 tests, 7 of 8 mutations caught and the survivor documented; size 5.2–8.8% at nominal 5%, power needs ~1 Sharpe point over 5 years; **no strategy's gap against buy-and-hold on AAPL, BABA or SPY is distinguishable from noise** (s.e. 0.5–0.7), and the one significant result (AAPL 2015→20 Bollinger, p 0.031) is a loss |
| Basket validation (post-roadmap, open-questions §2) | Done 21 Sep | `portfolio_validation.py` + `POST /api/portfolio/validate`: grid scored on the book, every leg re-timed independently (null decided, DECISIONS 21 Sep); 21 tests, 4 mutations caught; one-leg book == single-ticker bit for bit; AAPL+MSFT+GOOGL Bollinger held up 0.83→0.77, timing p 0.002, still −18.7%/yr vs holding the basket |
| Whole-grid inference (post-roadmap, open-questions §4) | Done 20 Sep | `snooping.py`: Reality Check, SPA l/c/u, Romano-Wolf stepdown vs buy-and-hold; 17 tests, 6 mutations caught; 0 survivors on 5 tickers × 2 windows × 3 grids; snooping gap printed per cell |
| Max-drawdown interval (post-roadmap, open-questions §5) | Done 24 Sep, PR #51 | BCa's `z0` suppressed for `max_drawdown` and `calmar_ratio` (`NO_BIAS_CORRECTION`); the band was never too narrow (98% of the true central-95% range); coverage 79% → 95.0% on three generators and five tickers; 6 mutations, 1 survivor closed |
| Transaction-cost realism (post-roadmap, open-questions §7) | Done 24–25 Sep, PRs #52, #54, #55 | vol-scaled model **not** shipped — coefficient unidentifiable from daily OHLCV, shape worth ~1/30 of the level; `costs.py` ships breakeven cost + headroom as `cost_sensitivity` on every `/api/backtest` and `/api/portfolio`, cost-tolerance strip on the results card; 20 tests across the two backend PRs |

## The redesign — PR #6, merged 17 Sep

Merged to `main` on the user's explicit call, before the Pitch Fest result
(the 14 Sep rule said wait; the override is logged in DECISIONS.md). Frontend
only — rev 00007 unchanged. Evidence carried from the preview: contrast
≥ 4.58:1 on 9 routes × 2 themes (measured), 375 px zero overflow, tap-safe hit
areas, one `<main>`, reduced-motion honoured; entry bundle 521 kB raw / 162 gz.

**Not yet verified on the new UI:** the logged-in paths — dashboard at
1024 px, History, Profile displayName save, Register — every
`firebase/firestore/lite` call. That smoke test is now against production.

Follow-ups all landed 19 Sep: "served from cache" note
(`data_source === "cache-stale"`), raw-vs-effective N in `ValidationPanel`,
rolling fold table and regime table (PR #13); favicon set, web manifest and
`og.png` share card (PR #14); plain-language landing copy (PR #16); and a
verdict card — "Is this real?", `N of 5 checks passed`, one plain word per
check, the five sections folded behind "Show the working" (PR #17, replacing
#15 after its stacked base was deleted). All frontend; rev 00007 unchanged.

## Timeline (condensed)

| Date | What | Proved |
|---|---|---|
| 14 Aug | `a3598e0` initial commit — all 8 stages | — |
| 15 Aug | mobile overhaul; Firestore privilege-escalation fix; HTTP-layer tests | 5 attacks closed against emulator |
| 19 Aug | two-tone UI overhaul; DSR; CSCV | paper constants reproduced |
| 20 Aug | purge/embargo | boundary leak measured |
| 22 Aug | type scale; dashboard density | 375 px zero overflow |
| 6 Sep | **deployed**; submitted to Pitch Fest; `Invalid Date` fixed same night | live |
| 8 Sep | bootstrap CIs (PR #1) | coverage measured |
| 13 Sep | backend redeployed (rev 00003); `.gcloudignore`; requirements pinned (PR #3); `.vercel` ignored (PR #4) | prod = pinned deps |
| 14 Sep | `learning/` + `planning/` folders created (PR #5) | — |
| 15 Sep | Firestore price cache (PR #7, rev 00004); effective N (PR #8, rev 00005); `prices` rules deployed; prewarm 28/28 | 17 + 15 tests, 5 mutation checks; walk-forward window flip found |
| 15 Sep | **Phase 4 decided: portfolio piece**; write-up drafted from re-run figures on both windows | — |
| 16 Sep | Volatility regimes (`regimes.py`): per-bar realised-vol terciles, Sharpe per regime on every backtest + the stitched OOS record; PR #11, rev 00007 | 14 + 2 tests, 603 total; 2 mutation checks; momentum OOS 2.26 calm / −0.76 turbulent |
| 17 Sep | **Redesign merged** (PR #6, `e10309b`) on explicit go-ahead; `planning/PROGRESS.md` added | preview evidence; logged-in paths unverified |
| 19 Sep | UI batch on `main`: rolling fold + regime tables, effective N, cache note (PR #13); favicon/manifest/OG (PR #14); plain landing copy (PR #16); verdict card over the validation tab (PR #17) | verified on a real AAPL 2018→2024 payload (2 of 5 checks passed) at 1280 + 375 px, both themes; prod serves the icons and the new copy |
| 20 Sep | Whole-grid inference (`snooping.py`): White RC + Hansen SPA + Romano-Wolf stepdown over the walk-forward candidate matrix vs buy-and-hold, in every `/api/validate` as `walk_forward.snooping`; open-questions §4 closed; write-up gains a table | 17 tests, 620 total; 6 mutation checks; AAPL 2018→24 momentum best −6.4%/yr vs B&H, RC p 0.89, SPA 1.0; no cell survives anywhere; deployed same day as rev 00009 (`bb5c5fb`), health 200 both URLs, 401 on a bogus token, zero errors; `backend-drift.yml` posted its first live comment on #38 (correct sha, diff and tag command) and the tag moved to `bb5c5fb` |
| 21 Sep | Whole-grid test on the validation tab (PR #40): sixth verdict check "Whole grid", section with the four p-values and the per-cell Romano–Wolf table; glossary entry | previewed on real AAPL/BABA payloads + a synthetic winner, 1280 + 375 px, both themes; prod bundle strings confirmed after merge; budget 8.7% headroom |
| 21 Sep | Trend label (PR #45): second regime axis, `down` / `flat` / `up` at ±1σ of the 60-day t-stat, crossed with vol into a 3 × 3 grid; open-questions §3 trend line closed with the finding that momentum's calm edge is not beta and its turbulent loss is chop | 662 tests; 6 mutation checks; not deployed — drift comment on #45 lists both un-deployed merges, tag target `e8b62e7` |
| 25 Sep | `cost_sensitivity` for portfolios: the book is affine in cost exactly as a single leg is — weights come off close returns, positions off closes, and nothing upstream of the weighted sum reads the cost — so the same bisection solves it. On every `/api/portfolio`; the existing card renders it unchanged | 723 tests; the affineness claim measured against the real `combine` (2e-17 on equal and inverse-vol) instead of argued from algebra; breakeven verified by re-POSTing it as `transaction_cost` and reading Sharpe off the response (-0.000000), every curve point bit-identical to a real re-run; 5 mutations, 4 caught, survivor shown unobservable |
| 24 Sep | Max-drawdown interval (§5, PR #51): `NO_BIAS_CORRECTION` — BCa's `z0` suppressed for `max_drawdown` and `calmar_ratio`, acceleration kept. The band was never too narrow (98% of the true central-95% range); `z0` was correcting a bias belonging to the block scheme, not the estimator, and is mostly noise (sd 0.44-0.63, mean ~0). `max_drawdown` left `UNDERSTATED`, and the coverage note under the grid was corrected with it | 702 tests at merge; 79% -> 95.0% coverage confirmed on three generators (Gaussian GARCH, GARCH t(5), Markov regime) and five real tickers; four-way term decomposition isolating z0 on identical replicates; 6 mutations, 1 survivor closed with an exact-identity test; open-questions §5 closed |
| 24 Sep | Transaction-cost realism (§7) closed by **not** shipping the vol-scaled model: the coefficient is unidentifiable from daily OHLCV, and the model's shape is worth a thirtieth of the cost level. `costs.py` ships the level instead — breakeven cost and headroom over the user's assumption, on every `/api/backtest` as `cost_sensitivity` | 717 tests; 9 mutations, 7 caught, one survivor proven equivalent (bit-identical on 40 pairs) and the other measured at 1.9e-12 in cost; negative control run on simulated bars with a CONSTANT spread — estimator slope 0.23-1.07 where truth is 0; shape-vs-level separated on 3 strategies x 8 tickers with total cost paid held equal; 4.6ms per call on 3,774 bars |
| 23 Sep | Sharpe-difference test (PR #48) and its UI (PR #49): `sharpe_test.py`, Ledoit-Wolf (2008) paired test of the strategy's Sharpe against buy-and-hold's — 1-D HAC by way of the scalar influence function, Bartlett kernel chosen so the variance cannot go negative and left unclamped so a broken kernel fails a test, headline p-value from a studentised block bootstrap; `BenchmarkTest.jsx` strips it under the headline metrics with the standard error given equal billing | 697 tests; 8 mutations, 7 caught and the survivor measured and documented (a studentised statistic barely notices an unpaired resample); size and power simulated on 500 GARCH paths; UI previewed on 5 real payloads at 1280 + 375 px, light + dark, every pair ≥ 4.83:1, bundle 8.4% headroom; open-questions §8 closed |
| 23 Sep | Regime direction table + vol × direction grid (PR #46), STATUS sync (PR #47) | previewed on real AAPL momentum/Bollinger full, stitched and 110-bar payloads; 375 px no overflow; renders only once rev 00010 ships the `trend` block |
| 23 Sep | **`backend-deployed` tag moved to `e8b62e7` while prod still served `bb5c5fb`** — the drift detector has been under-reporting since: its comment on #48 named only `da07ed5` and claimed prod was on `e8b62e7` | verified by `gcloud run services describe` (rev `00009-65g`) and a 404 from `POST /api/portfolio/validate` on prod |
| 21 Sep | Validation tab in portfolio mode (PR #43): same verdict card, walk-forward gains a per-name table (weight, tuned vs unseen Sharpe), timing test gains a per-name table and explains the independent-leg null; "holding the basket" wording; STATUS sync (PR #42) | previewed on real AAPL+MSFT+GOOGL Bollinger + momentum payloads, 1280 + 375 px, no overflow; budget 8.6% headroom; prod chunk `DashboardPage-DuW21dRS.js` carries the strings; route 404s on prod until the backend deploys |
| 21 Sep | Basket validation (PR #41): `portfolio_validation.py`, `POST /api/portfolio/validate`, null decided and recorded; write-up gains the basket table | 641 tests; 4 mutation checks; not yet deployed (no caller), drift comment posted on #41 |
| 20 Sep | Runtime SA rotated: `finertia-api-runtime` (no project roles, `secretAccessor` on `finertia-sa` only) replaces the default compute SA (`roles/editor`); rev 00008, same image; default SA's secret grant removed; `--service-account` added to README + deploy.yml | health 200 via proxy and direct; bogus bearer → 401 "Invalid token" (Admin SDK initialised under the new SA); zero ERROR logs on 00008 |
| 19 Sep | **Simplification**, user's call after reading the site as a customer: tweakcn Ocean Breeze palette + DM Sans (PR #19, contrast re-measured ≥ 4.5:1); notebook metaphor dropped — stamps → Badge, no pencil underlines, no graph paper (PR #20); set-up = strategy/ticker/dates + one Advanced fold, results = 4 numbers + curve + one fold (PR #21); signed-in users no longer sent to /register (PR #22, bug found on prod); landing rewritten for someone who has never heard of a backtest (PR #23) | each PR previewed on the real payload at 375 + 528/1280 px, light + dark; prod title + bundle strings confirmed after merge |
| 16 Sep | Rolling walk-forward (`rolling.py`): 4 anchored folds, market context per fold, stitched OOS + CI, parameter stability; wired as `rolling_walk_forward` in `/api/validate`; PR #10, rev 00006 | 18 + 3 tests, 588 total; 3 mutation checks; all three AAPL strategies read `regime_dependent` |
| 24 Sep | UI fixes (PR #53): FastAPI's array-shaped 422 `detail` rendered as `[object Object]` — now the backend's own messages reach the screen; switching to portfolio mode no longer crashes results. Cost-tolerance strip (PR #54): breakeven cost beside the assumed one, headroom multiple, metrics at 0×–5× | both bugs reported from a live session; strip reads `cost_sensitivity`, waited on rev 00010 |
| 23 Sep | STATUS sync after #49 (PR #50) recorded the lying tag; the tag was reset to `bb5c5fb` after it | `git rev-parse backend-deployed` = `bb5c5fb` on 28 Sep, matching rev 00009 |
| 28 Sep | **Rev `00010-rdj` deployed from `8d2a866`** (manual `gcloud run deploy`, README flags; the Deploy workflow has never run — no WIF secrets on the repo). First attempt from the user's terminal never reached Cloud Build; second run from the session. Tag moved `bb5c5fb` → `8d2a866`, drift now zero | 723 tests green before deploy; revision serving 100%; `/api/health` 200 via the proxy; `POST /api/portfolio/validate` 404 → 422 through `finertia.hulage.in`; service config (runtime SA, `finertia-sa` secret, `ALLOWED_ORIGINS`, `LOG_LEVEL`, caps) diffed unchanged before the deploy. New panels **not** yet seen on a logged-in run |
| 28 Sep | **Deploy workflow live** — Workload Identity Federation: `finertia-deployer` SA (run.admin, cloudbuild.builds.editor, artifactregistry.writer, storage.admin, serviceUsageConsumer; actAs on `finertia-api-runtime` and the Cloud Build compute SA only), pool/provider `github` accepting only `hulagerushikesh/Finertia` on `refs/heads/main`, secrets `GCP_WORKLOAD_IDENTITY_PROVIDER` / `GCP_SERVICE_ACCOUNT`; setup in `.github/scripts/setup-wif.sh`. First run failed at the build (deployer lacked actAs on the compute SA Cloud Build runs as) — binding added, script updated | run 36444594928 green: tests → rev `00011-cwn` 100% traffic as `finertia-api-runtime` → `/api/health` 200 via the proxy → `backend-deployed` moved to `26a6a10` by the workflow itself; `POST /api/portfolio/validate` 422 through `finertia.hulage.in`; re-run of the failed 36444541475 → rev `00012-7zc`, dispatches 36445752188, 36445780974, 36447370616 → revs `00013-7xd`, `00014-5g2`, `00015-z4f`, all green, identical code |
| 28 Sep | Contribution colour (PR #58): `PortfolioLegs` coloured the best leg green and the worst red whatever their sign — AAPL's −32.91% showed green beside MSFT's −41.67% because it was the smaller loss. Colour is now the sign; best/worst keep the bolder weight | found on the user's production portfolio run; frontend build + bundle budget pass |
| 7 Oct | **Write-up published** at `/writeup` (#60, #61): every figure re-run through the real route handlers by `backend/scripts/reproduce_writeup.py` (174 checks); the page renders `planning/write-up.md` itself, so it cannot drift. Share card `og-writeup.png` served to crawlers from a build-emitted `writeup.html` (#62) | 174/174 figures match; local prod build serves `og-writeup.png` on `/writeup`, `og.png` elsewhere |
| 7 Oct | `/demo` Validation tab (#63): the demo config's real `/api/validate` response, frozen by `scripts/freeze_demo_validation.py` — failed, 2 of 6 checks, IS 0.75 → OOS −0.03. README demo GIF (`docs/demo.gif`, 3.3 MB, 24 s) | desktop + 375 px dark: no overflow, no console errors; bundle budget 4.6% headroom |
| 7 Oct | Phase 3 kit (#64): `planning/feedback.md` + read-only `scripts/usage_counts.py` | first count: 1 sign-up, 21 saved runs, all the author's |
| 7 Oct | **Rev `00017-jq8`** — admin Pro grant (#68): Give / Remove Pro on Admin → Users; the server accepts only `free` / `pro` and stamps `planSource: "admin"` (the Stripe webhook stamps `"stripe"`), so `usage_counts.py` splits paid from comped. Firestore rules unchanged: clients still cannot write `plan` | 4 new tests, 727 green, mutation-checked; run 37577534153 green; unauthenticated `PATCH` on the live route 401. Button not yet clicked on prod (needs the admin login) |
| 7 Oct | CI deprecations (#69): `google-github-actions/auth` + `setup-gcloud` v2 → v3 (Node 24); every job pinned to `ubuntu-24.04` ahead of `ubuntu-latest` → 26.04 on 19 Oct | run 37578295198 → rev `00018-ml7` green, no deprecation annotations |

## Known risks

1. **yfinance in production** — mitigated since rev 00004: Firestore cache
   survives cold starts, stale-on-error serves the last good copy. Residual: a
   never-seen ticker during a Yahoo outage still 503s. Measured 7 Oct
   (AAPL momentum 2020–2024, logged in): **cold 11.4 s** = ~6.9 s instance start
   + 4.7 s handler (1.2 s of it compute); **warm 2.4 s** handler, 0.3 s compute.
   The ~2 s outside compute is price-cache read + auth + saving the run; the
   cache read is not logged on its own, so it cannot be split further.
2. **Backend redeploy is a manual trigger** and was forgotten once (5 days of stale prod). Since 28 Sep it is one command — `gh workflow run deploy.yml --ref main` — which tests, deploys, health-checks and moves the `backend-deployed` tag itself, so the tag can no longer be moved without a deploy behind it (the 23 Sep failure). `backend-drift.yml` still comments on any merged PR that leaves `backend/` ahead of the tag. Still not push-triggered, deliberately: a deploy stays a decision. Hand-deploys (README fallback) must still move the tag only after the revision serves and `/api/health` returns 200.
3. **Shared python** — local pandas 2.3.1 vs prod 3.0.5; suite passes on both today.
4. **`gh` token** still account-wide `repo` + `workflow`, no expiry.
5. **Rollback target is rev `00016-rzn`** (the code before #68, same as 00010–00015; `00009-65g` is the one before the six rev-00010 PRs) — both run as `finertia-api-runtime`, so a traffic shift works: `gcloud run services update-traffic finertia-api --region asia-south1 --project momentbacktracking --to-revisions finertia-api-00016-rzn=100`. **Rollback to rev 00007 no longer works by traffic shift** — that revision runs as the default compute SA, which lost its secret grant on 20 Sep. Rolling back means redeploying the 00007 source with `--service-account finertia-api-runtime@…`, or re-granting the secret first.
