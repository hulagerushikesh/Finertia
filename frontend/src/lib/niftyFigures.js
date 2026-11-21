/**
 * Figures from the Nifty 50 study, for the /learn articles that quote it.
 *
 * Every value here is copied from planning/research/nifty-funnel.json, the
 * study's saved results, which backend/scripts/reproduce_nifty.py checks.
 * The JSON is 450 kB, too big to ship to a reader, so the page carries these
 * copies and niftyFigures.test.js recomputes each one from the JSON. A re-run
 * that changes a figure fails that test until this file says the same.
 */
export const NIFTY = {
  period: "2011–2025",
  cost: "0.1%",
  stocks: 43,
  missing: 7,
  funnel: { tested: 129, beatInSample: 50, aheadOutOfSample: 7, survives: 4 },
  survivesHalfCost: 4,
  survivesDoubleCost: 3,
  medianInSample: "0.09",
  medianOutOfSample: "−0.18",
  medianHoldOutOfSample: "0.59",
  // Pairs whose unseen-years Sharpe beat holding the same stock, whatever they did on the tuning years.
  beatHoldUnseen: { momentum: 4, macd: 7, bollinger: 4, total: 15 },
  survivors: [
    { stock: "Reliance Communications", strategy: "Momentum", oos: "1.824", hold: "−0.452" },
    { stock: "Reliance Communications", strategy: "MACD", oos: "3.041", hold: "−0.452" },
    { stock: "Reliance Infrastructure", strategy: "MACD", oos: "0.445", hold: "0.366" },
    { stock: "Reliance Power", strategy: "MACD", oos: "0.955", hold: "0.505" },
  ],
  today: { tested: 150, survives: 1 },
};
