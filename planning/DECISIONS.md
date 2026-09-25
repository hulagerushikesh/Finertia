# Decisions

Constraints and reversals, each with the reason. Newest first. If you are about
to "fix" something that looks odd, check here first — it is probably deliberate.

## 2026-09-24 — No vol-scaled cost model. The cost LEVEL ships instead

The backlog item asked for costs that scale with volatility: real spreads
widen when vol rises, momentum trades when vol is high, so a flat charge
should flatter it exactly where it hurts. Both halves are true and the
conclusion still does not follow. Two measurements killed it.

**The coefficient is not identifiable from daily OHLCV.** A vol-scaled model
needs k in `cost_t = base * (sigma_t/sigma_ref)^k`, and with free data k can
only come from a high-low spread estimator. Simulating bars whose true spread
is CONSTANT under GARCH vol, then regressing estimated monthly spread on
realised vol in logs — true slope zero by construction — gives Abdi-Ranaldo:

    true spread    5bps   10bps   25bps   50bps   100bps
    measured slope 1.07    0.99    0.86    0.57     0.23

The mechanism, not just the number: when the true spread is small next to
daily vol the estimator returns its own noise floor, and that floor is
proportional to vol. The bias shrinks monotonically as the true spread grows,
which is the pattern above. On real tickers 2010-2025 the same estimator gives
0.73-1.03 — inside the range a constant spread produces — and puts SPY at
24bps and AAPL at 38bps, one to two orders of magnitude too high. Corwin-
Schultz returns a non-positive estimate in 69-96% of months. A regression
whose slope is the same whether or not the effect exists measures nothing.

**It would not matter if it were.** Separate the two channels, because
conflating them is what makes the original claim sound obvious: LEVEL (a model
that charges more on average scores worse) and TIMING (holding total cost paid
fixed, does moving the charge onto high-vol bars hurt). Only TIMING is about
the model's shape. Rescaling each vol-scaled model to pay exactly what the
flat model pays, across three strategies x eight tickers, 2010-2025:

    model                            cost paid vs flat   max |Sharpe shift|
    k = 1                               1.02 - 1.33x           0.002
    k = 2                               1.28 - 2.30x           0.003
    k = 3                               1.88 - 5.32x           0.015
    5x multiplier in top vol decile     1.28 - 1.45x           0.002

The LEVEL channel moves Sharpe by -0.16 to -0.32 per extra 10bps. The shape is
worth about a thirtieth of the level, and that is at k=3 with a crisis
multiplier, neither of which anyone would defend as calibrated.

The reason is structural. Redistributing a fixed cost budget leaves the mean
net return unchanged by construction, so it reaches Sharpe only through the
variance the cost series adds, which is second order next to return variance.
Forced to the absurd extreme — the entire budget charged on the top 1% of vol
bars, ~37 bars in fifteen years — the shift finally reaches 0.157, and it goes
the WRONG WAY: concentrating cost inflates return variance and shrinks
|Sharpe| toward zero, which for a losing strategy is an improvement. The flat
model is not flattering anybody.

Momentum also does not trade especially when vol is high: turnover-weighted
vol ratio 1.07-1.27 against an unweighted 1.06-1.31, and on three of eight
tickers it trades at LOWER vol than average. The premise that survived
measurement was the spread one, not the timing one.

**What ships instead.** If the level is what matters, report the level.
`costs.py` returns the breakeven cost — the per-unit-turnover charge at which
annualised return, and therefore the Sharpe on the page, reaches exactly zero
— plus the ratio of that to what the user assumed, and the metrics at 0x, 0.5x,
1x, 2x and 5x their assumption. Equity ending at 1.0 means sum(log1p(net)) = 0
and every term is non-increasing in cost with at least one strictly
decreasing, so the root is unique and bisection cannot pick the wrong one. On
momentum 20/50/2% at the default 10bps, AAPL breaks even at 19bps — a factor
of 1.9 — and five of the eight tickers tested never had an edge to lose.

**Extended to portfolios, 25 Sep.** A book is affine in cost exactly as one
leg is: its return is `sum_i w_i * leg_net_i`, each leg net is
`gross_i - turnover_i * c`, and nothing that builds those parts reads the cost
— positions, stops and sizing come off the close series, and both weighting
schemes come off the close returns. So the same bisection solves it. That was
the one thing worth checking rather than deriving, since a weighting scheme
that sized off NET returns would break it silently; measured against the real
`combine` at 2e-17 on equal and inverse-vol weights. If a future weighting or
stop ever starts reading the cost, `test_a_book_is_affine_in_cost_like_a_single_leg`
is what fails.

**Not decided.** This says nothing about whether a vol-scaled model is right
in principle; it says the coefficient cannot be measured with free daily data
and that no plausible value changes a Sharpe. Two things would reopen it: a
paid quote or spread feed, which makes k measurable; or a strategy whose
turnover really is concentrated in a handful of high-vol bars, where the
variance channel stops being second order. Neither applies to anything the
product runs today.
## 2026-09-23 — The drawdown interval drops BCa's bias correction, keeps its acceleration

`max_drawdown`'s interval had measured 79% coverage against a nominal 95% since
the bootstrap shipped, flagged in the response and the UI with a note blaming
the resample: a block cannot rebuild a decline longer than itself, so read the
band as "optimistic about long, slow declines". **That note was wrong about the
consequence**, and the three fixes queued against it (longer blocks for path
statistics, a parametric drawdown distribution, an honest one-sided bound) were
all aimed at a band being too narrow.

The band was not too narrow. Against the true sampling distribution it measured
0.2204 wide versus a central-95% range of 0.2255 — 98% — and the estimator was
unbiased (median error 0.0014). The defect was BCa's bias correction. `z0` reads
the share of replicates falling below the observed statistic as evidence that
the *estimator* is biased; for a drawdown that share is set by the block scheme,
so `z0` corrects a bias that is not in the estimator at all. Decomposing the
formula term by term on identical replicates:

    max_drawdown, 400 paths, nominal 95%
    percentile (no z0, no accel)   0.950
    z0 only                        0.823
    acceleration only              0.960
    full BCa                       0.810

The acceleration is not at fault; `z0` accounts for the entire loss. And the
loss is mostly noise rather than drift: `z0` has mean ≈ 0 but sd 0.44–0.63
across generators, and ranges −0.79 to +0.58 on real tickers, so each run got a
large random shift in its band rather than a consistent one. On real data the
bands move 0.045–0.131, in both directions — TSLA's positive `z0` had been
pushing its band shallow.

**Decided**: hold `z0` at zero for path-dependent statistics, keep the
acceleration. Coverage 79% → 95.0%, confirmed on Gaussian GARCH, GARCH t(5) and
a Markov regime-switching generator with no GARCH in it. `calmar_ratio` joins on
its own measurement (0.900 → 0.930), not by analogy — its denominator is the
drawdown. `max_drawdown` leaves `UNDERSTATED`, so the "understates" caveat
disappears from the metrics grid; `annualized_volatility` stays flagged at
73.5%, where the construction genuinely is irrelevant and the regime argument
holds.

**Not decided**: that percentile-type intervals are better in general. Eight of
nine metrics are unaffected either way, and BCa's correction is doing legitimate
work wherever the resample reproduces the estimator's behaviour. The rule is
scoped to statistics built from the *order* of returns, which the block scheme
provably distorts, and `NO_BIAS_CORRECTION` names them explicitly rather than
inferring the set at runtime.

## 2026-09-23 — The Sharpe gap is tested paired, two-sided, on the arithmetic Sharpe

Putting a p-value between the two Sharpe ratios the page already prints forced
three choices. (1) **Paired, not two-sample.** The strategy trades the
benchmark's own asset; treating the series as independent throws away the
shared bars and roughly triples the standard error, so the test would almost
never reject. Ledoit-Wolf (2008) is the paired, HAC version and is what is
implemented — headline p-value from their studentised bootstrap, the normal
one reported beside it so the gap between them is visible. (2) **Two-sided.**
A strategy significantly *worse* than holding the asset is information the
reader wants at least as much as the other direction, and the verdict string
says which way. (3) **The arithmetic Sharpe, mean/σ×√252, not the card's
geometric one.** The delta method is defined on the moments; there is no
matching expansion for annualised-return-over-annualised-vol. The two differ
by 0.05–0.19 on the canonical runs — volatility drag, always in the same
direction — so the block reports the pair it tested and says which pair that
is, rather than borrowing the headline numbers and quietly testing something
else. Bartlett kernel over the faster-converging Parzen and QS for one reason:
its variance estimate cannot come back negative, so there is no clamp hiding a
broken kernel. Not gated behind Pro, for the same reason the confidence
intervals are not: the free tier is the one most likely to read "1.2 against
0.6" as settled.

## 2026-09-21 — The trend label is a fixed ±1σ t-statistic, not a tercile

The second regime axis (open-questions §3) had to say which way the market
was going without inheriting the vol label's relativity. Candidates: terciles
of the trailing 60-day return (balanced by construction, but the middle third
of a bull market is not "flat"), a fixed return threshold (scale-dependent —
a 10% move means different things on T and on BABA), or the t-statistic of
the window's mean daily return, `sum(r) / (std(r) · √n)`, cut at ±1. The
t-statistic was chosen: it is unit-free across tickers, "flat" means the move
is inside one standard deviation of the window's own noise, and it is
deliberately harder to earn in turbulent stretches — a 10% move over 60 days
is a trend at 12% vol and noise at 60%. The cost is imbalance: on a
bull-market stock "down" is rare (AAPL 2018→24: 5% of bars, 62 of the 72 in the
turbulent third), and the vol × trend grid reports such cells by count with
no Sharpe below 21 bars rather than printing a number off a handful of days.
The window ends at the bar it labels, as the vol window does — a description,
not a signal.

## 2026-09-21 — A basket's permutation null re-times every leg on its own

Validation for portfolios needed a definition of "random timing" for a book
before any code (open-questions §2). Two candidates: shuffle each leg's
position series independently with the weight path fixed (null: no leg can
time its own market), or shuffle the weight path with the legs fixed (null: the
allocation rule adds nothing). The first was chosen: it is the direct extension
of the single-ticker test, a one-leg book reproduces `/api/validate` exactly, and
it is the question a user of a shared-parameter strategy is actually asking.
The second is a question about the weighting, only meaningful when weighting is
not equal, and stays unbuilt. Not one shared permutation across legs — that
would let mirror-image legs cancel under the null and read a flat book as
skill. The grid is scored on the book's Sharpe, and the whole-grid benchmark is
holding the basket at the same weights.

## 2026-09-20 — Cloud Run runs as a service account with no project roles

Until rev 00007 the API ran as the default compute service account, which
carries `roles/editor` on the whole project — an RCE in the API would have
owned everything. Rev 00008 runs as `finertia-api-runtime`, which has no
project-level roles; its single grant is `secretmanager.secretAccessor` on
`finertia-sa`. That is enough because the backend never uses the runtime
identity: `firebase_admin_init.py` builds `credentials.Certificate` from the
mounted key JSON, and Firestore, Auth and the price cache all go through that
app. The default compute SA's grant on the secret was removed the same day.

Consequences: `--service-account` is now part of the deploy command (README
and `deploy.yml`, flag for flag); a rollback to 00007 cannot be a traffic
shift, because that revision can no longer read the secret. Rev 00008 is the
same image as 00007, so the `backend-deployed` tag does not move.

## 2026-09-17 — Redesign merged before the Pitch Fest result

The 14 Sep constraint was "nothing that changes what a judge sees merges to
`main` until the result is in". PR #6 merged on 17 Sep, result still pending,
on the user's explicit instruction after the two holds were stated plainly:
the judged `/demo` now shows the new UI, and the logged-in paths on
`firebase/firestore/lite` had not been smoke-tested.

Why it was acceptable: the public routes — including `/demo`, the only link
the judges have — were verified on the preview (contrast, overflow, hit areas,
tooltips on touch, reduced motion); the unverified surface is behind login,
which judges are not expected to cross. Frontend only, so rev 00007 is
untouched and a rollback is one Vercel redeploy of `50877a4`.

What it changes: the "hold until the result" rule is spent; further frontend
work merges on its own merits. The smoke test moves from preview to
production and stays at the top of the blocked-on-user list.

## 2026-09-15 — Finertia is a portfolio piece with a write-up, not a product

M9 phase 4. The fork was portfolio piece vs product. **Portfolio path.**

Inputs on the day: Pitch Fest result not yet in; no evidence of use by anyone
other than the author (the newest `runs` document is the author's, 14 Sep;
the three pre-submission AAPL runs are the only real traffic). No funding,
no second person to read a support inbox, no entity for Stripe payouts.

What the decision changes:

- **Kept live, kept free, kept cost-capped.** The URL is the artefact. Nothing
  is switched off; `min-instances 0` means idle is ₹0.
- **Stripe stays built and unwired.** `plans.py` and `billing.py` remain
  tested; `STRIPE_*` stays unset in prod. Do not spend time on go-live,
  webhooks in prod, or a support address.
- **The write-up is the deliverable** — `planning/write-up.md`, drafted the
  same day. It is the highest-leverage remaining artefact: it turns "I built
  a backtester" into "the best in-sample strategy was the worst out-of-sample
  one, four of five checks said the edge was real, and the verdict inverted
  when the window moved one year".
- **Research items outrank feature items.** Regime-aware walk-forward and
  portfolio-mode validation stay above admin counters, Sentry, and Stripe in
  BACKLOG.md, because they improve the write-up and the product path does not
  exist.
- **The redesign still lands** (PR #6) — a portfolio piece is judged on
  polish too — but it is the last UI investment unless something changes.

What would reverse it: a Pitch Fest placement that brings users, or a second
person willing to own support. Either is a new decision, logged here.

## 2026-09-14 — Docs live in the repo, artifacts are views

`learning/` and `planning/` are the source of truth. The published artifacts
(planning/artifacts.md) are refreshed *from* these files, not the other way
round. Reason: six artifacts had drifted to three different dates and none
mentioned the last four commits.

## 2026-09-14 — `firebase/firestore/lite` on the client

The client only ever does `getDoc` / `setDoc` / `updateDoc` / `serverTimestamp`
on its own profile. The full SDK was ~250 kB minified of websocket, offline
cache and listener code on the landing page. Lite is REST, rules apply
identically. If a realtime listener is ever needed, that is the moment to
switch back — not before.

## 2026-09-14 — motion via `LazyMotion` + `m`, `strict`

Only opacity/transform animate here. `strict` throws on any `motion.*`
element so the full feature set cannot creep back into the entry.

## 2026-09-13 (branch `redesign`) — shadcn/ui adopted, reversing 22 Aug

The 22 Aug decision said no shadcn: 44 components on a bespoke token system,
and shadcn copies source in to be restyled. The redesign branch does it anyway,
with a new "Blue pencil" HSL token sheet, radix primitives, sonner, motion,
next-themes. **Reason for reversal**: the goal moved from "localised edits" to
"real-app polish" (hover cards, dialogs, sheets, command-style selects) — that
bar is easier to hit on radix primitives than by hand. **Condition**: it must
clear every bar the old UI cleared (M9 phase 1 checklist) and not regress the
bundle. If it cannot, the old UI wins.

## 2026-09-08 — Confidence intervals are on every plan, not Pro-gated

Validation is gated for a real cost reason (grid sweep + 500 permutations).
Bootstrap is one resample of a series already in memory, ~50 ms. Gating it
would leave the free tier — the users most likely to take a Sharpe at face
value — as the only ones shown a naked point estimate. If asked to make CIs
paid, push back.

## 2026-09-06 — API reached same-origin via Vercel rewrite, not `*.run.app`

Ad/content blockers block `*.run.app`; every cross-origin call needed a
preflight. `vercel.json` rewrites `/api/*` → Cloud Run. asia-south1 has no
Cloud Run domain mappings (501), so there is no `api.` subdomain and there
will not be one. `ALLOWED_ORIGINS` on the backend is still required.

## 2026-09-06 — Backend deploy is manual, by design

Only Vercel auto-deploys. `gcloud run deploy` is run by hand so a backend
change never silently turns on a meter. Cost: it was forgotten once (5 days of
stale prod). Mitigation in BACKLOG (CI reminder), not automation.

## 2026-09-06 — Cost caps are non-negotiable

`--min-instances 0 --max-instances 2 --memory 512Mi --cpu 1 --concurrency 40`.
Idle = ₹0. No funding; any change that turns on a meter is asked first with a ₹ figure.

## 2026-08-22 — Type scale floor: 11 px for interface text, 10 px for chart internals only

`tick` (10 px) is for axis labels, table headers, heatmap cells — fixed
geometry restating a number shown full-size elsewhere. Test: if a label is the
only place a fact appears, it is not a tick. Zero `text-[...]` escapes; keep it.

## 2026-08-20 — Purge/embargo gap: 1% of period, floor 5, cap 25, symmetric

Floor because 1% of 1y is 3 days, shorter than a holding period. Cap because
past a month it costs more OOS data than the bias it removes. It is *not* a
deflator and must not be described as one (median OOS move +0.014, up in 7 of 12).

## 2026-08-19 — No scipy

Normal CDF via `math.erf`, inverse via Acklam. Keeps the "every formula is
readable source" claim true for the statistics as well as the engine.

## 2026-08-19 — Two-tone palette: violet = measured value, mint = the reference it is tested against

Every screen sets a number beside the thing that tests it. The colour split
teaches the mental model before the copy does. The redesign's token sheet must
preserve this pairing under whatever names it uses.

## 2026-08-15 — Firestore clients can only read their own profile and change `displayName`

Original rules let users write their own profile doc, which held role, plan,
quota → self-promotion. The Admin SDK bypasses rules, so locking clients down
costs the backend nothing. `runs` is closed to clients entirely.

## 2026-08-14 — Portfolio alignment is an inner join

Forward-filling invents flat returns on non-trading days and flatters every
risk metric. Truncation is reported as `dropped_bars` against the longest leg,
not the requested start date.

## 2026-08-14 — Transaction cost on turnover, not per change

`|Δposition| × cost`. A −1→+1 flip pays 2×; fractional vol-target sizing is not
billed a full round trip every bar.

## 2026-08 — Email verification is a nudge, not a gate

No API route requires it. Gating the dashboard would invent a restriction the
backend does not enforce. It protects the password-reset path.

## 2026-07 (founding constraints)

- **Pure pandas + numpy. No backtesting or TA library, ever.** The readable
  maths is the product's moat, not an incidental choice.
- No `<form>` tags — controlled inputs + onClick.
- No Redux/Zustand — useState/useEffect/Context.
- Admin enforced on both sides (`AdminRoute` + `inject_admin`).
- Equity/drawdown arrays are never stored — recomputed on demand.
- Every API error reaches the UI.
- Vite port 5174 pinned (`strictPort`) so it matches `ALLOWED_ORIGINS`.
