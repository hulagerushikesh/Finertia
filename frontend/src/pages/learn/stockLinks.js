/**
 * Each /learn article's "On real stocks" block: one sentence and a few
 * /stocks/<slug> links, picked from the stock pages' own results.
 *
 * Reads only stockIndex.json (through stockMeta.js), which the entry bundle
 * already carries, so the learn pages do not pull in the full results. Like
 * the stock pages, the sentence is derived from the figures, so a re-run of
 * build_stock_pages.py cannot leave it saying something the pages do not.
 */
import { STOCKS, STOCK_PERIOD, signed } from "../../lib/stockMeta";

const bySharpe = (a, b) => b.buy_and_hold_sharpe - a.buy_and_hold_sharpe;
const heldNote = (s) => `${s.held_up} of 3 held up`;
const sharpeNote = (s) => `Sharpe ${signed(s.buy_and_hold_sharpe)} holding it`;
const pick = (slugs) => slugs.map((slug) => STOCKS.find((s) => s.slug === slug)).filter(Boolean);

function validation() {
  const held = STOCKS.reduce((n, s) => n + s.held_up, 0);
  const none = STOCKS.filter((s) => s.held_up === 0).sort(bySharpe);
  const most = Math.max(...STOCKS.map((s) => s.held_up));
  const best = most > 0 ? STOCKS.filter((s) => s.held_up === most) : [];
  return {
    lead:
      `On ${STOCKS.length} US and Indian stocks, ${STOCK_PERIOD.years}, the three rules were each tuned on ` +
      `the first 70% and scored on the rest: ${held} of ${STOCKS.length * 3} held up. On ${none.length} ` +
      `stocks none did, among them ${none[0].name}, which had a Sharpe ratio of ` +
      `${signed(none[0].buy_and_hold_sharpe)} for anyone who simply held it.`,
    stocks: [...best, ...none.slice(0, 4)].map((s) => ({ ...s, note: heldNote(s) })),
  };
}

function sharpe() {
  const sorted = [...STOCKS].sort(bySharpe);
  const [top, bottom] = [sorted[0], sorted[sorted.length - 1]];
  return {
    lead:
      `Simply holding, ${STOCK_PERIOD.years}, ${top.name} had the highest Sharpe ratio of the ` +
      `${STOCKS.length} stocks at ${signed(top.buy_and_hold_sharpe)} and ${bottom.name} the lowest at ` +
      `${signed(bottom.buy_and_hold_sharpe)}. Each page sets the three rules against that figure.`,
    stocks: [...sorted.slice(0, 3), ...sorted.slice(-3)].map((s) => ({ ...s, note: sharpeNote(s) })),
  };
}

function permutation() {
  return {
    lead:
      `Every stock page gives the permutation p-value for all three rules on that stock, ` +
      `${STOCK_PERIOD.years}. The broad indices are a good place to start: there is no single ` +
      `company's news to time.`,
    stocks: pick(["spy", "qqq", "nifty-50", "sensex"]).map((s) => ({ ...s, note: heldNote(s) })),
  };
}

function lookahead() {
  return {
    lead:
      `Every figure on the ${STOCKS.length} stock pages comes from the same engine, with each signal ` +
      `acting on the bar after it is known. If another tool shows a much better result for the ` +
      `same rule on the same stock, that gap is worth the one-day-delay check above.`,
    stocks: pick(["aapl", "nvda", "reliance", "tcs"]).map((s) => ({ ...s, note: heldNote(s) })),
  };
}

const BUILDERS = {
  "walk-forward-validation": validation,
  "backtest-overfitting": validation,
  "sharpe-ratio": sharpe,
  "permutation-test": permutation,
  "lookahead-bias": lookahead,
};

/** { lead, stocks: [{ ...stock, note }] } for an article id, or null. */
export function stockLinks(id) {
  const build = BUILDERS[id];
  return build ? build() : null;
}
