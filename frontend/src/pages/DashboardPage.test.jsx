import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import demo from "../demoData.json";
import demoValidation from "../demoValidation.json";

const api = vi.hoisted(() => ({
  runBacktest: vi.fn(),
  validateStrategy: vi.fn(),
  runPortfolio: vi.fn(),
  validatePortfolio: vi.fn(),
}));
vi.mock("../api", () => api);

const showToast = vi.hoisted(() => vi.fn());
vi.mock("../hooks/useToast", () => ({ useToast: () => ({ showToast }) }));

// Charts are Recharts and need a real layout engine; their own rendering is
// not what these tests are about.
// vi.mock is hoisted, so one call per module rather than a loop.
const NoChart = vi.hoisted(() => ({ default: () => null }));
vi.mock("../components/EquityCurveChart", () => NoChart);
vi.mock("../components/DrawdownChart", () => NoChart);
vi.mock("../components/MonthlyHeatmap", () => NoChart);
vi.mock("../components/RollingSharpeChart", () => NoChart);
vi.mock("../components/AnnualReturnsChart", () => NoChart);

import DashboardPage from "./DashboardPage";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <DashboardPage />
    </MemoryRouter>
  );
}

async function runAapl() {
  await userEvent.click(screen.getByRole("button", { name: "Run backtest on AAPL" }));
  await screen.findByRole("heading", { name: "AAPL" });
}

function payPlan() {
  const err = new Error("Walk-forward validation and the permutation test are Pro features.");
  err.status = 402;
  return err;
}

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  showToast.mockReset();
  api.runBacktest.mockResolvedValue({ ...demo, ticker: "AAPL" });
});

describe("DashboardPage", () => {
  it("runs the config in the panel and names it in the result header", async () => {
    renderPage();
    await runAapl();
    expect(api.runBacktest).toHaveBeenCalledWith(expect.objectContaining({ ticker: "AAPL" }));
    expect(showToast).toHaveBeenCalledWith(expect.stringMatching(/^AAPL complete/), "success");
  });

  // Tester bugs #6/#7 (12 Oct, fixed in #84): validation used the live ticker
  // box, so clearing it after a run sent an empty request and a free user got
  // "ticker missing" instead of the Pro wall.
  it("validates the run on screen, not the edited panel", async () => {
    api.validateStrategy.mockResolvedValue(demoValidation);
    renderPage();
    await runAapl();

    await userEvent.clear(screen.getByLabelText("Ticker"));
    await userEvent.click(screen.getByRole("tab", { name: /Validation/ }));

    expect(api.validateStrategy).toHaveBeenCalledOnce();
    expect(api.validateStrategy.mock.calls[0][0].ticker).toBe("AAPL");
    // The header still names the run, not the emptied box.
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  });

  it("sends a 402 to the pricing page instead of offering a retry", async () => {
    api.validateStrategy.mockRejectedValue(payPlan());
    renderPage();
    await runAapl();
    await userEvent.click(screen.getByRole("tab", { name: /Validation/ }));

    const banner = await screen.findByRole("alert");
    expect(within(banner).getByText(/Pro features/)).toBeInTheDocument();
    expect(within(banner).getByRole("link", { name: "See Pro" })).toHaveAttribute("href", "/pricing");
    expect(within(banner).queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("offers a retry of the action that failed", async () => {
    api.runBacktest.mockRejectedValueOnce(Object.assign(new Error("Cannot reach the API"), { status: undefined }));
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Run backtest on AAPL" }));
    const banner = await screen.findByRole("alert");
    await userEvent.click(within(banner).getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "AAPL" });
    expect(api.runBacktest).toHaveBeenCalledTimes(2);
  });
});
