import { describe, it, expect } from "vitest";
import { encodeParams, decodeParams } from "./permalink";
import { DEFAULTS } from "../components/ConfigPanel";

describe("encodeParams", () => {
  it("writes only the selected strategy's knobs", () => {
    const q = new URLSearchParams(encodeParams({ ...DEFAULTS, strategy: "macd" }));
    expect(q.get("macd_fast")).toBe("12");
    expect(q.has("momentum_lookback")).toBe(false);
    expect(q.has("bb_std")).toBe(false);
  });

  it("leaves out volatility knobs under fixed sizing and off stops", () => {
    const q = new URLSearchParams(encodeParams(DEFAULTS));
    expect(q.has("target_vol")).toBe(false);
    expect(q.has("stop_loss")).toBe(false);
  });

  it("writes a portfolio as comma-joined tickers and drops the single ticker", () => {
    const q = new URLSearchParams(
      encodeParams({ ...DEFAULTS, mode: "portfolio", tickers: ["AAPL", "MSFT"], weighting: "equal" })
    );
    expect(q.get("tickers")).toBe("AAPL,MSFT");
    expect(q.has("ticker")).toBe(false);
  });
});

describe("decodeParams", () => {
  it("returns null for an empty query", () => {
    expect(decodeParams("")).toBeNull();
  });

  it("returns null when nothing is recognised", () => {
    expect(decodeParams("?utm_source=x")).toBeNull();
  });

  it("round-trips a config", () => {
    const cfg = { ...DEFAULTS, ticker: "MSFT", strategy: "bollinger", bb_std: 2.5, stop_loss: 0.05 };
    const back = decodeParams(encodeParams(cfg));
    expect(back).toMatchObject({ ticker: "MSFT", strategy: "bollinger", bb_std: 2.5, stop_loss: 0.05 });
  });

  // Sharing a config with stops off must not hand the recipient a default stop.
  it("treats an absent stop as off", () => {
    expect(decodeParams("?ticker=AAPL").stop_loss).toBeNull();
  });

  it("drops numbers that do not parse and upper-cases the ticker", () => {
    const out = decodeParams("?ticker=aapl&transaction_cost=abc");
    expect(out.ticker).toBe("AAPL");
    expect(out.transaction_cost).toBe(DEFAULTS.transaction_cost);
  });

  it("dedupes and caps portfolio tickers, ignoring a list under two", () => {
    expect(decodeParams("?mode=portfolio&tickers=aapl,AAPL,msft").tickers).toEqual(["AAPL", "MSFT"]);
    const many = Array.from({ length: 12 }, (_, i) => `T${i}`).join(",");
    expect(decodeParams(`?tickers=${many}`).tickers).toHaveLength(10);
    expect(decodeParams("?mode=portfolio&tickers=AAPL").tickers).toEqual(DEFAULTS.tickers);
  });

  it("ignores another strategy's keys", () => {
    const out = decodeParams("?strategy=macd&bb_std=9");
    expect(out.bb_std).toBe(DEFAULTS.bb_std);
  });
});
