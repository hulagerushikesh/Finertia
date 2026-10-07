# Next milestone — M10: "Publish the finding, then let a real user decide"

_Drafted 7 Oct 2026. Target: ~2 weeks part-time. Previous milestone (M9, land
the redesign + close the roadmap + make data survive) closed 15 Sep; its full
text is [archive/M9.md](archive/M9.md)._

## Why this milestone

Three things are true today:

1. The engineering is done. Roadmap 5 of 5 plus seven post-roadmap research
   items, 723 tests, prod == `main`, and since 28 Sep a backend deploy is one
   command (`gh workflow run deploy.yml --ref main`, WIF, PR #57). Nothing
   technical is blocking anything.
2. The deliverable chosen on 15 Sep — the write-up — is drafted (3,300 words,
   now covering whole-grid inference, the Sharpe-difference test, baskets and
   costs) and **unpublished**. A finding nobody can read is worth nothing as a
   portfolio piece.
3. No one but the author has used the product. That is the input the 15 Sep
   decision named for reversing it ("a Pitch Fest placement that brings users,
   or a second person willing to own support") — and it has never been
   collected.

So M10 ships the write-up and collects the one piece of evidence that decides
what Finertia is next. It adds no features.

## Phases, in order

### Phase 0 — Close what M9 left on the user (≈1 hour)

- [ ] Narrow the `gh` token — fine-grained PAT over the active repos; `gh auth status` shows `github_pat_…`.
- [ ] Finish the production smoke test — portfolio results card done 28 Sep (it found the colour bug, PR #58); still to walk: validation tab in portfolio mode, regime direction table, History, Profile displayName save, Register a throwaway.
- [ ] One logged-in `/dashboard` AAPL run with the network panel open — record the prod cache read latency in STATUS (the M9 phase 2 number that was never taken).
- [ ] Merge PR #58 (contribution colour by sign).

**Exit:** STATUS "Blocked on user" row reads 0.

### Phase 1 — Publish the write-up (week 1)

The 15 Sep plan said "not before the Pitch Fest result". Three weeks on, the
result is either in or overdue; either way it no longer gates publishing.
Record which in DECISIONS.md when this phase starts.

- [x] Fact-check pass — `backend/scripts/reproduce_writeup.py` re-runs every call through the production route handlers and checks all 174 quoted figures (7 Oct). Every deterministic figure reproduced to the digit; the 9 bootstrap figures had come from research runs with a different seed and were replaced with the product's seeded values, endpoints now to one decimal (they move up to 0.3 between seeds). No conclusion changed. Draft 3.
- [x] Cut to a readable length — draft 4: main text ~2,050 words (from 3,400), per-check detail, the vol × trend grid and the Sharpe-gap table moved to appendices A–C; every one of the 174 figures still in it (7 Oct).
- [x] Home: `/writeup` renders `planning/write-up.md` itself (`?raw` import + a hand-written renderer for the subset it uses, React elements only), so the published page cannot drift from the file the script checks. Lazy chunk, 9.9 kB gz (7 Oct).
- [x] Linked from README ("What it found"), the landing page, the logged-out nav ("The finding") and the footer (7 Oct).
- [ ] Share card: the in-sample vs out-of-sample table as the og image for `/writeup`.

**Exit:** a public URL, linked from README and landing; every number in it re-run after 28 Sep.

### Phase 2 — Make the demo explain itself (week 1–2)

- [ ] Demo GIF for the README: `/demo` → results → the cost and benchmark strips → validation tab. ≤ 4 MB, under 30 s.
- [ ] Decide: does `/demo` get a frozen validation payload? Today it shows no validation at all, so the product's USP is invisible without an account. Log the decision either way; if yes, it is a frozen JSON like the existing demo payload, no API call.

**Exit:** a logged-out visitor can see the verdict card, or DECISIONS.md says why not.

### Phase 3 — One outside user (week 2)

The 15 Sep reversal condition, made concrete.

- [ ] Put Finertia in front of 5 people who are not the author: at least one trader, one finance student, one engineer. The field guide's pitches are the script.
- [ ] For each, record in `planning/feedback.md`: did they finish a run unaided, did they open Validation, what confused them, would they pay $12 / ₹1,000 a month for it.
- [ ] Count sign-ups and runs from Firestore (`users`, `runs`) at the start and end of the phase — the only usage number that exists.

**Exit:** `feedback.md` has 5 entries and the two counts.

### Phase 4 — The decision, revisited (end of milestone)

Not a task; a written decision, with phase 3 as its input.

| If phase 3 shows | Then |
|---|---|
| Nobody returns, nobody would pay | Stay portfolio. Finertia is finished software; maintenance only. |
| Students or educators engage, traders don't | Education path: class accounts, a course built on the write-up. Stripe still off. |
| Two or more would pay | Product path: Stripe live (keys + `STRIPE_WEBHOOK_SECRET`, one real test payment), a support inbox, legal check on SEBI positioning and the Yahoo data licence before charging. |

- [ ] DECISIONS.md entry with the phase 3 numbers and the path chosen.

**Exit:** DECISIONS.md has the entry; BACKLOG reordered to match.

## Definition of done for M10

- [ ] STATUS "Blocked on user" is 0
- [ ] Write-up public, linked, re-run after 28 Sep
- [ ] README has the demo GIF; `/demo` validation decided
- [ ] `feedback.md` with 5 outside users and usage counts
- [ ] Phase 4 decision recorded

## Explicitly not in M10

New strategies · user-written strategies · intraday data · the inverse-vol
weight-path null · Sentry · admin counters · Stripe go-live (unless phase 4
picks the product path). All in BACKLOG.md.
