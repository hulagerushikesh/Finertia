/**
 * Title, description and share card for each public page.
 *
 * Link-preview crawlers (LinkedIn, X, WhatsApp, Slack) read the HTML and never
 * run the app, so without this every route shares index.html's card. The build
 * (vite.config.js) writes one copy of index.html per entry here, as
 * dist/<name>.html with the entry's tags swapped in, and vercel.json routes
 * each path to its copy; the app inside is identical. The pages set the same
 * title on the tab once the app is running (usePageTitle).
 *
 * Plain data and string functions only: vite.config.js imports this file in
 * Node, before any alias or browser global exists.
 */
import { STOCKS, STOCK_PERIOD, ofThree, percent, signed } from "./stockMeta.js";

const SITE = "https://finertia.hulage.in";

/** index.html's own title, which every other route keeps. */
export const DEFAULT_TITLE = "Finertia — Test a trading idea before you risk money on it";
const CARD = { image: `${SITE}/og.png`, imageAlt: "Finertia — Test a trading idea before you risk money on it." };

export const PAGE_META = {
  demo: {
    name: "A real result",
    path: "/demo",
    title: "Momentum on Apple, 2019–2024: a real result · Finertia",
    ogTitle: "A real backtest, and whether it holds up.",
    description:
      "A momentum rule on Apple, 2019–2024: the equity curve, drawdowns and returns, then the validation checks that ask whether it was skill or luck. No account needed.",
    ...CARD,
  },
  pricing: {
    name: "Pricing",
    path: "/pricing",
    title: "Pricing · Finertia",
    ogTitle: "Start free. Pay when you want the checks.",
    description:
      "Both plans run the same engine on the same data. Pro adds the tests that tell you whether a result is worth anything, and raises the monthly run quota.",
    ...CARD,
  },
  docs: {
    name: "How it works",
    path: "/docs",
    title: "How it works · Finertia",
    ogTitle: "How Finertia computes every number, and where it can mislead you.",
    description:
      "Every number is computed by hand-written pandas and numpy, with no backtesting library. What those computations do, and where they can mislead you.",
    ...CARD,
  },
  support: {
    name: "Support",
    path: "/support",
    title: "Support · Finertia",
    ogTitle: "When something goes wrong.",
    description:
      "The common errors written out with what actually causes them, and how to reach a person when yours isn't listed.",
    ...CARD,
  },
  writeup: {
    name: "The write-up",
    path: "/writeup",
    type: "article",
    published: "2026-09-15",
    modified: "2026-10-07",
    title: "The best-looking strategy was the worst on new data · Finertia",
    ogTitle: "The best-looking strategy was the worst on new data.",
    description:
      "Three trading rules on Apple, 2018–2024. The one that looked best on the years it was tuned on lost money on the years it never saw. Every figure re-run and checked by a script.",
    image: `${SITE}/og-writeup.png`,
    imageAlt:
      "Sharpe ratios on AAPL 2018–2024. Momentum 0.95 tuned, −0.30 on new data; MACD 0.51, −0.30; Bollinger 0.56, 1.17.",
  },
  strategies: {
    name: "Strategies",
    path: "/strategies",
    title: "Three trading strategies, backtested honestly · Finertia",
    ogTitle: "Three ordinary strategies, and what validation said about them.",
    description:
      "Momentum, MACD and Bollinger bands: the exact rule each one trades, its parameters, and how it held up on data it was never tuned on.",
    ...CARD,
  },
  "strategy-momentum": {
    name: "Momentum",
    path: "/strategies/momentum",
    type: "article",
    published: "2026-10-24",
    title: "Momentum strategy: the exact rule and an honest backtest · Finertia",
    ogTitle: "Momentum: the best-looking rule, until new data.",
    description:
      "The momentum rule with a moving-average trend filter, written out exactly: its parameters, the grid validation sweeps, and how it did on AAPL on years it never saw.",
    ...CARD,
  },
  "strategy-macd": {
    name: "MACD",
    path: "/strategies/macd",
    type: "article",
    published: "2026-10-24",
    title: "MACD crossover strategy: the exact rule and an honest backtest · Finertia",
    ogTitle: "MACD crossover: the rule, and what validation said.",
    description:
      "The MACD crossover rule written out exactly: its three averages, the grid validation sweeps, and how it did on AAPL on years it was never tuned on.",
    ...CARD,
  },
  "strategy-bollinger": {
    name: "Bollinger bands",
    path: "/strategies/bollinger",
    type: "article",
    published: "2026-10-24",
    title: "Bollinger band strategy: the exact rule and an honest backtest · Finertia",
    ogTitle: "Bollinger bands: fading extremes, tested out of sample.",
    description:
      "The Bollinger-band mean-reversion rule written out exactly: its window and band width, the grid validation sweeps, and how it did on AAPL on years it never saw.",
    ...CARD,
  },
  learn: {
    name: "Learn",
    path: "/learn",
    title: "Learn backtesting: overfitting, lookahead bias, walk-forward · Finertia",
    ogTitle: "Before you trust a backtest.",
    description:
      "Short answers to the questions that decide whether a backtest is worth anything: overfitting, lookahead bias, walk-forward validation, the Sharpe ratio and the permutation test.",
    ...CARD,
  },
  "learn-walk-forward-validation": {
    name: "Walk-forward validation",
    path: "/learn/walk-forward-validation",
    type: "article",
    published: "2026-10-24",
    title: "Walk-forward validation for trading strategies, explained · Finertia",
    ogTitle: "Walk-forward validation, and why one split can lie.",
    description:
      "Choose parameters on the past, score them on what came after. How walk-forward validation works, the purge gap at the split, and why one split is not enough.",
    ...CARD,
  },
  "learn-backtest-overfitting": {
    name: "Backtest overfitting",
    path: "/learn/backtest-overfitting",
    type: "article",
    published: "2026-10-24",
    title: "How to tell if a backtest is overfit · Finertia",
    ogTitle: "How to tell if a backtest is overfit.",
    description:
      "Four checks for an overfit trading strategy: walk-forward, the deflated Sharpe ratio, the probability of backtest overfitting and a permutation test, with a real example.",
    ...CARD,
  },
  "learn-lookahead-bias": {
    name: "Lookahead bias",
    path: "/learn/lookahead-bias",
    type: "article",
    published: "2026-10-24",
    title: "Lookahead bias in backtesting: the one-day shift · Finertia",
    ogTitle: "Lookahead bias: the one-day shift that invents returns.",
    description:
      "Lookahead bias is a backtest trading on information it could not have had. The one-line bug behind most of it, its quieter forms, and how to check your own results.",
    ...CARD,
  },
  "learn-sharpe-ratio": {
    name: "Sharpe ratio",
    path: "/learn/sharpe-ratio",
    type: "article",
    published: "2026-10-24",
    title: "Sharpe ratio for backtests: what it measures, when it misleads · Finertia",
    ogTitle: "The Sharpe ratio: what it measures and when it misleads.",
    description:
      "What the Sharpe ratio measures, what a good one looks like on daily data, and four ways it flatters a backtest: short periods, parameter sweeps, fat tails and in-sample numbers.",
    ...CARD,
  },
  "learn-permutation-test": {
    name: "Permutation test",
    path: "/learn/permutation-test",
    type: "article",
    published: "2026-10-24",
    title: "Permutation test for trading strategies: skill or exposure? · Finertia",
    ogTitle: "The permutation test: skill, or just time in the market?",
    description:
      "Shuffle a strategy's positions 500 times and see whether its real timing beats random timing. How the permutation test works, how to read its p-value, and its limits.",
    ...CARD,
  },
  stocks: {
    name: "Stocks",
    path: "/stocks",
    title: `Backtests on ${STOCKS.length} well-known stocks, validated · Finertia`,
    ogTitle: "Three strategies on well-known stocks, tested on data they never saw.",
    description: `Momentum, MACD and Bollinger bands on ${STOCKS.length} US and Indian stocks and indices, ${STOCK_PERIOD.years}: each against buy-and-hold, and each validated on years it was never tuned on.`,
    ...CARD,
  },
  // One page per stock in stockIndex.json (backend/scripts/build_stock_pages.py).
  ...Object.fromEntries(
    STOCKS.map((s) => [
      `stock-${s.slug}`,
      {
        name: s.name,
        path: s.path,
        type: "article",
        published: "2026-10-24",
        title: `${s.label} backtest: momentum, MACD and Bollinger, ${STOCK_PERIOD.years} · Finertia`,
        ogTitle: `${s.label}: three strategies, tested on data they never saw.`,
        description:
          `Holding ${s.name} from ${STOCK_PERIOD.years.replace("–", " to ")} returned ${percent(s.buy_and_hold_return)} ` +
          `(Sharpe ${signed(s.buy_and_hold_sharpe)}). Momentum, MACD and Bollinger bands, validated walk-forward: ` +
          `${ofThree(s.held_up)} held up on years they were never tuned on.`,
        ...CARD,
      },
    ])
  ),
};

const attr = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
const text = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

/** The tag swaps that turn index.html into one page's shell. */
function swaps(m) {
  const url = `${SITE}${m.path}`;
  return [
    [/<title>[^<]*<\/title>/, `<title>${text(m.title)}</title>`],
    [/(<link rel="canonical" href=")[^"]*/, `$1${url}`],
    [/(name="description"\s+content=")[^"]*/, `$1${attr(m.description)}`],
    [/(property="og:type" content=")[^"]*/, `$1${m.type || "website"}`],
    [/(property="og:title" content=")[^"]*/, `$1${attr(m.ogTitle)}`],
    [/(property="og:description"\s+content=")[^"]*/, `$1${attr(m.description)}`],
    [/(property="og:url" content=")[^"]*/, `$1${url}`],
    [/(property="og:image" content=")[^"]*/, `$1${m.image}`],
    [/(property="og:image:alt" content=")[^"]*/, `$1${attr(m.imageAlt)}`],
    [/(name="twitter:image" content=")[^"]*/, `$1${m.image}`],
    [/(name="twitter:title" content=")[^"]*/, `$1${attr(m.ogTitle)}`],
    [/(name="twitter:description"\s+content=")[^"]*/, `$1${attr(m.description)}`],
  ];
}

const ORG = { "@type": "Organization", name: "Finertia", url: SITE };

/**
 * schema.org data for one page: its breadcrumb trail (Finertia, then any
 * section the path sits under, then the page), and for articles an Article.
 * The site-wide SoftwareApplication stays in index.html.
 */
export function structuredData(m) {
  const sections = m.path.split("/").slice(1, -1).map((seg) => `/${seg}`);
  const trail = [
    { name: "Finertia", path: "/" },
    ...sections.map((path) => ({ name: Object.values(PAGE_META).find((p) => p.path === path).name, path })),
    { name: m.name, path: m.path },
  ];
  const data = [
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: trail.map((c, i) => ({ "@type": "ListItem", position: i + 1, name: c.name, item: `${SITE}${c.path}` })),
    },
  ];
  if (m.type === "article") {
    data.push({
      "@context": "https://schema.org",
      "@type": "Article",
      headline: m.ogTitle,
      description: m.description,
      url: `${SITE}${m.path}`,
      mainEntityOfPage: `${SITE}${m.path}`,
      image: m.image,
      datePublished: m.published,
      dateModified: m.modified || m.published,
      author: ORG,
      publisher: ORG,
    });
  }
  return data;
}

/** A JSON-LD script tag; `<` escaped so no string in it can close the tag. */
const ldScript = (data) =>
  `<script type="application/ld+json">${JSON.stringify(data).replace(/</g, "\\u003c")}</script>\n  </head>`;

/**
 * index.html with one page's tags swapped in. Throws when a tag no longer
 * matches: that would silently ship the landing card on this page.
 */
export function shellFor(html, m) {
  for (const [re, to] of swaps(m)) {
    if (!re.test(html)) throw new Error(`no match for ${re} in index.html (${m.path})`);
    html = html.replace(re, to);
  }
  if (!html.includes("</head>")) throw new Error(`no </head> in index.html (${m.path})`);
  return html.replace("</head>", () => ldScript(structuredData(m)));
}
