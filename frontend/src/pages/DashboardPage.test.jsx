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

// AuthContext imports the Firebase app, which needs an API key CI does not
// have. Only the context object is used here, never the provider.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import DashboardPage from "./DashboardPage";
import { AuthContext } from "../context/AuthContext";
import { DEFAULTS } from "../components/ConfigPanel";
import { clearWorkspace } from "../lib/workspaceStore";

// `entry` is a router location: a path, or { pathname, state } for a re-run
// arriving from History.
function renderPage({ uid = "u1", entry = "/dashboard" } = {}) {
  return render(
    <AuthContext.Provider value={{ user: { uid } }}>
      <MemoryRouter initialEntries={[entry]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DashboardPage />
      </MemoryRouter>
    </AuthContext.Provider>
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
  clearWorkspace();
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

  // Tester report, 13 Oct: going to History and back emptied the workspace,
  // and getting the answer back cost another monthly run.
  describe("leaving and coming back", () => {
    it("shows the run and its validation again without asking the API", async () => {
      api.validateStrategy.mockResolvedValue(demoValidation);
      const first = renderPage();
      await runAapl();
      await userEvent.click(screen.getByRole("tab", { name: /Validation/ }));
      await vi.waitFor(() => expect(showToast).toHaveBeenCalledWith(expect.stringMatching(/^Validation/), "error"));
      first.unmount();

      renderPage();
      expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Validation/ })).toHaveAttribute("aria-selected", "true");
      expect(api.runBacktest).toHaveBeenCalledOnce();
      expect(api.validateStrategy).toHaveBeenCalledOnce();
    });

    it("keeps a result that arrived after the user left", async () => {
      let finish;
      api.runBacktest.mockReturnValue(new Promise((resolve) => (finish = resolve)));
      const first = renderPage();
      await userEvent.click(screen.getByRole("button", { name: "Run backtest on AAPL" }));
      first.unmount();
      finish({ ...demo, ticker: "AAPL" });
      await Promise.resolve();

      renderPage();
      expect(await screen.findByRole("heading", { name: "AAPL" })).toBeInTheDocument();
    });

    it("never shows one account's run to another", async () => {
      const first = renderPage({ uid: "u1" });
      await runAapl();
      first.unmount();

      renderPage({ uid: "u2" });
      expect(screen.queryByRole("heading", { name: "AAPL" })).toBeNull();
    });

    it("starts fresh on a re-run from History", async () => {
      const first = renderPage();
      await runAapl();
      first.unmount();

      renderPage({ entry: { pathname: "/dashboard", state: { params: { ...DEFAULTS, ticker: "MSFT" } } } });
      expect(screen.queryByRole("heading", { name: "AAPL" })).toBeNull();
      expect(screen.getByRole("button", { name: "Run backtest on MSFT" })).toBeInTheDocument();
    });
  });
});
