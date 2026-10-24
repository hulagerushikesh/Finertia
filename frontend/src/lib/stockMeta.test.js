import { describe, it, expect } from "vitest";
import index from "./stockIndex.json";
import results from "./stockResults.json";
import { STOCK_PERIOD, ofThree, percent, signed } from "./stockMeta";

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
