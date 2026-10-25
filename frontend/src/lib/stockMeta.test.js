import { describe, it, expect } from "vitest";
import index from "./stockIndex.json";
import results from "./stockResults.json";
import { PAIRS, STOCK_PERIOD, ofThree, percent, signed } from "./stockMeta";

// backend/scripts/build_stock_pages.py `summary`, restated: the index the
// titles quote must be the summary of the results the pages show.
describe("stockIndex.json", () => {
  it("is the summary of stockResults.json", () => {
    expect(index.start).toBe(results.start);
    expect(index.end).toBe(results.end);
    expect(Object.keys(index.stocks)).toEqual(Object.keys(results.stocks));
    for (const [slug, r] of Object.entries(results.stocks)) {
      expect(index.stocks[slug]).toEqual({
        symbol: r.symbol,
        name: r.name,
        market: r.market,
        buy_and_hold_return: r.buy_and_hold.total_return,
        buy_and_hold_sharpe: r.buy_and_hold.sharpe_ratio,
        held_up: Object.values(r.strategies).filter((x) => x.walk_forward.verdict === "held_up").length,
      });
    }
  });

  it("totals each strategy and each pair from the results", () => {
    const stocks = Object.values(results.stocks);
    const ids = Object.keys(stocks[0].strategies);
    for (const id of ids) {
      expect(index.strategies[id]).toEqual({
        held_up: stocks.filter((s) => s.strategies[id].walk_forward.verdict === "held_up").length,
        beat_random: stocks.filter((s) => s.strategies[id].permutation_p < 0.05).length,
      });
    }
    const sharpe = (s, id) => s.strategies[id].defaults.sharpe_ratio;
    expect(PAIRS.map((p) => p.slug)).toEqual(["momentum-vs-macd", "momentum-vs-bollinger", "macd-vs-bollinger"]);
    for (const { a, b, wins } of PAIRS) {
      expect(wins[a]).toBe(stocks.filter((s) => sharpe(s, a) > sharpe(s, b)).length);
      expect(wins[b]).toBe(stocks.filter((s) => sharpe(s, b) > sharpe(s, a)).length);
    }
  });
});

describe("formatting", () => {
  it("prints figures the way the site does", () => {
    expect(percent(5.641)).toBe("564%");
    expect(percent(38.753)).toBe("3,875%");
    expect(percent(-0.314)).toBe("−31%");
    expect(percent(-0.001)).toBe("0%");
    expect(signed(-0.528)).toBe("−0.53");
    expect(signed(-0.001)).toBe("0.00");
    expect(ofThree(0)).toBe("none of the three");
    expect(ofThree(3)).toBe("all three");
  });

  it("names the period by its last full year", () => {
    expect(STOCK_PERIOD.years).toBe("2019–2024");
  });
});
