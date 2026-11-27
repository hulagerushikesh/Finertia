# Phase 1: the nightly price load, and staging

Written 27 Nov 2026, when the author chose both as the next build. Part of
[PRODUCT-PLAN.md](PRODUCT-PLAN.md) section 5, Phase 1 and Phase 0.

## Why

Every price today is fetched from Yahoo the first time someone asks for it,
then cached in Firestore for six hours. That puts Yahoo, the least reliable
part of the system, in the path of users' requests, and it means an index
scan (Phase 2) would make hundreds of Yahoo calls on one click. The plan's
gate for this phase: **no request for a tracked ticker calls Yahoo.**

## What is tracked

`backend/universes/`: one JSON file per index, each naming its source and
date, refreshed by hand when membership changes (a few times a year).

| List | Count | Source |
|---|---|---|
| S&P 500 | 503 | Wikipedia, List of S&P 500 companies |
| Nasdaq-100 | 101 | Nasdaq's published list |
| Nifty 50 | 50 | the list the Nifty studies use |
| Nifty Next 50 | 50 | Wikipedia, NIFTY Next 50 |
| **All, without overlaps** | **618** | |

## Design

- **Storage stays Firestore** (`prices/<ticker>_<year>`, the existing L2 in
  `data.py`), not Parquet files as the plan first said. It is already in
  production, already read by every request, and fits in the free tier:
  618 tickers × 22 years × ~15 kB ≈ 200 MB of the 1 GB allowance. A second
  store would mean two copies of the truth. Revisit only if the index scan
  needs columnar reads across hundreds of tickers at once.
- **One job, once a day:** `python -m nightly_prices` as a Cloud Run job,
  started by Cloud Scheduler at 22:30 UTC Monday to Friday, after the US
  close (India closed twelve hours earlier). Same image as the API.
- **Same rule as on request:** each ticker's whole history (2005 onwards,
  plus any older year someone has asked for) is downloaded once and
  rewritten under one batch id, so adjusted prices are never stitched across
  two downloads.
- **Checks before writing:** missing or non-positive closes, dates out of
  order → not written, yesterday's copy stays. Daily moves over 50%, gaps
  longer than seven weekdays, a last bar more than five weekdays old →
  written, listed as warnings.
- **Gentle on Yahoo:** one ticker at a time, one second apart, two retries
  with backoff. That is 618 downloads a day however many people use the
  site, where today every first request per ticker per six hours is one.
- **A summary per run** in `price_loads/<date>`: written, failed, warnings,
  duration.
- **Serving:** with `NIGHTLY_PRICES=on` on the API, a tracked ticker's
  current year is served from Firestore for 30 hours instead of 6. Off by
  default, switched on once the job has run cleanly.

### Free-tier budget per night

| Resource | Use | Free allowance |
|---|---|---|
| Firestore writes | ~13,600 (618 × 22 docs) | 20,000 a day |
| Firestore reads | ~13,600 (listing cached years) | 50,000 a day |
| Cloud Run job | ~20 min of 1 vCPU, 1 GiB | 180,000 vCPU-s and 360,000 GiB-s a month, shared with the API |
| Cloud Scheduler | 1 job | 3 jobs |

Writes are the tight one. If the list grows past ~800 tickers, write only
the years whose bars changed (a dividend changes every year's adjusted close,
so this needs care) before adding more.

## Terms

The legal checklist (PRODUCT-PLAN section 6) says personal, non-commercial
use of Yahoo data and **no bulk download of raw prices offered to users**.
This load keeps prices inside our own cache to compute results; it does not
offer raw prices to anyone, and it replaces many on-demand calls with one
daily call per ticker. It is still more automated use of Yahoo than today,
so it stays paced and small, and it stops if Yahoo objects.

## Slices

1. **Loader, checks, universe, tests** — this PR. Dry run by hand on 27 Nov
   on all 618 tickers: **618 checked, 0 failed, 57 warned** (all of them a
   daily move over 50%, e.g. crash days, spin-offs and old splits — worth a
   look one day, not a reason to block), **17 minutes**.
2. **The job and the schedule** (needs the author's "deploy"): deploy the
   job from the same image in `deploy.yml`, create the Scheduler trigger,
   run it once by hand, read the summary, then switch `NIGHTLY_PRICES=on`.
3. **Visible status:** the last run's summary on the admin page and in
   `release-check.sh`.

## Staging (Phase 0)

A second API that matches production, for trying a change before users see
it. Agreed by the author on 27 Nov.

- **Service** `finertia-api-staging`, us-central1, min 0, max 1 instance.
  Deployed automatically on every push to `main` that touches `backend/`;
  production stays a manual "deploy".
- **Its own data:** a separate Firestore database named `staging` in the
  same project, chosen by a `FIRESTORE_DATABASE` setting. Runs, users'
  usage counts and the price cache never mix with production. Sign-in is the
  same Firebase project, so the same accounts work in both.
- **Cost:** only one Firestore database per project gets the free tier, so
  `staging` is billed at list price. At staging's traffic that is cents a
  month (₹0–10); the service itself is inside Cloud Run's free tier.
- **Front end:** Vercel preview builds point at staging instead of
  production. That needs one setting in the Vercel project (an environment
  variable for Preview), which is the author's part.
- **Gate (from the plan):** staging deploys automatically and the load test
  reports real numbers against it.

### Staging, as built (27 Nov)

- Service `finertia-api-staging` (https://finertia-api-staging-818037622374.us-central1.run.app),
  deployed by `.github/workflows/staging.yml` on every backend push to
  `main`; first deployed by hand from the PR branch.
- Firestore database `staging` (nam5, like production) with production's four
  `runs` indexes. Checked: a share card on staging cached KO's prices in
  `staging`, not in `(default)`.
- `/api/health` says `"environment": "staging"`; preview origins pass CORS,
  other origins do not.
- First numbers: 150 requests to the public share route, 10 at a time:
  34 a second, median 282 ms, 95th percentile 339 ms — and 32 refused by the
  per-address limit, which is working as intended. A proper load test needs
  signed-in backtests against staging with a test account; that is the next
  step for the gate.
- Still to do by the author: in Vercel, set `VITE_API_BASE_URL` for
  **Preview** only to the staging URL. Email sign-in works on preview
  addresses; Google sign-in needs each preview address added to Firebase's
  authorised domains, so use email there.
