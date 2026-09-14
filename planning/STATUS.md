# Status

_Current to `2093040` (main) + branch `redesign` · 14 Sep 2026._

## At a glance

| | |
|---|---|
| Live | https://finertia.hulage.in — Vercel (frontend) + Cloud Run `finertia-api` asia-south1 rev `00003` |
| Judged link | https://finertia.hulage.in/demo — Builders Pitch Fest 2026, BFSI, submitted 6 Sep; result pending |
| Tests | 535 backend (`cd backend && pytest tests/ -q`), 20 Firestore-rule (`cd firestore-tests && npm test`) |
| CI | green on `main` (backend tests + frontend build + secret scan) |
| Commits | 22 on main · 4 PRs merged |
| API | 16 routes |
| Cost | ₹0 idle (`min-instances 0`, max 2, 512Mi) |
| Blocked on user | 0 items |
| In flight | `redesign` branch — shadcn "Blue pencil" UI rebuild, committed in 5 slices + 3 fixes, PR open, **merge held until the Pitch Fest result** (see below) |

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

## Research roadmap — 4 of 5

| Item | State | Evidence |
|---|---|---|
| Deflated Sharpe Ratio | Done `4ad1b0c` | 36 tests; reproduces paper's 3.26; Lo (2002) to 1e-12 |
| PBO via CSCV | Done `52217af` | 21 tests; regime-blindness pinned by test |
| Purge + embargo | Done `e840a3c` | 20 tests; boundary trade measured at 33 bars |
| Block-bootstrap CIs | Done `7b178ca` PR #1 | 54 tests; coverage measured on 300 GARCH paths; serving since rev 00003 |
| Effective N of the grid | **Open** | Documented limitation, unquantified — see NEXT-MILESTONE |

## The redesign branch (PR open, merge held)

Five slices (tokens → primitives → charts → panels → shell/pages) plus three
fixes found while landing it. Adds radix-ui, motion, sonner, next-themes,
lucide, cva. `Toast.jsx` replaced by sonner. Reverses the 22 Aug "no shadcn"
decision — logged in DECISIONS.md.

**Verified (14 Sep, dev server, measured not eyeballed):**
- Contrast: every text node on 9 public routes × 2 themes ≥ 4.5:1 (min 4.58).
  Four light tokens had to move (faint 3.19 → 4.7, gain, loss, warn); dark
  faint 4.24 → 4.6.
- 375 px: zero horizontal overflow on all 9 routes.
- Exactly one `<main>`, one `h1` per route, zero `title=` attributes.
- Metric tooltips are radix Popovers: open on click/tap, verified; `.tap-safe`
  intact, 0 overlapping pairs at 24 px and at 44 px on `/demo` at 375 px.
- `/demo` at 650 / 1024 / 1280 px: no clipped or overlapping metric labels.
- Mobile Sheet nav opens, closes on route change; theme toggle persists.
- Bundle: entry was 746 kB raw / 221 gz (main: 480 / 135). LazyMotion +
  `firebase/firestore/lite` → **521 / 162**. Landing total incl. the
  preloaded firebase chunk: 196 gz vs 169 on main. The remaining +27 gz is
  radix + sonner + tailwind-merge.

**Not verified — needs a login on the Vercel preview:** Dashboard at the
~650 px results column, History, Profile (`displayName` save exercises
firestore/lite `updateDoc`), Register (`setDoc` + `serverTimestamp`).

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
| 14 Sep | `learning/` + `planning/` (PR #5); venv on prod pins (535 pass); redesign sliced into commits, bundle −59 kB gz, contrast floors restored, canonical fixed | measured, see above |

## Known risks

1. **yfinance in production** — rate limits, schema changes, and an in-memory
   cache that is cold on every scale-from-zero. No fallback. The single most
   likely way the live demo breaks in front of someone.
2. **Backend redeploy is manual** and was forgotten once (5 days of stale prod).
3. ~~Shared python~~ — `backend/.venv` on prod pins since 14 Sep; 535 pass.
4. **`gh` token** still account-wide `repo` + `workflow`, no expiry.
