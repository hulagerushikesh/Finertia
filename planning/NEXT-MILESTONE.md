# Next milestone — M9: "Land the redesign, close the roadmap, make data survive"

_Drafted 14 Sep 2026. Target: ~3 weeks part-time. Previous milestone (M8, deploy +
submit + bootstrap CIs + redeploy hygiene) closed 13 Sep._

## Why this milestone

Three things are true today:

1. A full UI rebuild sits uncommitted on `redesign` — 45 files, builds clean,
   verified nowhere. Unmerged work rots; this is the largest risk to the codebase.
2. The research roadmap is 4 of 5. The last item (effective N) is the one that
   decides whether the DSR is calling real edges noise.
3. The live demo depends on yfinance with a cache that dies on every cold start.
   That is the most likely way the product fails in front of a judge or a hirer.

Everything else in the backlog is optional until these three are settled.

## Constraint that orders everything

**`main` auto-deploys the judged site.** Until the Pitch Fest result is in,
nothing merges to `main` that changes what a judge sees. Backend work merges
to `main` freely (no auto-deploy) but is *not* redeployed until the result.
Frontend work stays on its branch until then.

## Phases, in order

### Phase 0 — Hygiene (1 hour, day 1)

- [x] Project venv — `backend/.venv`, pandas 3.0.5 / numpy 2.4.6 / fastapi 0.141.1, 535 pass (14 Sep).
- [ ] Narrow the `gh` token — a fine-grained PAT (`github_pat_…`) over the 6 active repos; `gh auth status` still shows the `gho_` token with `repo, workflow` as of 14 Sep. `echo TOKEN | gh auth login --with-token`.
- [x] Add `learning/` and `planning/` to the repo — PR #5, merged 14 Sep.

**Exit:** local suite matches prod's pins; `gh auth status` shows a scoped token.

### Phase 1 — Land the redesign (week 1)

The branch reverses the 22 Aug "no shadcn" decision. That is fine — the
decision is logged with the reason in DECISIONS.md — but it must clear the same
bars the old UI cleared, or it is a regression wearing new clothes.

- [x] **Commit the WIP** in reviewable slices — 5 commits, tokens → primitives → charts → panels → shell/pages (14 Sep).
- [x] **Bundle audit.** recharts was never in the entry — the growth was motion
  + radix + sonner + tailwind-merge. LazyMotion/domAnimation and
  `firebase/firestore/lite` took the entry from 746/221 to 521/162 (raw/gz kB).
  Landing total 196 gz vs 169 on main; the rest is the price of radix.
- [ ] **Verification checklist** — the bars the old UI passed, re-run on the new one:
  - [x] text ≥ 4.5:1 on every surface, both themes, measured — 4 light tokens + dark faint fixed; min now 4.58
  - [x] `:focus-visible` outline global; `prefers-reduced-motion` in CSS and every `m.*`/Recharts animation
  - [x] tooltips open on touch — radix Popover on click, verified on `/demo`
  - [x] hit targets: `.tap-safe` 24/44 intact, 0 overlapping pairs at either size, 375 px
  - [x] 375 px: zero horizontal overflow on all 9 public routes
  - [x] `/demo` at 650 / 1024 / 1280: no clipped or colliding labels
  - [ ] **Dashboard proper at ~650 px — needs a login on the Vercel preview (you)**
  - [x] exactly one `<main>`, one h1 per route, zero `title=`
  - [x] theme toggle + `finertia-theme` persistence + pre-mount paint script
- [x] **PR** `redesign → main` — see STATUS.md for the evidence list.
- [ ] **Your smoke test — now on production:** login → dashboard at 1024 px → run → History → Profile displayName save → Register a throwaway (exercises every firestore/lite call).
- [x] **Merged 17 Sep on explicit go-ahead** (`e10309b`), before the result. Frontend
  only — no backend redeploy needed. Override logged in DECISIONS.md.

**Exit:** PR open with every checklist line evidenced; bundle no larger than before.

### Phase 2 — Price data that survives — BUILT, PR #7 open

- [x] Persistent read-through cache in Firestore: `prices/{TICKER}_{YEAR}`, columnar. `backend/price_store.py` + `backend/data.py`.
- [x] Correctness rule that surfaced while designing: yfinance adjusts as of fetch date, so every cached year of a ticker must come from ONE download — any miss/stale refetches the whole ticker history under a new batch id; reads require a uniform batch. Pinned by test.
- [x] Stale-on-error → `data_source: "cache-stale"`; nothing cached + Yahoo down → 503 (was a misleading 400).
- [x] Pre-listing years stored as empty docs; current year expires after 6 h; past years never.
- [x] 17 tests, 552 total; two mutation checks each fail exactly one test.
- [x] Rules deny `prices` to clients — deployed 15 Sep, released ruleset byte-identical to the file.
- [x] Prewarm: 28/28 suggested tickers, 2015→today, ~300 docs. First real run of `FirestorePriceStore` — worked.
- [x] Latency measured (Mac in India → nam5): yfinance direct ~1.0 s; cache read 0.8–2.3 s. **A wash, not a win** — Firestore is in `nam5`, Cloud Run in `asia-south1`, both cross-continent. The PR buys resilience and zero rate-limit exposure on cold starts, not speed. Prod number after the Cloud Run deploy.
- [x] PR #7 merged; rev 00004 (then 00005). Prod cold-read latency still unmeasured — needs one logged-in run from `/dashboard` (the `/demo` page never calls the API).
- [x] "Served from cache" note in the UI — PR #13, merged 19 Sep.
- Option, not taken: a second named Firestore DB in `asia-south1` for `prices` (not free-tier; ≈₹0 in practice) if the latency ever matters.

**Exit:** with yfinance mocked to 429, a cached-ticker backtest still returns (test) — met. Latency recorded — met, unflattering.

### Phase 3 — Effective N — DONE

Roadmap 5 of 5. `backend/trials.py`; wired into `walk_forward` as `deflated.effective_trials`.

- [x] Correlation matrix from the in-sample candidate returns the sweep already builds.
- [x] Eigenvalue estimate (Li & Ji 2005).
- [x] Clustering estimate (LdP & Lewis 2019) — hand-written average linkage + silhouette; cluster spread only from K ≥ 3; one-blob fallback when silhouette finds nothing but every ρ > 0.875.
- [x] `deflated_sharpe_ratio` takes `n_trials_effective` + `trial_sharpes_effective`; response carries `under_raw / under_eigen / under_clusters / under_effective`, `n_trials_effective`, `n_trials_lower_bound`, `dsr_gap`.
- [x] **Headline = the larger estimate** — lowering N flatters; pinned by test.
- [x] 15 tests, 567 total; three mutation checks (min-for-max, drop one-blob, drop eigen fractional term) each fail exactly one test.
- [x] Canonical AAPL 2018→2024-01-01: momentum 16→6 (3), MACD 4→2, Bollinger 12→7 (2). DSR +0.07…+0.12. No verdict changes.
- [x] **Found while measuring:** the walk-forward verdict flips when the window extends one year (split Feb→Oct 2022). README now states the window and the flip; open-questions §3 promoted to the top research item.
- [x] Merged; Cloud Run rev 00005 serving, health 200, no warnings (15 Sep).
- [x] `ValidationPanel.jsx`: raw vs effective side by side — PR #13, merged 19 Sep.

### Phase 4 — Decide what Finertia is for (end of milestone)

Not a task; a written decision. Inputs: the Pitch Fest result, and whether
anyone other than the author has used it.

| Path | Needs | Cost |
|---|---|---|
| **Portfolio piece + write-up** (recommended) | live URL ✓, README ✓, a 1,500-word write-up of the walk-forward + bootstrap finding | ~2 days |
| Product | Stripe live, a support inbox someone reads, a business entity for payouts, ongoing ₹ | open-ended |

Recommendation: portfolio path. There is no funding and no second person to
answer support email. The write-up is the highest-leverage remaining artefact:
it turns "I built a backtester" into "I found that the best in-sample strategy
was the worst out-of-sample one, and here is the statistics that proves it".
Record the outcome in DECISIONS.md.

- [x] **Decided 15 Sep: portfolio path.** DECISIONS.md entry with inputs and
  what would reverse it. Pitch Fest result still pending — it is a possible
  reversal input, not a blocker.
- [x] Write-up drafted: `planning/write-up.md`, ~1,550 words, every figure
  re-run on 15 Sep on both windows (2024-01-01 and 2025-01-01) including the
  per-check disagreement (DSR/PBO/permutation vs walk-forward) and bootstrap
  intervals on the OOS Sharpes.
- [ ] Publish: README link + a home for it (hulage.in post, or a `/writeup`
  route off `main`). Not before the Pitch Fest result.

**Exit:** DECISIONS.md has an entry; if portfolio path, the write-up is drafted
in `planning/` or published. **Met** (drafted; publishing waits on the result).

## Definition of done for M9

- [x] Phase 0–3 exit criteria met (phase 0's `gh` token narrowing still on the user)
- [x] STATUS.md refreshed: rev 00007, 603 tests, roadmap 5/5, redesign merged 17 Sep (PR #6)
- [ ] Build-ledger artifact refreshed from STATUS.md
- [x] Phase 4 decision recorded (15 Sep)

## Explicitly not in M9

Stripe go-live · Sentry DSN · portfolio-mode validation · regime-aware
walk-forward · admin counters · whole-grid SPA/Reality Check. All in BACKLOG.md.
