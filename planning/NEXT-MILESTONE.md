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
- [ ] **Your smoke test on the Vercel preview:** login → dashboard at 1024 px → run → History → Profile displayName save → Register a throwaway (exercises every firestore/lite call).
- [ ] **Merge after the Pitch Fest result** (or on explicit go-ahead). Frontend
  only — no backend redeploy needed.

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
- [ ] Merge PR #7 → **manual Cloud Run redeploy** → record prod latency → re-run one live backtest and confirm `data_source` in the response.
- [ ] "Served from cache" note in the UI — on the `redesign` branch (DashboardPage would conflict on `main`).
- Option, not taken: a second named Firestore DB in `asia-south1` for `prices` (not free-tier; ≈₹0 in practice) if the latency ever matters.

**Exit:** with yfinance mocked to 429, a cached-ticker backtest still returns (test) — met. Latency recorded — met, unflattering.

### Phase 3 — Effective N (weeks 2–3, research, on a branch)

Roadmap item 5 of 5. See learning/research/open-questions.md §1.

- [ ] Build the candidate-return correlation matrix from the walk-forward sweep
  (already stored for CSCV — free).
- [ ] N_eff via eigenvalues (Nyholt 2004 / Li & Ji 2005) — first, because it is
  ~20 lines on data that exists.
- [ ] N_eff via correlation clustering (López de Prado & Lewis 2019) — second,
  as the comparison. Report both.
- [ ] `deflated.py` takes `n_trials`; response carries `n_trials_raw`,
  `n_trials_effective`, and DSR under each.
- [ ] Tests: identical candidates → N_eff ≈ 1; independent candidates → N_eff ≈ N;
  the canonical AAPL case's numbers pinned.
- [ ] `ValidationPanel.jsx`: show raw vs effective side by side — the gap *is*
  the finding.
- [ ] Merge to `main` (backend-only, no auto-deploy). **Redeploy Cloud Run by
  hand** — this is the step that was skipped last time. Confirm rev 00004 via
  `/api/health` and one live validation run.

**Exit:** roadmap 5/5; prod serves effective-N; learning/03 §3 updated.

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

**Exit:** DECISIONS.md has an entry; if portfolio path, the write-up is drafted
in `planning/` or published.

## Definition of done for M9

- [ ] Phase 0–3 exit criteria met
- [ ] STATUS.md refreshed: rev 00004, test count, roadmap 5/5, redesign merged or dated
- [ ] Build-ledger artifact refreshed from STATUS.md
- [ ] Phase 4 decision recorded

## Explicitly not in M9

Stripe go-live · Sentry DSN · portfolio-mode validation · regime-aware
walk-forward · admin counters · whole-grid SPA/Reality Check. All in BACKLOG.md.
