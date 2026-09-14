# Decisions

Constraints and reversals, each with the reason. Newest first. If you are about
to "fix" something that looks odd, check here first — it is probably deliberate.

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
