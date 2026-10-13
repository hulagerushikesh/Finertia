import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { exportMetrics, exportTrades } from "./csv";

// Capture what would be downloaded instead of downloading it.
let saved;
beforeEach(() => {
  saved = [];
  vi.stubGlobal("URL", {
    createObjectURL: (blob) => {
      saved.push({ blob });
      return "blob:x";
    },
    revokeObjectURL: () => {},
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
    saved[saved.length - 1].name = this.download;
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// jsdom's Blob has no .text(); FileReader it is.
const read = (blob) =>
  new Promise((resolve) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.readAsText(blob);
  });

const params = { ticker: "AAPL", start: "2020-01-01", end: "2024-01-01" };

describe("csv export", () => {
  it("names the file after the run and writes one row per trade", async () => {
    exportTrades({ trades: [{ date: "2020-01-02", position: 1, daily_return: 0.01, equity: 1.01 }] }, params);
    expect(saved[0].name).toBe("finertia_trades_AAPL_2020-01-01_2024-01-01.csv");
    expect(await read(saved[0].blob)).toBe("date,position,daily_return,equity\n2020-01-02,1,0.01,1.01");
  });

  it("quotes fields with commas or quotes, and blanks null", async () => {
    exportMetrics({ metrics: { note: 'a, "b"', empty: null } }, params);
    const text = await read(saved[0].blob);
    expect(text).toContain('note,"a, ""b"""');
    expect(text).toContain("empty,\n");
  });

  it("strips characters that are unsafe in a file name", () => {
    exportTrades({ trades: [] }, { ...params, ticker: "../BRK B" });
    expect(saved[0].name).toBe("finertia_trades_..BRKB_2020-01-01_2024-01-01.csv");
  });
});
