import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

import BenchmarkTest from "./BenchmarkTest";

const TEST = {
  computable: true,
  strategy_sharpe: 0.8,
  benchmark_sharpe: 1.1,
  difference: -0.3,
  standard_error: 0.5,
  significant: false,
  p_value: 0.54,
  p_value_normal: 0.55,
  resamples: 2000,
  block_length: 5,
  verdict: "No evidence either way.",
};

afterEach(() => vi.unstubAllEnvs());

describe("BenchmarkTest Sharpe note", () => {
  it("is hidden while the switch is off", () => {
    vi.stubEnv("VITE_FEATURES", "");
    render(<BenchmarkTest test={TEST} headlineSharpe={0.71} />);
    expect(screen.queryByTestId("sharpe-note")).toBeNull();
  });

  it("names both figures when they differ", () => {
    vi.stubEnv("VITE_FEATURES", "sharpe-note");
    render(<BenchmarkTest test={TEST} headlineSharpe={0.71} />);
    expect(screen.getByTestId("sharpe-note").textContent).toMatch(/Why 0\.80 here and 0\.71 on the card/);
  });

  it("stays quiet when they print the same, or the card has none", () => {
    vi.stubEnv("VITE_FEATURES", "sharpe-note");
    const { rerender } = render(<BenchmarkTest test={TEST} headlineSharpe={0.801} />);
    expect(screen.queryByTestId("sharpe-note")).toBeNull();
    rerender(<BenchmarkTest test={TEST} headlineSharpe={undefined} />);
    expect(screen.queryByTestId("sharpe-note")).toBeNull();
  });
});
