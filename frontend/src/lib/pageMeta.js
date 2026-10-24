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

const SITE = "https://finertia.hulage.in";

/** index.html's own title, which every other route keeps. */
export const DEFAULT_TITLE = "Finertia — Test a trading idea before you risk money on it";
const CARD = { image: `${SITE}/og.png`, imageAlt: "Finertia — Test a trading idea before you risk money on it." };

export const PAGE_META = {
  demo: {
    path: "/demo",
    title: "Momentum on Apple, 2019–2024: a real result · Finertia",
    ogTitle: "A real backtest, and whether it holds up.",
    description:
      "A momentum rule on Apple, 2019–2024: the equity curve, drawdowns and returns, then the validation checks that ask whether it was skill or luck. No account needed.",
    ...CARD,
  },
  pricing: {
    path: "/pricing",
    title: "Pricing · Finertia",
    ogTitle: "Start free. Pay when you want the checks.",
    description:
      "Both plans run the same engine on the same data. Pro adds the tests that tell you whether a result is worth anything, and raises the monthly run quota.",
    ...CARD,
  },
  docs: {
    path: "/docs",
    title: "How it works · Finertia",
    ogTitle: "How Finertia computes every number, and where it can mislead you.",
    description:
      "Every number is computed by hand-written pandas and numpy, with no backtesting library. What those computations do, and where they can mislead you.",
    ...CARD,
  },
  support: {
    path: "/support",
    title: "Support · Finertia",
    ogTitle: "When something goes wrong.",
    description:
      "The common errors written out with what actually causes them, and how to reach a person when yours isn't listed.",
    ...CARD,
  },
  writeup: {
    path: "/writeup",
    type: "article",
    title: "The best-looking strategy was the worst on new data · Finertia",
    ogTitle: "The best-looking strategy was the worst on new data.",
    description:
      "Three trading rules on Apple, 2018–2024. The one that looked best on the years it was tuned on lost money on the years it never saw. Every figure re-run and checked by a script.",
    image: `${SITE}/og-writeup.png`,
    imageAlt:
      "Sharpe ratios on AAPL 2018–2024. Momentum 0.95 tuned, −0.30 on new data; MACD 0.51, −0.30; Bollinger 0.56, 1.17.",
  },
  strategies: {
    path: "/strategies",
    title: "Three trading strategies, backtested honestly · Finertia",
    ogTitle: "Three ordinary strategies, and what validation said about them.",
    description:
      "Momentum, MACD and Bollinger bands: the exact rule each one trades, its parameters, and how it held up on data it was never tuned on.",
    ...CARD,
  },
  "strategy-momentum": {
    path: "/strategies/momentum",
    title: "Momentum strategy: the exact rule and an honest backtest · Finertia",
    ogTitle: "Momentum: the best-looking rule, until new data.",
    description:
      "The momentum rule with a moving-average trend filter, written out exactly: its parameters, the grid validation sweeps, and how it did on AAPL on years it never saw.",
    ...CARD,
  },
  "strategy-macd": {
    path: "/strategies/macd",
    title: "MACD crossover strategy: the exact rule and an honest backtest · Finertia",
    ogTitle: "MACD crossover: the rule, and what validation said.",
    description:
      "The MACD crossover rule written out exactly: its three averages, the grid validation sweeps, and how it did on AAPL on years it was never tuned on.",
    ...CARD,
  },
  "strategy-bollinger": {
    path: "/strategies/bollinger",
    title: "Bollinger band strategy: the exact rule and an honest backtest · Finertia",
    ogTitle: "Bollinger bands: fading extremes, tested out of sample.",
    description:
      "The Bollinger-band mean-reversion rule written out exactly: its window and band width, the grid validation sweeps, and how it did on AAPL on years it never saw.",
    ...CARD,
  },
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

/**
 * index.html with one page's tags swapped in. Throws when a tag no longer
 * matches: that would silently ship the landing card on this page.
 */
export function shellFor(html, m) {
  for (const [re, to] of swaps(m)) {
    if (!re.test(html)) throw new Error(`no match for ${re} in index.html (${m.path})`);
    html = html.replace(re, to);
  }
  return html;
}
