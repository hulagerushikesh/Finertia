import { describe, it, expect } from "vitest";
import { formatDay, presetRange, matchingPreset, describeRange, todayISO } from "./dates";

describe("formatDay", () => {
  // Tester bug #2 (12 Oct): 06/01/2024 read as 1 June. A spelled-out month cannot be.
  it("spells out the month", () => {
    expect(formatDay("2024-01-06")).toBe("6 Jan 2024");
    expect(formatDay("2024-06-01")).toBe("1 Jun 2024");
  });

  it("rejects things that are not dates", () => {
    expect(formatDay("")).toBe("");
    expect(formatDay("2024-02-30")).toBe("");
    expect(formatDay("06/01/2024")).toBe("");
  });
});

describe("todayISO", () => {
  it("uses the local calendar day", () => {
    expect(todayISO(new Date(2026, 9, 3, 23, 59))).toBe("2026-10-03");
  });
});

describe("presetRange", () => {
  it("ends today and starts N years back", () => {
    expect(presetRange(5, "2026-10-13")).toEqual({ start: "2021-10-13", end: "2026-10-13" });
  });

  it("steps 29 Feb back to 28 Feb in a non-leap year", () => {
    expect(presetRange(1, "2028-02-29").start).toBe("2027-02-28");
    expect(presetRange(4, "2028-02-29").start).toBe("2024-02-29");
  });
});

describe("matchingPreset", () => {
  it("finds the preset a range came from", () => {
    expect(matchingPreset("2023-10-13", "2026-10-13", "2026-10-13")).toBe("3y");
  });

  it("returns null for a hand-picked range or an old end date", () => {
    expect(matchingPreset("2023-10-12", "2026-10-13", "2026-10-13")).toBeNull();
    expect(matchingPreset("2022-10-12", "2025-10-12", "2026-10-13")).toBeNull();
  });
});

describe("describeRange", () => {
  const today = "2026-10-13";

  it("puts the range in words with its length", () => {
    expect(describeRange("2020-01-01", "2024-01-01", today)).toEqual({
      words: "1 Jan 2020 → 1 Jan 2024",
      span: "4 years · ~1,008 trading days",
      problem: null,
    });
    expect(describeRange("2024-01-01", "2024-01-06", today).span).toBe("5 days · ~3 trading days");
    expect(describeRange("2025-10-13", today, today).span).toMatch(/^1 year ·/);
  });

  it("flags a backwards range, a future end, and a missing date", () => {
    expect(describeRange("2024-06-01", "2024-01-06", today).problem).toMatch(/before the end/);
    expect(describeRange("2024-01-01", "2026-10-14", today).problem).toMatch(/future/);
    expect(describeRange("", "2024-01-06", today).problem).toMatch(/Pick both/);
  });
});
