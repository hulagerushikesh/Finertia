/**
 * The stocks with a /stocks/<slug> page, and the few figures their titles quote.
 *
 * stockIndex.json and stockResults.json are both written by
 * backend/scripts/build_stock_pages.py, from the real route handlers on a
 * fresh download; stockMeta.test.js checks the index is the summary of the
 * results. This file reads only the index because pageMeta.js imports it, and
 * pageMeta.js is in the landing page's bundle. The full results load with the
 * stock pages (StockPage.jsx).
 *
 * Plain data and string functions only, like pageMeta.js: vite.config.js
 * imports it in Node.
 */
import index from "./stockIndex.json";

const year = (iso) => Number(iso.slice(0, 4));

/** The period every stock page covers. The end date is exclusive, so a 1 January end is the year before. */
export const STOCK_PERIOD = {
  start: index.start,
  end: index.end,
  years: `${year(index.start)}–${index.end.endsWith("-01-01") ? year(index.end) - 1 : year(index.end)}`,
};

/** RELIANCE.NS reads as RELIANCE; an index symbol like ^NSEI is left out. */
function displaySymbol(symbol) {
  if (symbol.startsWith("^")) return null;
  return symbol.replace(/\.NS$/, "");
}

export const STOCKS = Object.entries(index.stocks).map(([slug, s]) => {
  const ticker = displaySymbol(s.symbol);
  return {
    slug,
    ...s,
    path: `/stocks/${slug}`,
    label: ticker && !s.name.includes(ticker) ? `${s.name} (${ticker})` : s.name,
  };
});

/** A signed figure as the site prints it, with a true minus sign. */
export function signed(x, digits = 2) {
  const s = Math.abs(x).toFixed(digits);
  return x < 0 && Number(s) !== 0 ? `−${s}` : s;
}

/** 5.641 → "564%", 38.753 → "3,875%". */
export function percent(x) {
  const s = `${Math.abs(Math.round(x * 100)).toLocaleString("en-US")}%`;
  return x < 0 && Math.round(x * 100) !== 0 ? `−${s}` : s;
}

/** "none of the three", "one of the three", ... */
export function ofThree(n) {
  return n === 3 ? "all three" : `${["none", "one", "two"][n]} of the three`;
}

/** How the strategies are named in prose. The ids are backend/strategies.py's. */
export const STRATEGY_LABEL = { momentum: "Momentum", macd: "MACD", bollinger: "Bollinger bands" };

/** Per strategy, across every stock: walk-forward runs that held up, and permutation p-values under 0.05. */
export const STRATEGY_TOTALS = index.strategies;

/**
 * The /strategies/<a>-vs-<b> pages, one per pair. `wins[id]` is how many stocks
 * that strategy had the higher Sharpe ratio on at its default settings.
 */
export const PAIRS = Object.entries(index.pairs).map(([slug, wins]) => {
  const [a, b] = slug.split("-vs-");
  return { slug, a, b, wins, path: `/strategies/${slug}`, label: `${STRATEGY_LABEL[a]} vs ${STRATEGY_LABEL[b]}` };
});
