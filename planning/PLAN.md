# Finertia — the plan from 12 Nov 2026

_Written 12 Nov 2026. This file replaces [ROADMAP.md](ROADMAP.md) and
[NEXT-MILESTONE.md](NEXT-MILESTONE.md) as the place to look for "what are we
doing and why". Those two stay as the record of M11 and M12. Detail on what
is live stays in [STATUS.md](STATUS.md); reasons stay in
[DECISIONS.md](DECISIONS.md)._

**How to use it.** The author reads parts 1–4 (two minutes). Claude reads the
whole file at the start of every session and follows part 7 for how to work
and how to reply.

---

## 1. The goal

Finertia is a **portfolio piece**: one live URL that shows the author can
build a full product and do honest quantitative research. That was decided
on 31 Oct, after five testers tried it and none came back.

A portfolio piece is only worth something when **people who matter read
it**. So the goal for the next stretch is not more building:

> **By 10 Dec 2026, strangers have read the two studies, and the project
> can be judged in five minutes by someone who has never seen it.**

_Assumption to confirm (part 6, decision 1): the readers who matter are
people hiring for quant or full-stack roles, and people who trade._

## 2. Where the project stands

| Area | State | Evidence |
|---|---|---|
| Product | Live and complete for its purpose: backtests, portfolios, six validation checks, history, accounts | 856 backend, 342 frontend, 26 end-to-end tests; CI green |
| Research | Two published studies. Apple: the checks disagree and the verdict flips with the window. Nifty 50: of 129 strategies, 4 survive | Every figure is re-run by a script (174 and 68 figures match) |
| Operations | One server in the US, backups, alerts, ₹0 when idle | Restore drill done; uptime alert proven |
| Public pages | 60 pages for search: strategies, 39 stocks, five explainers, two studies | All pre-rendered, each with a share card |
| Users | 5 sign-ups from friends, **0 returned**, nobody said they would pay | Tester round closed 31 Oct |
| Readers | **Counting from 13 Nov** with the host's cookie-free counter (B2) | — |
| Money | Payments, licensed data and the legal review are **off** | DECISIONS 31 Oct |

**What is strong:** the engineering and the honesty of the research.
**What is missing:** an audience, and any way to tell if one exists.

**Loose ends from the last sprint**

1. ~~The status update (pull request #185) is not merged.~~ Merged 13 Nov.
2. ~~The old Mumbai server is still running as a rollback.~~ Deleted 13 Nov.
3. ~~Two things were never looked at signed in.~~ Both seen working 13 Nov.
4. ~~The README still calls the project a "SaaS" and does not mention the
   Nifty study.~~ Rewritten 13 Nov (B1).

## 3. The plan — M13 "Make the work seen" (13 Nov → 10 Dec)

Three phases, in order. **You** marks what only the author can do.

### Phase A — Close out (13–16 Nov)

| # | Item | Done when | You |
|---|---|---|---|
| A1 | ✅ 13 Nov · Merge the status update and this plan | Both on the main branch | Say "approve" |
| A2 | ✅ 13 Nov · Delete the Mumbai server | Only one server holds production settings; site health still passes | One command, on your yes |
| A3 | ✅ 13 Nov · The two signed-in looks | Both seen working on the live site, or a defect logged and fixed | 5 minutes signed in, or let Claude drive your Chrome |
| A4 | ✅ 13 Nov · Archive M12; trim STATUS to one screen at the top | STATUS "At a glance" fits one screen; history moved below | — |

### Phase B — Make it judgeable in five minutes (17–23 Nov)

| # | Item | Done when | You |
|---|---|---|---|
| B1 | Built 13 Nov, waiting on the author's read · **README as the front door**: what it is, the two findings with one chart each, how to check the figures, then the engineering. No "SaaS" | A stranger can say what the project found after reading the first screen | Read it once |
| B2 | Built 13 Nov, waiting on the dashboard switch · **Count visitors**, without cookies or personal data | Daily visits per page visible for `/writeup`, `/writeup/nifty-50`, `/demo` | Turn it on in the hosting dashboard (decision 2) |
| B3 | ✅ 13 Nov · **Landing page points at the studies** first, the tool second | Both studies are one click from the home page, above the fold | — |
| B4 | **Link the Nifty study back** to the first one in its own text | Link present on the live page | Yes needed: it edits a published essay |
| B5 | **Search Console check** | Sitemap accepted; a list of which pages get impressions | Share the screen or the numbers |

### Phase C — Put it in front of people (24 Nov → 10 Dec)

| # | Item | Done when | You |
|---|---|---|---|
| C1 | **Three drafts of the Nifty finding**: a LinkedIn post, a longer post for a trading forum, a one-paragraph note for direct messages | Drafts in `planning/outreach/`, each with the funnel image | Edit in your own voice |
| C2 | **Post them**, one channel per week | Three posts live, links recorded with dates | **You post.** Claude never posts or messages for you |
| C3 | **Send the direct note to 10 people** who hire or trade | 10 sent, replies recorded | You send |
| C4 | **Weekly read-out** every Monday: visits, where from, replies | One row per week in part 5 | — |
| C5 | **Fix what readers trip on** | Each reported problem logged in `feedback.md` and fixed | Forward what people say |

### Standing maintenance (through the whole plan)

- Once a month: re-run both figure checks and the stock pages check; fix or
  note any drift from the price source.
- Cost stays ₹0 idle. Any spend is a decision for the author.
- Bugs get fixed when found, unless the fix collides with work in flight.

## 4. What happens on 10 Dec — rule fixed now

Fixed before any post goes out, so the result cannot be argued with later.
Counts are for 24 Nov → 10 Dec, the author's own visits excluded.

| Result | Then |
|---|---|
| **300 or more visitors** to the two studies together, **or 2 or more replies from strangers** that engage with the content | **Write study 3.** Pick from the list below; plan and thresholds written before the run, as with Nifty |
| Fewer than that, but one channel clearly worked | One more month on that channel only. No new building |
| Neither | **Freeze.** Monthly maintenance only. The project is finished as a portfolio piece, and that is a fine ending |

**Study 3 candidates** (do not start before 10 Dec):

1. Do the four Nifty survivors hold on 2026 data they have never seen?
2. The same funnel on the S&P 100 as it stood in 2011.
3. A rolling walk-forward for baskets (the gap named in the first study).

## 5. Scoreboard

Claude fills one row every Monday in phase C.

| Week of | Visitors, both studies | Top source | Replies from strangers | Posts live |
|---|---|---|---|---|
| 24 Nov | | | | |
| 1 Dec | | | | |
| 8 Dec | | | | |

## 6. Decisions needed from the author

| # | Decision | Default if you say nothing | Needed by |
|---|---|---|---|
| 1 | Who should read this: hiring managers, traders, or both? | Both; the drafts lead with the finding, not the code | 17 Nov |
| 2 | ~~Visitor counting: the host's built-in counter (free, no cookies)~~ | Decided 13 Nov: yes | — |
| 3 | ~~Delete the Mumbai server~~ | Decided 13 Nov: deleted | — |
| 4 | The 10 Dec thresholds in part 4 | As written | 23 Nov |
| 5 | Hours per week you can give | 3 hours: mostly editing and posting | 17 Nov |

## 7. Instructions to Claude

### Before doing anything

1. Read this file and the top table of STATUS.md.
2. Find the first unfinished item in part 3. Work on that, unless the author
   asks for something else.
3. If the author's request is outside this plan, do it, then say in the
   "Next" paragraph which plan item is still waiting.

### What not to build

No new strategies, indicators, pages or features. No payments, licensed
data or legal work. No study 3 before 10 Dec. If a request needs one of
these, say it is outside the plan and ask once.

### What needs the author's yes, every time

- Any change to production settings, servers or data; any backend deploy.
- Editing either published study.
- Anything that costs money.
- Posting, emailing or messaging anyone. Claude drafts; the author sends.
- Deleting anything that cannot be restored.

Claude merges its own pull requests when the checks pass, without asking.

### How to reply — every time, nothing more

1. **Opening sentence:** `Completed the **<what>** and pushed <where>.`
   Or `… — nothing pushed.`
2. **3–5 bullets**, one short line each. A result, not a step. The key
   number or outcome in bold.
3. **Details line:** one link to where the details live, then what stayed
   unchanged.
4. **`**Next <item id and name>:**`** a short paragraph: what comes next,
   what it waits on, and one honest sentence on what this work does not
   prove.
5. **Last line in bold:** `**Nothing needed from you right now.**` or the
   one thing the author must do.

Rules for the reply:

- It fits on one screen. If it does not, cut it.
- Plain sentences for someone who is not an engineer. No file lists, no
  script names, no command output, no revision ids.
- Nothing written between steps while working. One reply per turn.
- Name the plan item by its id (A2, B1, C4) so the author always knows
  where the project is.
- If nothing was done because a decision is missing, the whole reply is the
  question, in two lines.

### When the author must run a command

Stop all other work. Send only: one sentence on why and what it costs, the
terminal tab to open, the command in a code block, and
`**Say "done" when it finishes.**` Then wait. Do not watch the terminal. A
list of commands is given once and never repeated.

### Keeping this file true

- When an item is done, mark it ✅ with the date in part 3, in the same pull
  request as the work.
- When something is decided, add a dated entry to DECISIONS.md and update
  part 6.
- Do not add new items to part 3 without the author's yes. New ideas go to
  BACKLOG.md.
- Every figure quoted anywhere must come from a script that can re-run it.
  Built and verified are different claims; say which.
