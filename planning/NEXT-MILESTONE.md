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

- [ ] Project venv: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && python -m pytest -q` → 535 on pandas 3.0.5, same as prod.
- [ ] Narrow the `gh` token to a fine-grained PAT scoped to `hulagerushikesh/Finertia`. Verify with `gh auth status`.
- [ ] Add `learning/` and `planning/` to the repo (this PR).

**Exit:** local suite matches prod's pins; `gh auth status` shows a scoped token.

### Phase 1 — Land the redesign (week 1)

The branch reverses the 22 Aug "no shadcn" decision. That is fine — the
decision is logged with the reason in DECISIONS.md — but it must clear the same
bars the old UI cleared, or it is a regression wearing new clothes.

- [ ] **Commit the WIP** in reviewable slices on `redesign`: (1) token sheet +
  tailwind config, (2) `components/ui/*` + `lib/utils`, (3) charts + `chartTheme`,
  (4) pages, (5) package changes. No single 3,664-line commit.
- [ ] **Bundle audit.** Entry is 764 kB vs 464 kB before. Network-trace the
  landing page; confirm recharts is not in the entry graph via `chartTheme`.
  Target: landing JS ≤ 500 kB gzip-equivalent to before. Fix by moving chart
  theme constants out of any module the entry imports, not by `manualChunks`
  (see learning/02 §E for why that backfires).
- [ ] **Verification checklist** — the bars the old UI passed, re-run on the new one:
  - text ≥ 4.5:1 on every surface, both themes, measured numerically
  - `:focus-visible` outline global; `prefers-reduced-motion` honoured (motion lib included)
  - tooltips open on touch (sonner/radix Tooltip ≠ `title=`)
  - hit targets ≥ 24 px fine / 44 px coarse, no overlapping pairs at 375 px
  - 375 px: zero horizontal overflow on all 7 public routes
  - dashboard results column at ~650 px (1024 − sidebar): no label collisions
  - exactly one `<main>`; h1/h2/h3 outline intact
  - dark theme correct for both the explicit toggle and system preference
- [ ] **PR** `redesign → main`, CI green, screenshots of the checklist in the PR body.
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
- [x] PR #7 merged; rev 00004 (then 00005). Prod cold-read latency still unmeasured — needs one logged-in run from `/dashboard` (the `/demo` page never calls the API).
- [ ] "Served from cache" note in the UI — on the `redesign` branch (DashboardPage would conflict on `main`).
- Option, not taken: a second named Firestore DB in `asia-south1` for `prices` (not free-tier; ≈₹0 in practice) if the latency ever matters.

**Exit:** with yfinance mocked to 429, a cached-ticker backtest still returns (test) — met. Latency recorded — met, unflattering.

### Phase 3 — Effective N — BUILT, PR open

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
- [ ] `ValidationPanel.jsx`: raw vs effective side by side — on the `redesign` branch with the cache note.

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
  route on the redesign branch). Not before the Pitch Fest result.

**Exit:** DECISIONS.md has an entry; if portfolio path, the write-up is drafted
in `planning/` or published. **Met** (drafted; publishing waits on the result).

## Definition of done for M9

- [x] Phase 0–3 exit criteria met (phase 0's `gh` token narrowing still on the user)
- [x] STATUS.md refreshed: rev 00005, 567 tests, roadmap 5/5, redesign dated (PR #6, held)
- [ ] Build-ledger artifact refreshed from STATUS.md
- [x] Phase 4 decision recorded (15 Sep)

## Explicitly not in M9

Stripe go-live · Sentry DSN · portfolio-mode validation · regime-aware
walk-forward · admin counters · whole-grid SPA/Reality Check. All in BACKLOG.md.
