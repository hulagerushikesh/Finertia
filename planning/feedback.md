# Outside-user feedback — M10 phase 3

Five people who are not the author: at least one trader, one finance student,
one engineer. **Exit:** five entries below and both usage counts filled in.

## Usage counts

Taken with `backend/scripts/usage_counts.py` (read-only, prints no emails),
author's account excluded:

```bash
cd backend && .venv/bin/python scripts/usage_counts.py --since 2026-10-07 --exclude <your email>
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

1. Send the message for their type (below). Live is better than async: a call
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
**Admin → Users → Give Pro**. It is stamped `planSource: "admin"`, and
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
> pandas/numpy with ~600 tests, and every figure in the write-up is checked
> by a script. Would you try it for 15 minutes as a user, not a reviewer, and
> tell me where it lost you? https://finertia.hulage.in/demo

**Anyone else**
> I built a website that tells you whether a trading idea would have
> worked, and whether that was luck. Could you try it for 10 minutes while I
> watch and say what's confusing? https://finertia.hulage.in

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

_(fill in after entry 5: patterns, not anecdotes. This is the input to phase 4.)_
