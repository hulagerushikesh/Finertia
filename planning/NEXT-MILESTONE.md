# Next milestone — M12 "Product readiness", sprint 1

_Planned 13 Oct 2026 (PM + Scrum). Sprint 1: **Wed 14 Oct → Tue 27 Oct**,
review on the 27th with the author. Sprint 2 runs 28 Oct → 10 Nov. M11
(quality foundation) closed 13 Oct, all seven items: see [ROADMAP.md](ROADMAP.md).
M10's text is in [archive/M10.md](archive/M10.md); its two open phases are
carried here unchanged._

## The constraint that shapes this sprint

The tester round runs until **31 Oct**, and the 8 Oct process rule (DECISIONS)
says: *"A bug that stops a tester finishing a run is fixed before the next
session … Anything else waits for the end of the round, so the five see the
same product."*

So sprint 1 builds what testers **cannot see**: legal groundwork, data
licensing, backups, monitoring, the backend half of account deletion, cold
start. Everything that changes the logged-in product goes into sprint 2,
after the round closes and the phase-4 decision is written. That includes
the free validation, onboarding and the deletion UI. Ordering it this way
keeps the round's evidence clean, and lets sprint 2 build on what the
testers actually said.

Stripe stays off in both sprints unless phase 4 reads "two or more would pay"
**and** the legal check and licensed data are in place (DECISIONS 13 Oct).

## Sprint goal

> By 27 Oct we know what it would cost to charge legally, and production can
> lose data, go down or be asked to delete a user without anyone finding out
> from WhatsApp.

## Sprint 1 board

Ordered by priority. **You** = needs the author: a decision, an account, money
or a production change. Everything else Claude builds and merges on green CI.

| # | Item | Hat | Evidence of done | You |
|---|---|---|---|---|
| 0 | **Close M11 by hand**: RELEASE.md part 4 on live (signed-in run, History, admin ticker filter) + the Sentry test from both snippets | System | Both Sentry projects show the test issue: uid only, request_id tag, no email | 10 min, day 1 |
| 1 | ✅ **Backups** (done 13 Oct: PITR 7 days, daily + weekly schedules, delete protection; drill matched users 6 / runs 42 / prices 336): Firestore point-in-time recovery (7 days) + managed backup schedules (daily kept 7 days, weekly kept 14 weeks) | DB + Cloud | `gcloud firestore databases describe` shows PITR on, and the schedule is listed. **Restore drill**: today's backup restored into a scratch database, `users`/`runs` counts match prod, scratch deleted. Runbook in RELEASE.md part 5 | Yes to the cost (storage, single-digit ₹ at today's size) and to the prod change |
| 2 | ✅ **Uptime alert** (done 13 Oct: `finertia-health` check + down and 5xx policies to the author's email; wiring proven with a deliberately failing check): Cloud Monitoring uptime check on `/api/health` every 5 min from 3 regions, emailing the author after 2 failures; plus an alert on Cloud Run 5xx rate | System + Cloud | A deliberately failing check (wrong path, in a test policy) sends the email, then is deleted | Yes to the prod change; confirm the alert address |
| 3 | ✅ **Licensed data spike** (spike + seam done 13 Oct; budget set to ₹0 for now, provider chosen in a dedicated data sprint after the build work — DECISIONS 13 Oct): shortlist 3 EOD providers covering NSE + US. Compare price per month at our size, the licence (may a paid app *display* derived results?), history depth, corporate actions, API limits | PM + Backend | DECISIONS entry with a comparison table and a recommendation. `data.py` gets a provider interface, with yfinance as the one implementation and no behaviour change (tests green, demo payload identical), so the switch is one module | Pick one, and the budget ceiling |
| 4 | ⏸ **Deferred until the build work is done** (DECISIONS 13 Oct). **Legal brief for counsel**: a data map (what personal data, where: Firebase Auth, Firestore nam5, Cloud Run asia-south1, Sentry US, Vercel), the processors, retention, and the questions for a SEBI / DPDP consult (research-analyst lines, disclaimers, consent, grievance officer, cross-border transfer). Draft Terms and Privacy for counsel to mark up, **not published** | PM | `planning/legal-brief.md` plus the two drafts in `planning/legal/`. This is preparation for a lawyer, not legal advice | Book the consult; target before 10 Nov |
| 5 | ✅ **Account deletion + export, backend only** (done 13 Oct): `GET /api/me/export` (the user's profile and runs as JSON), `DELETE /api/me` (runs, user doc, rate-limit counters, then the Firebase Auth user, in an order that can be retried after a partial failure) | Backend + DB | Route tests, plus an emulator test that a deleted user leaves zero documents behind; E2E for the API. **UI held for sprint 2** (round freeze) | — |
| 6 | **Cold start, measured then cut**: break the 11.4 s down (container start, imports, Firebase init, first Firestore read nam5 ↔ asia-south1). Try the free fixes first: lazy imports, `--cpu-boost`, smaller image | Cloud + System | A before/after table in STATUS. Target: first run < 5 s without `min-instances`. If it can't get there, the cost of `min-instances 1` goes to the author as a decision | Only for the `min-instances` spend |
| 7 | ✅ **Support inbox** (done 13 Oct: Cloudflare Email Routing → author's Gmail, outside test received; the site shows support@ instead of a personal address):: `support@hulage.in` forwarding to the author, linked from Support, Pricing and the footer. The status page stays a sentence on Support ("the API's health: /api/health") until there are users to warn | PM | An email from an outside address arrives. The support-page change is copy only, and allowed under the freeze rule because it changes no flow | Set up forwarding at the domain registrar |
| 8 | **Carried from M10**: tester round (5 sessions, feedback.md entries, end usage count) | PM | As in archive/M10.md phase 3 | Runs the sessions |

**Capacity**: about 2 weeks part-time for the author. Claude's side is about
7 PRs, items 1–3 and 5–6, each through the [release checklist](../RELEASE.md).
Items 1, 2 and 6 touch production; each waits for an explicit yes.

**If time runs short, drop from the bottom of 1–7.** The support inbox and
the cold start can slip to sprint 2. Backups, alerts and the data spike
cannot, because the 31 Oct decision needs the data costs.

## Sprint 2 (28 Oct → 10 Nov) — pencilled, re-planned on 27 Oct

1. **Phase-4 decision** (carried from M10), written by 1 Nov with the round's numbers, by the 8 Oct rules. It decides how much of the rest happens.
2. **One free validation per month** on the free plan: the USP in front of free users, with conversion measured (validations run → upgrade clicks).
3. **Onboarding** from what the testers got stuck on: a first-run hint, 3 sample strategies, empty states on History and Compare.
4. **Account deletion and export UI** in Profile, on the sprint 1 backend.
5. ~~Licensed data integration~~ → its own sprint after the build work (DECISIONS 13 Oct).
6. ~~Terms and Privacy published~~ → after the legal consult, which follows the build work.
7. **Stripe live**: only on the product path, and only after the data sprint and the legal review.

## Definition of done (unchanged from ROADMAP)

Code + unit tests + an E2E path for any user flow touched + the
[release checklist](../RELEASE.md) + STATUS updated.

## Explicitly not in sprint 1

Anything a tester would see in the logged-in app, apart from a bug that stops
a run · Stripe · new strategies or indicators · SEO pre-rendering (M13) ·
the free-validation change (sprint 2, after the round).

## Decisions needed from the author this sprint

1. Backups and alerts in production: yes / no (items 1–2). Roughly ₹0–100 a month at today's data.
2. ~~Monthly budget ceiling for licensed data~~ — ₹0 for now; a data sprint after the build (13 Oct).
3. ~~Book the legal consult~~ — after the build work (13 Oct).
4. `support@` forwarding: Cloudflare Email Routing (DNS is on Cloudflare), set up by the author (item 7).
5. After item 6: whether `min-instances 1` (~₹1–2k a month) is worth it, if the free fixes miss the target.
