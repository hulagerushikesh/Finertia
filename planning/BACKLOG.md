# Backlog

Everything not in the current milestone. "Evidence" = what would prove it done.

## Small and unblocked

- [ ] Narrow the `gh` token → in M9 phase 0
- [ ] Project venv → in M9 phase 0
- [ ] Bundle-size CI check: fail the frontend build if entry JS grows > 10% (would have caught the redesign regression automatically)
- [ ] Backend deploy reminder: a CI job on `main` that diffs `backend/` against the last deployed SHA and comments "backend changed, redeploy" on the merge (fixes the forgotten-redeploy failure mode without automating a cost)
- [ ] Rotate the Cloud Run runtime SA to a dedicated one (currently the default compute SA)

## Research (after effective N)

- [ ] Portfolio-level validation — needs a definition of a portfolio permutation first (open-questions §2)
- [ ] Regime-aware walk-forward: anchored multi-split; per-year OOS; realised-vol tercile labels (§3)
- [ ] Whole-grid inference: White Reality Check / Hansen SPA / Romano-Wolf stepdown (§4)
- [ ] Max-drawdown interval with honest coverage (§5)
- [ ] Vol-scaled transaction-cost model (§7)
- [ ] Ledoit-Wolf test for strategy-vs-benchmark Sharpe difference — the "does it beat buy-and-hold" question with a p-value

## Product (only if Phase 4 picks "product")

- [ ] Wire Stripe: keys + `STRIPE_WEBHOOK_SECRET` on Cloud Run; never without the secret
- [ ] Sentry DSN (env-gated; unset = SDK never imported)
- [ ] Support inbox that a human reads
- [ ] Admin stats via counters / aggregation queries instead of collection scans (defer until it hurts)
- [ ] Email notifications for long validation runs
- [ ] Intraday bars (needs a paid data source)

## Portfolio / write-up (if Phase 4 picks "portfolio")

- [ ] 1,500-word write-up: the walk-forward table, the DSR random-walk table, the bootstrap headline (Sharpe 0.39, CI −0.39 to 1.29), what each method catches that the others miss
- [ ] Put the write-up on hulage.in and link it from the README and the landing page
- [ ] Short demo GIF of `/demo` → validation tab for the README

## Docs

- [ ] README "Deploy" section still describes Firebase Hosting; production is Vercel + Cloud Run — rewrite to match STATUS.md
- [ ] README route count and test count are stale (say 16 routes, 535 tests)
- [ ] Retire or refresh the four stale artifacts in artifacts.md

## Done (moved from earlier lists, kept for the record)

- [x] S1 smoke test on live · [x] Docker image built · [x] GCP billing · [x] `VITE_SUPPORT_EMAIL` · [x] GitHub secret scanning + push protection · [x] walk-forward finding in README · [x] DSR · [x] PBO · [x] purge/embargo · [x] bootstrap CIs · [x] `.gcloudignore` · [x] requirements pinned
