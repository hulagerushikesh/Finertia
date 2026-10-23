# B1: move the API to us-central1

_Prepared 23 Oct 2026. Decided 23 Oct: B1, carried out **after the tester
round closes on 31 Oct** (the five testers see the same product). Each step
marked **prod** waits for the author's yes on the day._

## Why

The first signed-in backtest on rev `00025-82m` (18 Oct) took 3.7 s, and
nearly all of it was Firestore round trips of 0.4–1.8 s each between Cloud
Run in Mumbai and Firestore nam5 (STATUS, 23 Oct). nam5's primary region is
Iowa, so the API moves to `us-central1`. Users in India then pay one long
trip per request (Vercel → Iowa) instead of about five. No data moves.

## What was checked on 23 Oct (read-only)

| Item | Finding | Action |
|---|---|---|
| Runtime service account, secret `finertia-sa` | Project- and secret-level grants, not regional | None |
| Deployer (`finertia-deployer`) | `run.admin`, `cloudbuild.builds.editor`, `storage.admin`, `artifactregistry.writer` | `writer` cannot create a repository: the `cloud-run-source-deploy` repository in us-central1 is created once by hand (step 1) |
| Firebase Auth, Sentry | Not tied to a region | None |
| Uptime check `finertia-health` | Hits `finertia.hulage.in/api/health`, through Vercel | Follows the rewrite on its own |
| 5xx alert policy | Filters on `service_name="finertia-api"`, any region | Covers both services |
| Service settings not passed by the deploy | `ALLOWED_ORIGINS`, `LOG_LEVEL` (env); startup CPU boost | Env copied in step 3; `--cpu-boost` now in the deploy command |
| New service URL | Deterministic: `https://finertia-api-818037622374.us-central1.run.app` | Used in the switch PR |

## Steps

**1. Create the image repository** (prod, once):

```bash
gcloud artifacts repositories create cloud-run-source-deploy --repository-format=docker \
  --location=us-central1 --project=momentbacktracking
```

**2. Deploy to us-central1** (prod: a new service, but nobody is sent to it yet):

```bash
scripts/release-check.sh pre
gh workflow run deploy.yml --ref main -f region=us-central1
```

The workflow tests, deploys and checks `/api/health` on the new service. It
does not move the `backend-deployed` tag, because `SERVING_REGION` is still
`asia-south1`.

**3. Copy the service settings the deploy does not pass** (prod). Values are
read from Mumbai, never written down:

```bash
eval "$(gcloud run services describe finertia-api --region asia-south1 --project momentbacktracking --format=json \
  | jq -r '.spec.template.spec.containers[0].env[] | select(.name=="ALLOWED_ORIGINS" or .name=="LOG_LEVEL") | "export \(.name)=\(.value|@sh)"')"
gcloud run services update finertia-api --region us-central1 --project momentbacktracking \
  --update-env-vars "^@^ALLOWED_ORIGINS=$ALLOWED_ORIGINS@LOG_LEVEL=$LOG_LEVEL"
```

(`^@^` makes `@` the separator, since `ALLOWED_ORIGINS` contains commas.)

**4. Check the new service directly** before anyone is sent to it:

```bash
U=https://finertia-api-818037622374.us-central1.run.app
curl -s $U/api/health
curl -s -o /dev/null -w '%{http_code}\n' $U/api/strategies
curl -s -D - -o /dev/null -X OPTIONS $U/api/backtest -H 'Origin: https://finertia.hulage.in' \
  -H 'Access-Control-Request-Method: POST' | grep -i access-control-allow-origin
REGION=us-central1 scripts/release-check.sh pre
```

Health reports the `main` commit, strategies return 200, and the preflight
allows the site's origin.

**5. Switch** (prod): merge the switch PR. It changes three things together:

- the `/api/*` rewrite in `frontend/vercel.json` to the us-central1 URL;
- `SERVING_REGION` and the `region` input's default in `deploy.yml` to `us-central1`;
- the region in README, RELEASE.md and `release-check.sh`.

Vercel deploys the rewrite within about a minute of the merge. Then move the
tag to what us-central1 serves, and run the after-release checks:

```bash
git tag -f backend-deployed "$(curl -s https://finertia.hulage.in/api/health | jq -r .commit)" && git push -f origin backend-deployed
scripts/release-check.sh post
```

Then by hand, signed in (RELEASE.md part 4): a backtest, the same one again,
a portfolio, History, Admin Overview.

**6. Compare.** After a day of use, the same query as SYSTEM-DESIGN "Reading
A1's numbers", with `resource.labels.location="us-central1"`. Expect
`profile`, `ratelimit`, `prices_read` and `run_write` in single-digit
milliseconds, and a whole-request backtest well under the 3.6 s baseline
(the Vercel → Iowa trip is added once).

## Rollback

Revert the switch PR. Mumbai keeps running with min-instances 0, so it costs
nothing idle and answers again within a cold start. The uptime check goes
through the site, so the first requests after a revert may take ~8 s.

Keep Mumbai for at least a week after the switch, then delete it (with the
author's yes) so that only one service holds production config.

## Not affected

Firestore data, rules, indexes, backups and PITR; Firebase Auth; Sentry
projects; the domain (served by Vercel, not by Cloud Run domain mapping).
