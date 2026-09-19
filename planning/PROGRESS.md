# Progress — the whole story, from the first commit

_Chronological. One section per stretch of work, each with what was built, what
it proved, and what changed course because of it. STATUS.md says where things
are now; this file says how they got there. Append a section per stretch; never
rewrite an old one._

## Numbers over time

| Date | Tests | Cloud Run rev | Commits (main) | PRs | Note |
|---|---|---|---|---|---|
| 14 Aug | 336* | — | 1 | 0 | initial commit, all 8 product stages |
| 22 Aug | 421* | — | 14 | 0 | validation engine complete (DSR, PBO, purge) |
| 6 Sep | 421* | 00001–00002 | 17 | 0 | live; submitted to Pitch Fest |
| 13 Sep | 535 | 00003 | 26 | 4 | M8 closed: bootstrap CIs, deploy hygiene |
| 15 Sep | 567 | 00005 | 45 | 9 | price cache, effective N, phase 4 decided |
| 16 Sep | 603 | 00007 | 52 | 11 | rolling walk-forward, volatility regimes |
| 17 Sep | 603 | 00007 | 56 | 11 | redesign merged (PR #6) |

\* `def test_` definitions counted from git, which undercount parametrised
cases; from 13 Sep the figure is what `pytest` collects. Commits are
`git rev-list --count`, merges included.

## 1. 14–15 Aug — Foundation

**Built.** `a3598e0`: the whole product in one commit — FastAPI backend
(signals, engine, metrics, risk overlays, portfolios, analytics, plans, billing),
React 18 + Vite + Tailwind + Recharts frontend, Firebase Auth + Firestore, 8
stages S1–S8 laid out in the README. Next day: usable on a phone, CI off the
deprecated Node 20 actions, test deps in their own file.

**Proved.** The Firestore rules had a privilege-escalation hole (a client could
promote itself to admin or the Pro plan through its own profile document,
which every backend authorisation decision reads back). Closed in `8083c02` and pinned by the
`firestore-tests` suite against the emulator — 5 attack shapes, 20 rule tests.
The HTTP layer had zero coverage; `3d87185` added route tests.

**Changed course.** Security tests before features. Every later PR that touches
rules re-runs the emulator suite.

## 2. 19–22 Aug — The validation engine and a measurement UI

**Built.** Deflated Sharpe Ratio (`deflated.py`, Bailey & López de Prado 2014),
PBO via CSCV (`pbo.py`), purge + embargo at the walk-forward split
(`purge.py`). Two-tone "measurement" palette; the validation panel shows what
each check found rather than a single verdict. Type scale, document outline,
dashboard density fitted to its real column.

**Proved.** DSR reproduces the paper's 3.26 and Lo (2002) to 1e-12. CSCV
regime-blindness pinned by test. Purge measured a real boundary trade at 33
bars. 535 tests.

**Changed course.** Decision (22 Aug): no shadcn — hand-written components,
because shadcn copies source in to be restyled and the UI was small. Reversed
13 Sep (see §5). Decision: pure pandas/numpy, no backtesting or TA library —
every formula is in the repo and testable.

## 3. 6 Sep — Live, and submitted

**Built.** Vercel (frontend, SPA fallback for deep links) + Cloud Run
`finertia-api` in asia-south1, `min-instances 0`, secret in Secret Manager.
`/api/*` proxied through Vercel so the browser never crosses origins.
Submitted to Builders Pitch Fest 2026 (BFSI track) with `/demo` as the judged
link, a deck and a demo video.

**Proved.** Three real AAPL runs on the live site before submission. `Invalid
Date` in run history found on the live site and fixed the same night.

**Changed course.** From here on, `main` auto-deploys the judged site. Rule
adopted: nothing that changes what a judge sees merges until the result is in.
Backend is *not* auto-deployed — every backend change needs a manual
`gcloud run deploy`, which was forgotten once (5 days of stale prod, §4).

## 4. 8–13 Sep — Confidence intervals and deploy hygiene (M8 closed)

**Built.** Stationary block bootstrap with BCa intervals around every metric
the dashboard prints (`bootstrap.py`, PR #1). Dev-server launch config (PR #2).
`.gcloudignore` so `.env` and tests never reach Cloud Build; requirements
pinned to what prod runs (PR #3). `.vercel` ignored (PR #4). Backend
redeployed, rev 00003.

**Proved.** Bootstrap coverage measured on 300 GARCH paths. A wiped-out
backtest crashed the metrics (`21170e3`) — found by the interval code, fixed.

**Changed course.** Prod had been serving unpinned deps for 5 days without
anyone noticing. Pinning + a `.gcloudignore` + "redeploy is manual" written
into the risk list. M8 closed 13 Sep.

## 5. 14 Sep — M9 begins: docs in the repo, the redesign committed, the cache built

**Built.** `learning/` (foundations → stack → validation methods → research)
and `planning/` (STATUS, NEXT-MILESTONE, BACKLOG, DECISIONS, product brief),
PR #5. The uncommitted 45-file shadcn rebuild on `redesign` committed in five
reviewable slices: token sheet → primitives + motion vocabulary + sonner →
charts on CSS variables → dashboard panels → app shell and pages. Bundle
audited: entry 746 → 521 kB raw after LazyMotion and `firebase/firestore/lite`.
Light-theme contrast raised to ≥ 4.5:1 on every ground. Firestore price cache
(`price_store.py`) written the same evening.

**Proved.** Redesign verified on the Vercel preview: contrast ≥ 4.58:1 across
9 routes × 2 themes (measured), 375 px zero overflow, one `<main>` per route,
reduced-motion honoured. PR #6 opened and **held** under the §3 rule.

**Changed course.** Decision: docs live in the repo; the published artifacts
are views refreshed *from* `planning/`, not the other way round. Decision
(dated 13 Sep on the branch): shadcn adopted after all — the UI had outgrown
hand-written primitives; reversal logged with the reason.

## 6. 15 Sep — The cache lands, the roadmap closes, the fork is decided

**Built.** Price cache merged (PR #7, rev 00004): `prices/{TICKER}_{YEAR}`
columnar docs, stale-on-error, whole-ticker refetch under one batch id because
yfinance adjusts as of fetch date. Prewarmed 28/28 suggested tickers. Effective
N of the grid (PR #8, rev 00005): eigenvalue (Li & Ji 2005) and clustering
(LdP & Lewis 2019) estimates, headline = the larger, wired into the DSR.
Roadmap 5 of 5.

**Proved.** Cache latency is a wash (Firestore `nam5` ↔ Cloud Run
`asia-south1`), so the cache buys resilience, not speed — recorded
unflattering. Canonical AAPL: momentum 16 → 6 effective trials, MACD 4 → 2,
Bollinger 12 → 7; DSR moved +0.07…+0.12, no verdict changed. **Found while
measuring:** the walk-forward verdict *flips* when the window extends one year
(split Feb → Oct 2022). Open-questions §3 promoted to the top research item.

**Changed course.** Phase 4 decided (PR #9, DECISIONS.md): Finertia is a
**portfolio piece with a write-up, not a product**. Stripe stays built and
unwired; research items outrank feature items; the write-up
(`planning/write-up.md`) is the deliverable. Reversal conditions logged.

## 7. 16 Sep — One verdict per fold, and a name for the regime

**Built.** Rolling anchored walk-forward (`rolling.py`, PR #10, rev 00006):
first split at 40 %, the remainder tiled into 4 folds, purge gap at every
boundary, one grid sweep per fold, stitched OOS curve with a bootstrap CI,
parameter stability, verdict `consistent` / `regime_dependent` / `failed`.
Volatility regimes (`regimes.py`, PR #11, rev 00007): every bar labelled by
the *market's* trailing 21-bar realised vol into period terciles; Sharpe,
contribution and hit rate per regime on every backtest and on the stitched
OOS record.

**Proved.** 18 + 14 new tests, 603 total; five mutation checks (select on OOS,
drop the gap, fixed window, label on strategy returns, centred window) each
fail the test written for them. Canonical AAPL 2018 → 2024: momentum's
parameters changed in all four folds; all three strategies read
`regime_dependent` on both windows. Momentum OOS Sharpe 2.26 in the calm third
of bars, −0.76 in the turbulent third — the window flip of §6 now has a
mechanism, not just a date.

**Changed course.** The write-up grew two sections (fold table, regime table)
and needs trimming to ~1,500 words before publishing. Open-questions §3 closed
as scoped; a trend/range label is the remaining regime question.

## 8. 17 Sep — The redesign merges

**Built.** `redesign` brought up to date with `main` (one conflict,
`planning/STATUS.md`, resolved to main's copy), CI green, merged as PR #6 on
the user's explicit call — before the Pitch Fest result, overriding the §3
rule (logged in DECISIONS.md). Frontend only; rev 00007 unchanged. This file
added.

**Still open from the merge.** The login smoke test (dashboard at 1024 px,
History, Profile displayName save, Register — every `firebase/firestore/lite`
call) now runs against production rather than a preview. The two UI follow-ups
that waited on the branch — "served from cache" note and raw-vs-effective N in
`ValidationPanel` — plus the rolling fold table and regime table are now
plain feature branches off `main`.

## 9. 19 Sep — The UI batch lands

**Built.** Four frontend PRs merged to `main` in one go, all previewed
against a real AAPL 2018 → 2024 payload before opening. PR #13: rolling fold
table, regime tables, raw-vs-effective N, "served from cache" note — the two
follow-ups that had waited on the redesign. PR #14: favicon set (Newsreader
"F" on ink, pencil underline), web manifest, `og.png` share card — the fix
for the blank icon in the phone's search results. PR #16: landing copy in
plain words ("Backtest · then check it's real"; "The blue stretch is the only
part that counts") after the user read the page as a customer and found it
heavy. PR #17: a verdict card above the validation working — "Is this real?",
`2 of 5 checks passed`, an overall stamp, one sentence on what the combination
means, one plain word per check; the five sections fold behind "Show the
working" and a chip click opens the section it names.

**Proved.** CI green on each PR; 1280 + 375 px, light + dark, zero overflow;
prod serves `/favicon.svg` as `image/svg+xml` and the `DashboardPage` chunk
carries the verdict strings. Backend untouched — rev 00007 still serving.

**Changed course.** PR #15 (verdict card) was stacked on #13's branch; GitHub
closed it when that branch was deleted on merge and would not reopen it, so
the same commit went in as PR #17 against `main`. Lesson: merge stacked PRs
bottom-up *without* `--delete-branch`, or retarget the upper PR first. The
"525: SSL handshake" the user saw in a mobile search was a stale history
title from the Cloudflare-proxied era — DNS points at Vercel directly now, no
fix needed. Still open from the merge: the logged-in smoke test on production,
and whether to trim the results tab to four headline numbers.

## 10. 19 Sep — Simplify: theme, surfaces, folds, landing

**Built.** Five PRs in one sitting after the user's read: "UI is a little
good, but complex for a user's view — only black and white". PR #19 swapped
the palette to tweakcn's Ocean Breeze (green accent, sky paper, slate dark)
and the type to DM Sans; the preset's oklch tokens were converted to the HSL
triples the charts already consume, and every text role re-measured to
≥ 4.5:1 (the preset's own white-on-green button was 2.3:1 — buttons carry
ink instead). PR #20 removed the notebook metaphor: rotated stamps became
shadcn Badge tones, pencil underlines became colour only, graph paper and
the custom shadow scale went. PR #21 folded the set-up panel to three
decisions (strategy, ticker, dates) plus one Advanced fold with a
changed-count badge, and the results tab to four numbers and the equity
curve plus one "show all" fold — `useDisclosure` + `MoreToggle` now shared
with the validation working. PR #23 rewrote the landing page for a reader
who has never heard the word backtest: what it is, three steps, a real run,
who it is for, why the checks matter, one call to action.

**Found.** Signed in on production, "Run a backtest" sent the user to
/register. Every marketing CTA hard-linked there. PR #22: CTAs go to the
workspace when a user is present, and /login and /register redirect
signed-in users (`PublicOnlyRoute`).

**Proved.** Each PR previewed on the dev server against the real AAPL
2018 → 2024 payload (set-up panel, metrics halves, verdict card, working),
at 375 px and 528/1280 px, light and dark, scrollWidth 375, production build
clean; prod bundle strings and `<title>` checked after each merge.

**Changed course.** Four theme candidates were rendered on a mock Finertia
result screen (not tweakcn's generic dashboard) so the choice was made on our
own components; Ocean Breeze won over Modern Minimal on warmth. The stacked-PR
lesson from §9 held: every PR today branched from `main`.

## What is next

See [NEXT-MILESTONE.md](NEXT-MILESTONE.md) for the ordered list and
[BACKLOG.md](BACKLOG.md) for everything behind it. The short version on 19 Sep:
run the logged-in smoke test on production (the new folds and the CTA fix have
only been seen on previews), regenerate the demo payload with regimes, publish
the write-up once the Pitch Fest result is in.
