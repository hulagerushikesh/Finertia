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

### Phase 2 — Price data that survives (week 2)

- [ ] Persistent read-through cache in Firestore: `prices/{TICKER}_{YEAR}` docs
  holding the year's closes (~252 floats — tiny). Admin SDK is already wired;
  no new infra, no new cost line.
- [ ] `data.py`: serve from Firestore for complete past years; hit yfinance only
  for missing years and the current partial year; keep the in-memory dict as L1.
- [ ] **Stale-on-error**: if yfinance fails and the cache has the range, serve
  it and flag `data_source: "cache"` in the response.
- [ ] Pre-warm the demo tickers (AAPL + the curated autocomplete list) with a
  one-off script.
- [ ] Tests: cache hit/miss/partial-year, stale-on-error, and a subprocess test
  that the L1 dict really is per-process.
- [ ] Measure cold-start backtest latency before/after; put both numbers in the PR.

**Exit:** with yfinance mocked to 429, `/demo` and a cached-ticker backtest
still return; latency numbers recorded.

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
