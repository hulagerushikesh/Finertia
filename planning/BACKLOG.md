# Backlog

Everything not in the current milestone. "Evidence" = what would prove it done.

## Small and unblocked

- [ ] Narrow the `gh` token → in M9 phase 0
- [x] Project venv → M9 phase 0, done 14 Sep
- [x] Bundle-size CI check — `frontend/scripts/check-bundle.mjs` + `bundle-budget.json`, gzip entry + total, limits ~10% over the 19 Sep build; CI step "Bundle budget" (19 Sep)
- [x] Backend deploy reminder — `backend-drift.yml` diffs `backend/` against the `backend-deployed` tag on every push to main and comments on the merged PR; deploy.yml moves the tag, manual deploys move it per README (19 Sep)
- [ ] Rotate the Cloud Run runtime SA to a dedicated one (currently the default compute SA)

## Research (after effective N)

- [ ] Portfolio-level validation — needs a definition of a portfolio permutation first (open-questions §2)
- [x] Regime-aware walk-forward — anchored rolling folds + realised-vol regime label, both 16 Sep (`rolling.py`, `regimes.py`, §3). Remaining, narrower: a trend/range label beside vol
- [ ] Whole-grid inference: White Reality Check / Hansen SPA / Romano-Wolf stepdown (§4)
- [ ] Max-drawdown interval with honest coverage (§5)
- [ ] Vol-scaled transaction-cost model (§7)
- [ ] Ledoit-Wolf test for strategy-vs-benchmark Sharpe difference — the "does it beat buy-and-hold" question with a p-value

## Product (parked — Phase 4 picked "portfolio"; reopen only on the reversal conditions in DECISIONS.md)

- [ ] Wire Stripe: keys + `STRIPE_WEBHOOK_SECRET` on Cloud Run; never without the secret
- [ ] Sentry DSN (env-gated; unset = SDK never imported)
- [ ] Support inbox that a human reads
- [ ] Admin stats via counters / aggregation queries instead of collection scans (defer until it hurts)
- [ ] Email notifications for long validation runs
- [ ] Intraday bars (needs a paid data source)

## Portfolio / write-up (Phase 4 picked "portfolio", 15 Sep)

- [x] 1,500-word write-up — drafted as `planning/write-up.md`: both windows, the per-check disagreement, bootstrap intervals on the OOS Sharpes
- [ ] Put the write-up on hulage.in (or a `/writeup` route) and link it from the README and the landing page — after the Pitch Fest result
- [ ] Short demo GIF of `/demo` → validation tab for the README

## Docs

- [x] README "Deploy" section rewritten for Vercel + Cloud Run (13 Sep)
- [x] README route and test counts — 16 routes, 603 tests (19 Sep)
- [ ] Retire or refresh the four stale artifacts in artifacts.md

## Done (moved from earlier lists, kept for the record)

- [x] S1 smoke test on live · [x] Docker image built · [x] GCP billing · [x] `VITE_SUPPORT_EMAIL` · [x] GitHub secret scanning + push protection · [x] walk-forward finding in README · [x] DSR · [x] PBO · [x] purge/embargo · [x] bootstrap CIs · [x] `.gcloudignore` · [x] requirements pinned
