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

  // Survivorship: the 2011 list against today's list, same test, same years.
  survivorship: {
    // Funnel on today's list at the default cost; its one survivor.
    todayFunnel: { tested: 150, beatInSample: 33, aheadOutOfSample: 4, survives: 1 },
    todaySurvivor: { stock: "Adani Enterprises", strategy: "Momentum" },
    todaySurvivesDoubleCost: 0,
    // Median Sharpe of simply holding the stock, tuning years, one figure per stock.
    holdTuning2011: "0.28",
    holdTuningToday: "0.51",
    // Stocks whose holding Sharpe on the tuning years was below zero.
    holdNegative2011: 11,
    stocksToday: 50,
    holdNegativeToday: 4,
    // Of the 43 priced 2011 stocks, how many are still on today's list.
    stillInIndex: 25,
    // None of the stocks behind the 2011 survivors is on today's list.
    survivorStocksStillIn: 0,
    missingNames: [
      "Cairn India",
      "HDFC",
      "IDFC",
      "Jaiprakash Associates",
      "Ranbaxy Laboratories",
      "Reliance Capital",
      "Sterlite Industries",
    ],
  },

  // Bollinger bands alone: the 2011 list at three costs, today's list, and
  // the 70 Bollinger settings of the one-stock grid (nifty-grid.json).
  bollinger: {
    settings: 12,
    funnel: { tested: 43, beatInSample: 18, aheadOutOfSample: 1, survives: 0 },
    half: { beatInSample: 21, aheadOutOfSample: 2, survives: 0 },
    double: { beatInSample: 11, aheadOutOfSample: 0, survives: 0 },
    medianInSample: "0.12",
    medianOutOfSample: "−0.22",
    positiveOutOfSample: 14,
    aheadStock: "Steel Authority of India",
    commonPick: { window: 10, width: "2.5", stocks: 15 },
    today: { tested: 50, beatInSample: 12, aheadOutOfSample: 0, survives: 0 },
    grid: {
      stock: "Reliance Industries",
      combinations: 70,
      windows: "5 to 100",
      widths: "1 to 3",
      beatHold: 0,
      holdInSample: "0.553",
      holdOutOfSample: "0.544",
      best: { window: 40, width: "3.0", is: "0.342", oos: "−0.463", rank: 623, of: 834 },
      small: { window: 50, width: "2.5", is: "−0.086", oos: "−0.333" },
      medianOutOfSample: "−0.31",
      positiveOutOfSample: 11,
    },
  },

  // MACD crossover alone: the 2011 list at three costs, today's list, and
  // the 284 MACD settings of the one-stock grid (nifty-grid.json).
  macd: {
    settings: 4,
    funnel: { tested: 43, beatInSample: 15, aheadOutOfSample: 4, survives: 3 },
    half: { beatInSample: 15, aheadOutOfSample: 4, survives: 3 },
    double: { beatInSample: 15, aheadOutOfSample: 4, survives: 3 },
    medianInSample: "0.05",
    medianOutOfSample: "−0.22",
    medianOutOfSampleHalf: "−0.19",
    medianOutOfSampleDouble: "−0.30",
    positiveOutOfSample: 15,
    // Ahead on the later years but not a survivor: failed the Deflated Sharpe only.
    nearMiss: "Tata Motors",
    commonPick: { fast: 16, slow: 34, signal: 9, stocks: 14 },
    today: { tested: 50, beatInSample: 9, aheadOutOfSample: 1, survives: 0 },
    grid: {
      combinations: 284,
      fast: "3 to 25",
      slow: "10 to 100",
      signal: "5 to 15",
      beatHold: 0,
      best: { fast: 5, slow: 60, signal: 5, is: "0.309", oos: "0.199", isRank: 2, oosRank: 13 },
      medianOutOfSample: "−0.17",
      positiveOutOfSample: 43,
    },
  },

  // All 129 pairs on the 2011 list at half, default and double the cost.
  costs: {
    half: { beatInSample: 56, aheadOutOfSample: 8, survives: 4, medianInSample: "0.18", medianOutOfSample: "−0.11", positiveOutOfSample: 50 },
    default: { beatInSample: 50, aheadOutOfSample: 7, survives: 4, medianInSample: "0.09", medianOutOfSample: "−0.18", positiveOutOfSample: 41 },
    double: { beatInSample: 42, aheadOutOfSample: 6, survives: 3, medianInSample: "−0.04", medianOutOfSample: "−0.31", positiveOutOfSample: 33 },
  },
};

/**
 * The /demo run's cost curve (momentum on Apple, from src/demoData.json),
 * copied here so the /learn chunk does not carry the whole demo payload.
 * niftyFigures.test.js checks each value against that file.
 */
export const DEMO_COST = {
  ticker: "AAPL",
  years: "2019–2024",
  trades: 164,
  assumed: "0.1%",
  breakeven: "0.41%",
  headroom: "4.1",
  sharpe: { free: "0.52", half: "0.45", assumed: "0.39", double: "0.26", five: "−0.10" },
};
