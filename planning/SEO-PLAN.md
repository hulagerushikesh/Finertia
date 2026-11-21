# Finertia — search plan (articles + Google)

_Written 21 Nov 2026, at the author's request. **Not part of M13 yet.**
PLAN.md part 7 says "no new pages before 10 Dec", so the build half of this
plan waits for the author's yes (decision S1 below). The Google half needs no
build and can start now._

## 1. Where search stands today

| What | State | Source |
|---|---|---|
| Pages Google can read without running the app | 60, all pre-rendered, each with its own title, description, canonical link, share card and structured data | `frontend/src/lib/pageMeta.js`, `scripts/prerender.mjs` |
| robots.txt and sitemap | Both live; sitemap lists the 60 pages | `frontend/public/` |
| Search Console | Verified for the whole `hulage.in` domain. Sitemap submitted 13 Nov, status Success, 60 discovered | STATUS 13 Nov (B5) |
| Results so far | Finertia: 10 impressions, 0 clicks in 3 months | STATUS 13 Nov (B5) |
| Articles already on the site | 5 explainers under `/learn` (walk-forward, overfitting, lookahead bias, Sharpe ratio, permutation test) | `frontend/src/pages/learn/articles.jsx` |

**What this means.** The technical setup is already done; there is no
missing Google setting that holds the site back. The site gets few
impressions because it has few pages that match what people type, and almost
no other sites link to it. Those two things are what this plan works on.

## 2. Google side — no build, about 30 minutes, ₹0

Done by the author in Search Console (or by Claude in the author's Chrome, on
their yes). None of these change the site.

| # | Step | Why |
|---|---|---|
| G1 | **URL Inspection → Request indexing** for `/`, `/writeup`, `/writeup/nifty-50`, `/demo`, `/learn` | Puts the five most important pages in the queue now instead of waiting for Google to get round to them |
| G2 | **Pages report** (Indexing → Pages), read once a week | Shows which of the 60 pages are indexed and why any are not ("Discovered – not indexed" is normal for a new site) |
| G3 | **Performance report**, filtered to `finertia.hulage.in` | The real scoreboard: queries, impressions, clicks per page. Goes into the Monday read-out (C4) |
| G4 | **Bing Webmaster Tools → Import from Search Console** | Free, two clicks; also feeds DuckDuckGo and ChatGPT search |
| G5 | **Link from the main `hulage.in` site to Finertia and both studies** | Google already knows the main domain (424 impressions there); a link passes that along |

There is no setting that makes Google rank a page higher. Ranking comes from
(a) pages that answer what people search, and (b) other sites linking to
them. Phase C's posts help (b); the articles below help (a).

## 3. Articles — the build half (waits on decision S1)

### Where they live

**Grow `/learn` rather than start a separate `/blogs`.** `/learn` already
has five explainers, already pre-rendered, in the sitemap and allowed in
robots.txt. A second section would split the same kind of page across two
addresses. If the author prefers the word "blog" in the menu, add `/blog` as a
redirect to `/learn` — one address for Google, either word for people.

### What each article must have

- One question a real person types, answered in the first paragraph.
- At least one figure from Finertia's own runs, re-run by a script like the
  studies (PLAN part 7: every quoted figure comes from a script).
- A link to the study it draws on, and a "try it in the demo" link.
- Its own title, description and share card, in the sitemap the same day.
- No advice to buy or sell anything; same tone as the studies.

### First six topics, ordered by how directly they reuse finished work

| # | Working title | Search phrase it aims at | Draws on |
|---|---|---|---|
| W1 | Does a moving-average strategy beat buying the Nifty 50? | nifty 50 strategy backtest | Nifty study |
| W2 | Survivorship bias: why backtesting today's Nifty 50 lies | survivorship bias backtest india | Nifty study (2011 list) |
| W3 | Bollinger Bands on Indian stocks: 15 years of results | bollinger band strategy backtest | Nifty study grid |
| W4 | How to backtest a trading strategy without fooling yourself | how to backtest a trading strategy | Both studies, /demo |
| W5 | MACD strategy: what 15 years of Nifty data say | macd strategy backtest results | Nifty study grid |
| W6 | What brokerage and taxes do to a backtest in India | transaction cost backtest india | cost tolerance numbers |

Pace: one article a week, the author reads each before it goes live (each
quotes the published studies).

### Done when

- Each article is live, pre-rendered, in the sitemap, and requested for
  indexing (G1) on the day it ships.
- After 8 weeks: each article's impressions and clicks are in the read-out.
  Expectation, set now: a new site usually waits 4–12 weeks before articles
  show in results at all, so week-2 numbers prove nothing either way.

## 4. Decisions for the author

| # | Decision | Default if you say nothing |
|---|---|---|
| S1 | ~~Build articles now or after 10 Dec~~ | Decided 21 Nov: **now**. W1 built (PR #198), waiting on the author's read |
| S2 | Section name: grow `/learn` (with `/blog` redirecting to it), or a separate `/blogs` | Grow `/learn` |
| S3 | ~~Who does G1–G5~~ | Decided 21 Nov: Claude in the author's Chrome. Not started: the Chrome extension was not connected to the session |
