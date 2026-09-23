# Status

_Current to `e8b62e7` (main) · 21 Sep 2026._

## At a glance

| | |
|---|---|
| Live | https://finertia.hulage.in — Vercel (frontend) + Cloud Run `finertia-api` asia-south1 rev `00009` (20 Sep: whole-grid inference, built from `bb5c5fb`, runs as `finertia-api-runtime`) — **`backend/` on `main` is ahead by two merges (#41 basket validation, #45 trend label; drift comments posted on both) — the frontend calls the basket route since #43, so the portfolio-mode Validation tab 404s on prod until rev `00010` ships**; frontend = the shadcn redesign since 17 Sep (PR #6), plus the 19 Sep UI batch (PRs #13, #14, #16, #17) and the same-day simplification (PRs #19–#23: Ocean Breeze theme, plain shadcn surfaces, folded set-up/results, signed-in CTA fix, newcomer landing) |
| Judged link | https://finertia.hulage.in/demo — Builders Pitch Fest 2026, BFSI, submitted 6 Sep; result pending |
| Tests | 662 backend (`cd backend && pytest tests/ -q`), 20 Firestore-rule (`cd firestore-tests && npm test`) |
| CI | green on `main` (backend tests + frontend build + bundle budget + secret scan); `backend-drift.yml` comments on the merged PR when `backend/` is ahead of the `backend-deployed` tag |
| Commits | 122 on main (`git rev-list --count`, counted 21 Sep) · 44 PRs merged (`gh pr list --state merged`) |
| API | 17 routes |
| Cost | ₹0 idle (`min-instances 0`, max 2, 512Mi) |
| Blocked on user | 4 — **backend deploy of `e8b62e7` (rev 00010) + tag move**, without which the basket Validate button 404s · login smoke test **on production** · one logged-in `/dashboard` AAPL run for the prod cache latency · `gh` fine-grained PAT |
| In flight | PR #46 — direction table + vol × direction grid on `RegimeTable.jsx` (frontend, reads `regimes.trend` / `regimes.joint`) |
| Direction | **Portfolio piece + write-up** (decided 15 Sep, DECISIONS.md); draft at [write-up.md](write-up.md) |

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

## Research roadmap — 5 of 5, plus three post-roadmap

| Item | State | Evidence |
|---|---|---|
| Deflated Sharpe Ratio | Done `4ad1b0c` | 36 tests; reproduces paper's 3.26; Lo (2002) to 1e-12 |
| PBO via CSCV | Done `52217af` | 21 tests; regime-blindness pinned by test |
| Purge + embargo | Done `e840a3c` | 20 tests; boundary trade measured at 33 bars |
| Block-bootstrap CIs | Done `7b178ca` PR #1 | 54 tests; coverage measured on 300 GARCH paths; serving since rev 00003 |
| Effective N of the grid | Done PR #8 | 15 tests; eigen + clusters, headline = larger; canonical AAPL 16→6 / 4→2 / 12→7; mutation-checked |
| Trend label beside vol (post-roadmap, open-questions §3) | Done 21 Sep | `label_trend` / `trend_breakdown` / `joint_breakdown` in `regimes.py`: ±1σ t-stat of the 60-day mean return (fixed cut, DECISIONS 21 Sep), 3 × 3 vol × trend grid in every `regimes` block; 21 tests, 6 mutations caught; AAPL OOS momentum calm-flat 2.40 vs calm-rising 2.29 (calm edge is not beta), turbulent-flat −1.88 vs turbulent-rising +1.29 (the loss is chop) |
| Basket validation (post-roadmap, open-questions §2) | Done 21 Sep | `portfolio_validation.py` + `POST /api/portfolio/validate`: grid scored on the book, every leg re-timed independently (null decided, DECISIONS 21 Sep); 21 tests, 4 mutations caught; one-leg book == single-ticker bit for bit; AAPL+MSFT+GOOGL Bollinger held up 0.83→0.77, timing p 0.002, still −18.7%/yr vs holding the basket |
| Whole-grid inference (post-roadmap, open-questions §4) | Done 20 Sep | `snooping.py`: Reality Check, SPA l/c/u, Romano-Wolf stepdown vs buy-and-hold; 17 tests, 6 mutations caught; 0 survivors on 5 tickers × 2 windows × 3 grids; snooping gap printed per cell |

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
| 21 Sep | Validation tab in portfolio mode (PR #43): same verdict card, walk-forward gains a per-name table (weight, tuned vs unseen Sharpe), timing test gains a per-name table and explains the independent-leg null; "holding the basket" wording; STATUS sync (PR #42) | previewed on real AAPL+MSFT+GOOGL Bollinger + momentum payloads, 1280 + 375 px, no overflow; budget 8.6% headroom; prod chunk `DashboardPage-DuW21dRS.js` carries the strings; route 404s on prod until the backend deploys |
| 21 Sep | Basket validation (PR #41): `portfolio_validation.py`, `POST /api/portfolio/validate`, null decided and recorded; write-up gains the basket table | 641 tests; 4 mutation checks; not yet deployed (no caller), drift comment posted on #41 |
| 20 Sep | Runtime SA rotated: `finertia-api-runtime` (no project roles, `secretAccessor` on `finertia-sa` only) replaces the default compute SA (`roles/editor`); rev 00008, same image; default SA's secret grant removed; `--service-account` added to README + deploy.yml | health 200 via proxy and direct; bogus bearer → 401 "Invalid token" (Admin SDK initialised under the new SA); zero ERROR logs on 00008 |
| 19 Sep | **Simplification**, user's call after reading the site as a customer: tweakcn Ocean Breeze palette + DM Sans (PR #19, contrast re-measured ≥ 4.5:1); notebook metaphor dropped — stamps → Badge, no pencil underlines, no graph paper (PR #20); set-up = strategy/ticker/dates + one Advanced fold, results = 4 numbers + curve + one fold (PR #21); signed-in users no longer sent to /register (PR #22, bug found on prod); landing rewritten for someone who has never heard of a backtest (PR #23) | each PR previewed on the real payload at 375 + 528/1280 px, light + dark; prod title + bundle strings confirmed after merge |
| 16 Sep | Rolling walk-forward (`rolling.py`): 4 anchored folds, market context per fold, stitched OOS + CI, parameter stability; wired as `rolling_walk_forward` in `/api/validate`; PR #10, rev 00006 | 18 + 3 tests, 588 total; 3 mutation checks; all three AAPL strategies read `regime_dependent` |

## Known risks

1. **yfinance in production** — mitigated since rev 00004: Firestore cache
   survives cold starts, stale-on-error serves the last good copy. Residual: a
   never-seen ticker during a Yahoo outage still 503s; prod cold-read latency
   still unmeasured.
2. **Backend redeploy is manual** and was forgotten once (5 days of stale prod). Since 20 Sep `backend-drift.yml` comments on the merged PR whenever `backend/` is ahead of the `backend-deployed` tag (PR #34); first live comment on PR #38 the same day, redeploy followed within the hour.
3. **Shared python** — local pandas 2.3.1 vs prod 3.0.5; suite passes on both today.
4. **`gh` token** still account-wide `repo` + `workflow`, no expiry.
5. **Rollback to rev 00007 no longer works by traffic shift** — that revision runs as the default compute SA, which lost its secret grant on 20 Sep. Rolling back means redeploying the 00007 source with `--service-account finertia-api-runtime@…`, or re-granting the secret first.
