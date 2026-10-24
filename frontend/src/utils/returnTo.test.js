import { describe, it, expect } from "vitest";
import { nextPath, authPath, AFTER_AUTH } from "./returnTo";

describe("nextPath", () => {
  it("returns the path it was given", () => {
    expect(nextPath("?next=%2Fdashboard%3Fticker%3DAAPL%26strategy%3Dmacd")).toBe("/dashboard?ticker=AAPL&strategy=macd");
    expect(nextPath("?next=/history")).toBe("/history");
  });

  it("falls back to the workspace without one", () => {
    expect(nextPath("")).toBe(AFTER_AUTH);
    expect(nextPath("?next=")).toBe(AFTER_AUTH);
  });

  it("refuses anything that leaves the site", () => {
    for (const bad of ["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"]) {
      expect(nextPath(`?next=${encodeURIComponent(bad)}`)).toBe(AFTER_AUTH);
    }
  });

  it("does not send someone back to a form", () => {
    expect(nextPath("?next=/login")).toBe(AFTER_AUTH);
    expect(nextPath("?next=/register?next=/x")).toBe(AFTER_AUTH);
    expect(nextPath("?next=/loginhelp")).toBe("/loginhelp");
  });
});

describe("authPath", () => {
  it("carries next only when it says something", () => {
    expect(authPath("/register", "/dashboard?a=1&b=2")).toBe("/register?next=%2Fdashboard%3Fa%3D1%26b%3D2");
    expect(authPath("/login", AFTER_AUTH)).toBe("/login");
    expect(authPath("/login", null)).toBe("/login");
  });

  it("round-trips through nextPath", () => {
    const next = "/dashboard?ticker=AAPL&strategy=bollinger&bb_std=2.5";
    expect(nextPath(authPath("/register", next).split("?").slice(1).join("?"))).toBe(next);
  });
});
