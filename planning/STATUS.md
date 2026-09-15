# Status

_Current to `ac0ca6f` (main) · 14 Sep 2026._

## At a glance

| | |
|---|---|
| Live | https://finertia.hulage.in — Vercel (frontend) + Cloud Run `finertia-api` asia-south1 rev `00005` (15 Sep: price cache + effective N) |
| Judged link | https://finertia.hulage.in/demo — Builders Pitch Fest 2026, BFSI, submitted 6 Sep; result pending |
| Tests | 567 backend (`cd backend && pytest tests/ -q`), 20 Firestore-rule (`cd firestore-tests && npm test`) |
| CI | green on `main` (backend tests + frontend build + secret scan) |
| Commits | 22 on main · 4 PRs merged |
| API | 16 routes |
| Cost | ₹0 idle (`min-instances 0`, max 2, 512Mi) |
| Blocked on user | 0 items |
| In flight | `redesign` branch — shadcn "Blue pencil" UI rebuild, **45 files uncommitted**, builds clean (see below) |

## Stages — verified vs built

Verified = proven by something that would fail if it broke. Built = written and
compiles, never exercised end to end.

| Stage | State | Evidence |
|---|---|---|
| S1 Connect — Firebase end to end | **Verified** | 3 real AAPL runs on the live site before submission; rules diffed byte-identical against the released ruleset |
| S2 Harden — guards, validators, error paths | **Verified** | Route tests mutation-checked; Docker image built 3× by Cloud Build |
| S3 Deploy — Vercel + Cloud Run | **Verified** | Live since 6 Sep; same-origin `/api/*` proxy; secret in Secret Manager |
| S4 Deepen — analytics, comparison, permalinks | **Verified** | Walked through on live |
| S5 Strategies — MACD, Bollinger, risk overlays, portfolios | **Verified** | Walked through on live; 535 tests |
| S6 Billing — plans, quota, Stripe | Built | `plans.py` tested; Stripe env-gated and unset in prod, never exercised |
| S7 Ops — rate limit, JSON logs, CI | **Verified** | CI green; deps pinned to prod 13 Sep |
| S8 Grow — demo, docs, support, SEO, email verification | **Verified** | All public routes walked before submission |

## Research roadmap — 5 of 5

| Item | State | Evidence |
|---|---|---|
| Deflated Sharpe Ratio | Done `4ad1b0c` | 36 tests; reproduces paper's 3.26; Lo (2002) to 1e-12 |
| PBO via CSCV | Done `52217af` | 21 tests; regime-blindness pinned by test |
| Purge + embargo | Done `e840a3c` | 20 tests; boundary trade measured at 33 bars |
| Block-bootstrap CIs | Done `7b178ca` PR #1 | 54 tests; coverage measured on 300 GARCH paths; serving since rev 00003 |
| Effective N of the grid | Done PR #8 | 15 tests; eigen + clusters, headline = larger; canonical AAPL 16→6 / 4→2 / 12→7; mutation-checked |

## The redesign branch (in flight, uncommitted)

`git diff --stat` on `redesign`: 45 files, +3,664 / −2,959, plus 21 new
`components/ui/*` (shadcn), `lib/utils.js`, `ThemeToggle`, `motion.jsx`,
`ChartFrame`, `ChartTip`, `Prose`, `Stamp`, `Spinner`. `Toast.jsx` deleted in
favour of sonner. Adds radix-ui, motion, sonner, next-themes, lucide, cva.

- `npm run build` passes (3.5s).
- **Bundle regressed**: entry `index-*.js` is 764 kB (was 464 kB after the lazy
  split). `chartTheme-*.js` at 366 kB suggests recharts is being pulled by the
  theme module. Needs a network-trace check before merge.
- Nothing verified in a browser yet: contrast floors, `tap-safe`, touch
  tooltips, 375 px overflow, dark theme, the ~650 px dashboard column.
- Reverses the 22 Aug "no shadcn" decision — logged in DECISIONS.md.

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
| 14 Sep | `learning/` + `planning/` folders created | — |

## Known risks

1. **yfinance in production** — mitigated by PR #7 once deployed: Firestore
   cache survives cold starts, stale-on-error serves the last good copy.
   Residual: a never-seen ticker during a Yahoo outage still 503s.
2. **Backend redeploy is manual** and was forgotten once (5 days of stale prod).
3. **Shared python** — local pandas 2.3.1 vs prod 3.0.5; suite passes on both today.
4. **`gh` token** still account-wide `repo` + `workflow`, no expiry.
