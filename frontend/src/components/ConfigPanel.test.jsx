import { describe, it, expect, vi, afterEach } from "vitest";
import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConfigPanel, { DEFAULTS } from "./ConfigPanel";
import { todayISO, presetRange } from "../utils/dates";

function Harness({ initial = DEFAULTS, onRun = () => {}, loading = false }) {
  const [params, setParams] = useState(initial);
  return (
    <>
      <ConfigPanel params={params} setParams={setParams} onRun={onRun} loading={loading} />
      <output data-testid="state">{JSON.stringify(params)}</output>
    </>
  );
}
const state = () => JSON.parse(screen.getByTestId("state").textContent);

describe("ConfigPanel", () => {
  // Labels are tied to their inputs (#88), which screen readers and the E2E suite rely on.
  it("labels the ticker and date inputs", () => {
    render(<Harness />);
    expect(screen.getByLabelText("Ticker")).toHaveValue("AAPL");
    expect(screen.getByLabelText("Start")).toHaveValue(DEFAULTS.start);
    expect(screen.getByLabelText("End")).toHaveValue(DEFAULTS.end);
  });

  it("names the ticker on the run button and runs on click", async () => {
    const onRun = vi.fn();
    render(<Harness onRun={onRun} />);
    await userEvent.click(screen.getByRole("button", { name: "Run backtest on AAPL" }));
    expect(onRun).toHaveBeenCalledOnce();
  });

  it("switches strategy", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "MACD" }));
    expect(state().strategy).toBe("macd");
  });

  it("blocks the run and says why when the MACD fast EMA is not shorter than the slow", () => {
    render(<Harness initial={{ ...DEFAULTS, strategy: "macd", macd_fast: 30, macd_slow: 26 }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Fast EMA must be shorter than the slow EMA.");
    expect(screen.getByRole("button", { name: /^Run backtest/ })).toBeDisabled();
  });

  it("blocks a take-profit no further than the stop", () => {
    render(<Harness initial={{ ...DEFAULTS, stop_loss: 0.05, take_profit: 0.05 }} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/Take profit must be further/);
  });

  it("is disabled and says so while a run is in flight", () => {
    render(<Harness loading />);
    expect(screen.getByRole("button", { name: /Running/ })).toBeDisabled();
  });

  it("Reset restores the defaults", async () => {
    render(<Harness initial={{ ...DEFAULTS, ticker: "MSFT", strategy: "bollinger" }} />);
    await userEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(state()).toEqual(DEFAULTS);
  });

  // Tester bug #2 (12 Oct): the pickers follow the browser's locale, so the
  // range is repeated in words that cannot be misread.
  it("spells the range out beside the pickers", () => {
    render(<Harness initial={{ ...DEFAULTS, start: "2024-01-01", end: "2024-01-06" }} />);
    expect(screen.getByTestId("range-words")).toHaveTextContent("1 Jan 2024 → 6 Jan 2024 · 5 days · ~3 trading days");
  });

  it("a preset sets the last N years ending today and shows as pressed", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Last 5 years" }));
    expect(state()).toMatchObject(presetRange(5, todayISO()));
    expect(screen.getByRole("button", { name: "Last 5 years" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Last 1 year" })).toHaveAttribute("aria-pressed", "false");
  });

  it("blocks a backwards range before it reaches the server", () => {
    render(<Harness initial={{ ...DEFAULTS, start: "2024-06-01", end: "2024-01-06" }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Start date must be before the end date.");
    expect(screen.getByRole("button", { name: /^Run backtest/ })).toBeDisabled();
  });
});
