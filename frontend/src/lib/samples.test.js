import { describe, it, expect } from "vitest";
import { SAMPLES, sampleById, sampleFor } from "./samples";
import { DEFAULTS } from "../components/ConfigPanel";
import { STRATEGIES } from "../components/ConfigPanel";
import { encodeParams, decodeParams } from "../utils/permalink";

// The free plan's basket cap (plans.py). An example a new free user cannot
// run would be the worst possible first impression.
const FREE_MAX_HOLDINGS = 3;

describe("sample strategies", () => {
  it("has three, with unique ids", () => {
    expect(SAMPLES).toHaveLength(3);
    expect(new Set(SAMPLES.map((s) => s.id)).size).toBe(3);
  });

  it("covers every strategy the app offers", () => {
    expect(new Set(SAMPLES.map((s) => s.params.strategy))).toEqual(
      new Set(STRATEGIES.map((s) => s.id))
    );
  });

  it.each(SAMPLES.map((s) => [s.id, s]))("%s has its copy", (_, s) => {
    for (const field of ["title", "idea", "look_at"]) {
      expect(typeof s[field]).toBe("string");
      expect(s[field].length).toBeGreaterThan(10);
    }
  });

  it.each(SAMPLES.map((s) => [s.id, s]))("%s survives a share link", (_, s) => {
    // Opening an example has to give the same run a permalink would, or a
    // shared example would silently become a different one.
    const link = encodeParams(s.params);
    const back = decodeParams(link);
    expect(encodeParams(back)).toBe(link);
    expect([back.mode, back.strategy, back.stop_loss]).toEqual(
      [s.params.mode, s.params.strategy, s.params.stop_loss]
    );
  });

  it("keeps baskets inside the free plan", () => {
    for (const s of SAMPLES.filter((x) => x.params.mode === "portfolio")) {
      expect(s.params.tickers.length).toBeLessThanOrEqual(FREE_MAX_HOLDINGS);
    }
  });

  it("finds one by id, and nothing for an unknown id", () => {
    expect(sampleById("basket-with-stop").params.tickers).toEqual(["AAPL", "MSFT", "GOOGL"]);
    expect(sampleById("nope")).toBeNull();
  });

  it("recognises an example only while it is unchanged", () => {
    const s = SAMPLES[1];
    expect(sampleFor(s.params)).toBe(s);
    expect(sampleFor({ ...s.params, bb_std: 2.5 })).toBeNull();
    expect(sampleFor(DEFAULTS)).toBeNull();
    expect(sampleFor(null)).toBeNull();
  });
});
