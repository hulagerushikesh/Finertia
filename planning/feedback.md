# Outside-user feedback — M10 phase 3

Five people who are not the author: at least one trader, one finance student,
one engineer. **Exit:** five entries below and both usage counts filled in.

## Usage counts

Taken with `backend/scripts/usage_counts.py` (read-only, prints no emails),
author's accounts excluded (the `+fin1` one is the 7 Oct smoke-test throwaway):

```bash
cd backend && .venv/bin/python scripts/usage_counts.py --since 2026-10-07 \
    --exclude hulagerushikesh@gmail.com --exclude hulagerushikesh+fin1@gmail.com
```

**Start, 7 Oct 2026:**

| | All time | Since 2026-10-07 |
|---|---|---|
| Sign-ups | 0 | 0 |
| Saved backtest runs | 0 | 0 |
| Users with a saved run | 0 | 0 |
| Backtest + portfolio runs (`totalRuns` sum) | 0 | — |
| Pro accounts | 0 | — |

Including the author: 1 sign-up, 21 saved runs, 24 counted runs. Every
recorded use so far is the author's.

**End, _date_:**

_(paste the script's output here)_

## Running a session

Printable version, with space for notes: [session-sheet.md](session-sheet.md).

0. **Warm the API, 2–5 minutes before.** Open
   https://finertia.hulage.in/api/health and wait for it to answer, then run
   one backtest on your own account. Cloud Run scales to zero when idle, and a
   cold first run takes ~11 s (STATUS known risk 1): a tester reads that as
   broken, which is a finding about the server, not the product. The instance
   stays warm about 15 minutes after the last request; for an async tester,
   say "the first run can take 10 seconds" in the message instead.
1. Send the message for their type (below). If they will register, add: "the
   confirmation email is from noreply@momentbacktracking.firebaseapp.com —
   that's us" (the subject says Finertia; the sender address is the Firebase
   project ID and cannot change without custom SMTP). Live is better than async: a call
   with their screen shared, or sitting beside them.
2. **Don't help.** Say once, "think out loud; I'll stay quiet." When they get
   stuck, write down where and wait 30 seconds before saying anything. Where
   they get stuck is the finding.
3. The task: "Test whether a simple rule would have made money on a stock you
   know." Nothing more specific.
4. Afterwards, ask the four questions in the entry, in order. Ask the price
   question last and exactly as written. Don't defend the price.

**The Pro wall is part of the test.** The dashboard's Validation tab is Pro
only, and Stripe is not live, so a free account hits an upgrade prompt there.
Record what they do at that point; it is the most honest willingness-to-pay
signal the round will get. `/demo#validation` shows them the checks without
it. If a tester wants to run validation on their own idea, give them Pro from
**Admin → Users → Give Pro** (the author's account is admin since 7 Oct). It
is stamped `planSource: "admin"`, and
`usage_counts.py` counts it as comped, not paid. Note it in their entry.

## Messages

Keep them short; the link does the work. Send the `/writeup` link only to
people who will read 2,000 words.

**Trader / investor**
> I built a tool that tests a trading rule on past prices, and then checks
> whether the result was skill or luck by re-testing it on years it was never
> tuned on. Most backtests skip that part. Could you try it on a stock you
> follow and tell me where it's wrong or confusing? 15 minutes:
> https://finertia.hulage.in/demo#validation

**Finance student**
> I built a backtester that runs the overfitting checks you read about:
> walk-forward, permutation test, deflated Sharpe, PBO. It shows when they
> disagree. Would you try it for 15 minutes and tell me what doesn't make
> sense? https://finertia.hulage.in/demo. The write-up of what it found is at
> https://finertia.hulage.in/writeup

**Engineer**
> Side project: a FastAPI and React backtester whose engine is plain
> pandas/numpy with 700+ tests, and every figure in the write-up is checked
> by a script. Would you try it for 15 minutes as a user, not a reviewer, and
> tell me where it lost you? https://finertia.hulage.in/demo

**Anyone else**
> I built a website that tells you whether a trading idea would have
> worked, and whether that was luck. Could you try it for 10 minutes while I
> watch and say what's confusing? https://finertia.hulage.in

## Bugs found in testing (fix log)

First weekend round (12–13 Oct), friends testing the live dashboard. These are
product defects, logged apart from the per-person Q&A below. "This should be
caught by us" — the PVT missed the logged-in dashboard paths.

| # | Finding | Status |
|---|---|---|
| 1 | Unverified email can sign in and run backtests (indicators usable; the "Confirm your email" banner just persists) | **Decision needed** — gating runs on `emailVerified` would have blocked these testers; see note below |
| 2 | Date-too-short error didn't show the parsed range, so a dd/mm vs mm/dd mix-up (06/01/2024 read as 6 Jan, not 1 June → ~3 trading days) looked like a tool bug | **Fixed** — error now echoes `start → end` in ISO (schemas.py) |
| 3 | Trading-day count ignores that NSE occasionally trades a Saturday/Sunday (special sessions) | Noted, low priority — affects Indian tickers only; generic calendar |
| 4 | (= #1) banner persists after registering without verifying, indicators still available | Decision needed |
| 5 | Validation can't be run as a non-Pro member (the Pro wall) | Working as designed — this is the willingness-to-pay test |
| 6 | Validation required the ticker to still be in the left box after a run; clearing it gave "ticker missing" although AAPL had already been run | **Fixed** — Validation now reads the frozen config of the run on screen, not the live box (DashboardPage.jsx) |
| 7 | With the box cleared, the user hit "ticker missing" first, then "not a Pro user" only after re-typing — auth/Pro should be the first thing they hit | **Fixed** by #6 — a non-Pro user now goes straight to the Pro wall; the 402 gate already runs before data fetch (main.py:681), the problem was the empty request from the frontend |
| 8 | Leaving the workspace (to History, anywhere) and coming back emptied it: the result, the validation and the config were gone, so getting the answer back meant re-running — a monthly run spent and a duplicate History row (author, 13 Oct) | **Fixed** — the workspace keeps its last run in memory per account (`lib/workspaceStore.js`): coming back shows it, with no API call. Memory only: a reload or closed tab starts fresh, and sign-out clears it. Treated as a defect under the 8 Oct rule (work lost, quota spent), not a feature |
| 9 | Admin → Overview showed "Something went wrong": `/api/admin/stats` returned 500 since rev 00021, because the averages query (avg Sharpe + avg return in one aggregation) needs a composite index Firestore's emulator does not enforce, so CI passed (author, by-hand check, 13 Oct) | **Fixed** — index on `runs` (`metrics.sharpe_ratio`, `metrics.total_return`) in firestore.indexes.json, plus a test that fails if a multi-field aggregation has no index |
| 10 | Pricing: with billing off, the Pro card's button ("Create an account") made a free account, and signed in it read "Billing is not enabled on this deployment" (author, 13 Oct) | **Fixed** — while billing is off the Pro card says **Coming soon** / "Not on sale yet", offers Start free, and points testers who need validation to support@hulage.in; the cancellation line is hidden. Unchanged once billing is on |
| 11 | History on a phone: with no runs, "No runs yet." sits in a 52rem-wide table row, so the text is cut off at 375 px (Claude, found in the 375 px check for the onboarding screens, 13 Oct) | **Queued** — cosmetic, does not stop a run, so it waits for the round (8 Oct rule). Already fixed behind the `onboarding` switch (the empty state becomes its own card outside the table), so it goes live when that switch does |

Also fixed this round (spotted by the author): admin **Actions** column was
ragged — variable-width buttons (Block/Unblock, Give/Remove Pro, Make
Admin/User) in a right-justified row — now fixed-width slots so the verbs line
up; and admin green text was invisible on the light theme (`text-accent`, a
background tint, → `text-pencil`), shipped in #83.

**Decision on #1 (unverified email) — resolved 13 Oct: leave it, keep the
banner.** Anyone can use the app before verifying; the only consequence is a
password reset can't reach an unverified address, which the banner states.
Enforcing verification before runs would be a real wall — it would have stopped
this very round, since none of the friends verified. Not worth the friction
while the goal is getting people to try it. Revisit only if it becomes an abuse
or deliverability problem.

## Entries

Copy the block once per person. Use a first name or a role, not a full name.

### 1. _who_ — _trader / student / engineer / other_ · _date_ · _live / async_

- **Finished a run unaided?** _yes / no — if no, where they stopped_
- **Opened Validation?** _on /demo / in the dashboard / no — and what they made of the verdict_
- **What confused them:** _their words, quoted where possible_
- **Would they pay ₹1,000 / $12 a month?** _yes / no / "maybe if…" — exact words_
- **Hit the Pro wall?** _what they did_
- **Anything else:**

### 2.

### 3.

### 4.

### 5.

## What the five said, together

Score each tester against the definitions fixed on 8 Oct in
[DECISIONS.md](DECISIONS.md) ("How phase 4 will read the five sessions"), not
against impressions. **Returned** is read from the `runs` collection 7 days
after the session (Firestore console → `runs` → filter `uid`).

| # | Type | Finished unaided | Opened Validation | Engaged | Returned | Would pay |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| **Total** | | /5 | /5 | /5 | /5 | /5 |

**Rule result:** _product / education / portfolio_ — which line of the rule
fired, and the numbers that fired it.

_Patterns, not anecdotes (fill in after entry 5): where people got stuck in
more than one session, what the Pro wall did, what the price answers had in
common. This is the input to phase 4._
