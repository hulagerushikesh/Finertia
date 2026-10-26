# Release checklist (PVT)

Production verification before and after every release. It exists because
"it builds" shipped #84's bugs, and because on 13 Oct the first run of the
script below found the live Firestore rules a release behind the repo.

Two kinds of release:

- **Frontend** — every merge to `main` deploys on Vercel by itself. Parts 1 and 4.
- **Backend** — `deploy.yml`, run by hand. All five parts, in order.

Firestore rules and indexes are deployed separately with `firebase deploy`. They
are covered in part 2 because code that needs a new index or rule must not go
out before it.

Automated checks are in `scripts/release-check.sh`. It is read-only: it reads
GitHub, the live site and the GCP project, and changes nothing. Anything that
changes production (deploys, env vars, rules, indexes, traffic) needs the
author's yes first.

## 1. Before merging (every PR)

Tick these in the PR template.

- [ ] CI green: Backend tests, Frontend build (unit tests + bundle budget), E2E (Playwright), Secret scan, Vercel preview.
- [ ] A user flow the PR touches has an E2E path, either an existing one or a new one (Definition of Done, [ROADMAP](planning/ROADMAP.md)).
- [ ] Pages touched checked in the light **and** the dark theme, and at 375 px wide with no horizontal scroll.
- [ ] A new environment variable, Firestore rule or index is called out in the PR description.

## 2. Before a backend deploy

```bash
scripts/release-check.sh pre
```

- [ ] No FAIL. Every WARN read and settled. The script checks:
  - CI and Vercel are green on `main`;
  - what `backend/` would ship since the `backend-deployed` tag;
  - dependency changes;
  - new `os.environ` reads;
  - live rules == `firestore.rules`;
  - composite indexes READY.
- [ ] New env vars are set on the service first, or are safe when unset. Use `gcloud run services update finertia-api --region us-central1 --update-env-vars …`, never `--set-env-vars`, which wipes the others.
- [ ] Changed indexes are deployed first and READY: `firebase deploy --only firestore:indexes --project momentbacktracking`. A query that needs a missing index fails.
- [ ] Changed rules are deployed: `firebase deploy --only firestore:rules --project momentbacktracking`.
- [ ] The rollback revision printed by the script is noted.
- [ ] The author said yes.

## 3. Deploy

```bash
gh workflow run deploy.yml --ref main
gh run watch "$(gh run list --workflow deploy.yml --limit 1 --json databaseId -q '.[0].databaseId')"
```

The workflow runs the backend tests, deploys, and waits until `/api/health`
returns 200 **and** reports the commit just deployed. Then it moves the
`backend-deployed` tag. If it fails after the deploy step, the new revision may
be serving; go to part 5.

## 4. After the release

```bash
scripts/release-check.sh post
```

- [ ] No FAIL. The script checks:
  - `/api/health` 200 through the site, serving the `backend-deployed` commit;
  - the public API routes return 200;
  - an admin route without a token returns 401;
  - the CORS preflight from the site is allowed;
  - every public page returns 200;
  - live rules and indexes;
  - Cloud Run traffic;
  - no ERROR log lines in the last 30 minutes.

By hand on https://finertia.hulage.in, signed in with your own account. Never
create accounts on production; registration is covered by E2E against the
emulators.

- [ ] Logged out: `/`, `/demo` (Results and Validation tabs), `/pricing`, `/writeup` render, with no console errors.
- [ ] Signed in: run a backtest. Results show, and the Validation tab gives the verdict (Pro) or the Pro wall (free).
- [ ] History lists the run. Re-run opens its config.
- [ ] Admin, if the release touches it: Overview numbers load; Users search by email prefix; Runs filter by ticker.
- [ ] Pages the release touched: light and dark theme, 375 px.
- [ ] Sentry, 15 minutes later: no new issue in `python-fastapi` (release = the new revision) or in `finertia-web`.

## 5. If something is wrong

Roll back first, then debug.

**Backend.** Send traffic back to the previous revision, from part 2:

```bash
gcloud run services update-traffic finertia-api --region us-central1 --project momentbacktracking --to-revisions <previous-revision>=100
```

Then point the tag at what is serving again. `/api/health` names the commit:

```bash
git tag -f backend-deployed <commit> && git push -f origin backend-deployed
```

**Frontend.** Vercel → Deployments → the last good one → **Instant Rollback**.
Then revert the PR on `main`, so the next push does not redeploy the bad build.

**Rules or indexes.** Revert the file on `main` and deploy it again with the
same `firebase deploy` command.


**Data.** Firestore keeps 7 days of point-in-time versions (any whole
minute), a daily backup kept 7 days, and a weekly backup (Sundays) kept 14
weeks. The database also has delete protection on. Never restore over
`(default)`. Restore into a new database, check it, then copy back what was
lost:

```bash
# A minute in the last 7 days:
gcloud firestore databases clone --project momentbacktracking \
  --source-database="projects/momentbacktracking/databases/(default)" \
  --snapshot-time=2026-10-13T07:10:00Z --destination-database=restore-YYYYMMDD

# Or a scheduled backup, for anything older:
gcloud firestore backups list --project momentbacktracking --location nam5
gcloud firestore databases restore --project momentbacktracking \
  --source-backup=<backup name from the list> --destination-database=restore-YYYYMMDD
```

Delete the scratch database when done
(`gcloud firestore databases delete --database=restore-YYYYMMDD`).

Drill, 13 Oct 2026: cloned to 07:10 UTC in about 10 minutes. `users` 6,
`runs` 42 and `prices` 336 matched production, and the scratch database was
deleted. Repeat the drill once a quarter, or after any change to how data is
stored.

**Alerts.** Cloud Monitoring emails the author when:
- `https://finertia.hulage.in/api/health` fails from 2 or more of 3 regions
  for 10 minutes (uptime check `finertia-health`, every 5 minutes, through
  Vercel, so the rewrite is covered too);
- `finertia-api` returns more than 4 responses with a 5xx status in 5 minutes.

Both close on their own 30 minutes after recovery. Sentry covers the
individual errors. These two cover "the site is down" and "many requests are
failing", which Sentry can miss when the process cannot start at all. The
checks also keep one instance warm most of the time. That costs nothing extra,
because CPU is billed only while a request is being served.

## Record

- [ ] Comment on the PR(s) shipped with the ticked list and the `post` output.
- [ ] Update `planning/STATUS.md` → Live: the revision, the commit, the date.
