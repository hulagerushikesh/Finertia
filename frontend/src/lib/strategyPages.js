/**
 * What the public strategy pages (/strategies, /strategies/:id) say about each
 * strategy.
 *
 * The rules are written from backend/signals.py, the defaults are
 * ConfigPanel's, and the validation grids are the backend's own
 * (strategyGrids.json, kept equal to backend/strategies.py by
 * backend/tests/test_strategies.py). The AAPL figures are the write-up's,
 * which reproduce_writeup.py re-runs; strategyPages.test.js checks each one
 * against planning/write-up.md so a re-run that changes them cannot leave
 * these pages quoting the old numbers.
 */
import grids from "./strategyGrids.json";

/** The set-up the write-up's first table ran, for "run it yourself". */
const WRITEUP_RUN = { ticker: "AAPL", start: "2018-01-01", end: "2024-01-01" };

export const STRATEGY_PAGES = [
  {
    id: "momentum",
    kind: "Trend following",
    summary:
      "Buys a stock that has been rising and sits above its moving average; sells it short on the mirror condition.",
    rule: [
      "Long when the return over the lookback is above the threshold and the close is above its moving average.",
      "Short when the return over the lookback is below minus the threshold and the close is below its moving average.",
      "Flat otherwise.",
    ],
    why:
      "The moving average is a trend filter: it stops the rule buying a bounce inside a downtrend. The threshold keeps it out of the market when the price is drifting rather than moving.",
    params: [
      ["momentum_lookback", "Lookback", "20 days", "How far back the return is measured."],
      ["ma_window", "Moving average", "50 days", "The trend filter's window."],
      ["momentum_threshold", "Threshold", "2%", "How large that return must be before the rule takes a position."],
    ],
    cell: (c) => `lookback ${c.momentum_lookback} · MA ${c.ma_window}`,
    writeup: {
      best: "lookback 20 / MA 200",
      first: { is: "0.949", oos: "−0.303", verdict: "failed" },
      moved: { is: "0.766", oos: "0.547", verdict: "held up" },
    },
    misleads:
      "Trend following earns in sustained moves and is whipsawed in choppy markets, so its result depends on which of the two a test period happens to contain. On AAPL it failed on 2022–2023 and held up once 2024's uptrend was in the test half. One good run says more about the period than about the rule.",
  },
  {
    id: "macd",
    kind: "Trend following",
    summary:
      "Long while the MACD line is above its signal line, short while it is below: a smoothed trend signal.",
    rule: [
      "The MACD line is the fast exponential average of the close minus the slow one; the signal line is an exponential average of the MACD line.",
      "Long while the MACD line is above the signal line, short while it is below.",
      "Flat for the first slow-window days, while the averages still mostly reflect the starting price.",
    ],
    why:
      "It holds the crossover state rather than trading only on the day of the crossing, so it is always in the market once warmed up, and its position series can be compared day by day with momentum's.",
    params: [
      ["macd_fast", "Fast average", "12 days", "Span of the faster exponential average."],
      ["macd_slow", "Slow average", "26 days", "Span of the slower one, and the warm-up."],
      ["macd_signal", "Signal line", "9 days", "Span of the average of the MACD line."],
    ],
    cell: (c) => `${c.macd_fast} / ${c.macd_slow} / ${c.macd_signal}`,
    writeup: {
      best: "16 / 34 / 9",
      first: { is: "0.511", oos: "−0.300", verdict: "failed" },
      moved: { is: "0.656", oos: "−0.114", verdict: "failed" },
    },
    misleads:
      "Being always in the market means paying for every flip between long and short, so costs matter more here than for the other two. And with only four combinations to choose from it looks hard to overfit, yet on the later AAPL window the probability that its in-sample pick was overfit came out at 0.77.",
  },
  {
    id: "bollinger",
    kind: "Mean reversion",
    summary:
      "Buys when the price falls below its lower band and shorts when it rises above the upper one: it fades extremes.",
    rule: [
      "The bands are the moving average plus and minus a number of standard deviations of the close over the same window.",
      "Long while the close is below the lower band, short while it is above the upper band.",
      "Flat as soon as the close is back inside, which is most of the time.",
    ],
    why:
      "It is the opposite stance to momentum on purpose. Running the two on the same data is the quickest way to see how much a result depends on which question the rule asks.",
    params: [
      ["bb_window", "Window", "20 days", "Window of the average and of the standard deviation."],
      ["bb_std", "Band width", "2σ", "How many standard deviations the bands sit from the average."],
    ],
    cell: (c) => `${c.bb_window} days · ${c.bb_std}σ`,
    writeup: {
      best: "window 50 / 2.5σ",
      first: { is: "0.558", oos: "1.169", verdict: "held up" },
      moved: { is: "0.686", oos: "−0.157", verdict: "failed" },
    },
    misleads:
      "Mean reversion earns in chop and sells every rally in a sustained uptrend. Because it is flat most of the time, few trades decide its result, and on AAPL its entries could not be told apart from shuffled ones (permutation test, p 0.066).",
  },
].map((s) => ({
  ...s,
  label: grids[s.id].label,
  grid: grids[s.id].grid,
  path: `/strategies/${s.id}`,
  run: { ...WRITEUP_RUN, strategy: s.id },
}));

export function strategyPage(id) {
  return STRATEGY_PAGES.find((s) => s.id === id) || null;
}
