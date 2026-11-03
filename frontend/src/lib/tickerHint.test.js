import { describe, expect, it } from "vitest";
import { withTickerHint } from "./tickerHint";

describe("withTickerHint", () => {
  it("suggests the NSE suffix for a bare symbol", () => {
    expect(withTickerHint("No data found for RELIANCE")).toBe(
      "No data found for RELIANCE. Indian shares need .NS on the end, for example RELIANCE.NS.",
    );
  });

  it("leaves a symbol that already has a suffix alone", () => {
    expect(withTickerHint("No data found for RELIANCE.NS")).toBe("No data found for RELIANCE.NS");
  });

  it("leaves other errors alone", () => {
    expect(withTickerHint("Backtest failed.")).toBe("Backtest failed.");
  });
});
