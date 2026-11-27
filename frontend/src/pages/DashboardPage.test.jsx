import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import demo from "../demoData.json";
import demoValidation from "../demoValidation.json";

const api = vi.hoisted(() => ({
  runBacktest: vi.fn(),
  validateStrategy: vi.fn(),
  runPortfolio: vi.fn(),
  validatePortfolio: vi.fn(),
  getUsage: vi.fn(),
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

function limitReached() {
  const err = new Error("You have used your 10 validations for this month.");
  err.status = 402;
  return err;
}

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  showToast.mockReset();
  clearWorkspace();
  api.runBacktest.mockResolvedValue({ ...demo, ticker: "AAPL" });
  // The workspace always asks for the validation allowance; by default there
  // is none to show.
  api.getUsage.mockResolvedValue({ plan: "free", validation: false, validations_used: 0,
    validations_limit: 0, validations_remaining: 0 });
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

  it("sends a 402 to the limits page instead of offering a retry or an upgrade", async () => {
    api.validateStrategy.mockRejectedValue(limitReached());
    renderPage();
    await runAapl();
    await userEvent.click(screen.getByRole("tab", { name: /Validation/ }));

    const banner = await screen.findByRole("alert");
    expect(within(banner).getByText(/validations for this month/)).toBeInTheDocument();
    expect(within(banner).getByRole("link", { name: "See the limits" })).toHaveAttribute("href", "/limits");
    expect(within(banner).queryByRole("button", { name: "Try again" })).toBeNull();
    expect(screen.queryByText(/\bPro\b|upgrade/i)).toBeNull();
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


// The monthly validation allowance (a fair-use limit set on the API).
describe("DashboardPage — the monthly validations", () => {
  const FREE_USAGE = { plan: "free", validation: false, validations_used: 0,
    validations_limit: 1, validations_remaining: 1 };

  async function openValidation() {
    await runAapl();
    await userEvent.click(screen.getByRole("tab", { name: /Validation/ }));
  }

  it("says validation is switched off when the allowance is 0", async () => {
    api.validateStrategy.mockRejectedValue(limitReached());
    renderPage();
    await openValidation();
    expect(await screen.findByRole("link", { name: "Validation is switched off — see the limits" })).toBeInTheDocument();
  });

  it("says after a validation how many are left", async () => {
    api.getUsage.mockResolvedValue(FREE_USAGE);
    api.validateStrategy.mockResolvedValue({ ...demoValidation, free_validations_remaining: 0 });
    renderPage();
    await openValidation();
    expect(await screen.findByTestId("free-validation-used")).toHaveTextContent(
      "0 of 1 validations left this month"
    );
  });

  it("shows the counter beside Run validation", async () => {
    api.getUsage.mockResolvedValue(FREE_USAGE);
    const outage = new Error("Market data unavailable");
    outage.status = 503;
    api.validateStrategy.mockRejectedValue(outage);
    renderPage();
    await openValidation();
    expect(await screen.findByTestId("free-validation-left")).toHaveTextContent(
      "1 of 1 free validation left this month"
    );
  });

  it("names the used-up allowance on a 402, with the limits, not a plan", async () => {
    api.getUsage.mockResolvedValue({ ...FREE_USAGE, validations_used: 1, validations_remaining: 0 });
    api.validateStrategy.mockRejectedValue(limitReached());
    renderPage();
    await openValidation();
    expect(
      await screen.findByRole("link", { name: "This month's validations are used — see the limits" })
    ).toHaveAttribute("href", "/limits");
  });

  it("shows nothing extra to an unlimited account", async () => {
    api.getUsage.mockResolvedValue({ plan: "pro", validation: true, validations_used: 0,
      validations_limit: null, validations_remaining: null });
    api.validateStrategy.mockResolvedValue(demoValidation);
    renderPage();
    await openValidation();
    await screen.findByRole("button", { name: "Re-run checks" });
    expect(screen.queryByTestId("free-validation-used")).toBeNull();
    expect(screen.queryByTestId("free-validation-left")).toBeNull();
  });
});


// Sprint 2 item 3, behind the "onboarding" switch until the round closes.
describe("DashboardPage — examples (switch)", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("offers no examples while the switch is off", () => {
    vi.stubEnv("VITE_FEATURES", "");
    renderPage();
    expect(screen.queryByText("Or start from an example")).toBeNull();
  });

  it("loads an example into the panel without running it", async () => {
    vi.stubEnv("VITE_FEATURES", "onboarding");
    renderPage();
    const cards = screen.getAllByRole("button", { name: "Load this example" });
    expect(cards).toHaveLength(3);
    await userEvent.click(cards[1]);
    expect(screen.getByRole("button", { name: "Run backtest on SPY" })).toBeInTheDocument();
    expect(api.runBacktest).not.toHaveBeenCalled();
  });

  it("says what to look at after running an unchanged example, and not otherwise", async () => {
    vi.stubEnv("VITE_FEATURES", "onboarding");
    api.runBacktest.mockResolvedValue({ ...demo, ticker: "SPY" });
    renderPage();
    await userEvent.click(screen.getAllByRole("button", { name: "Load this example" })[1]);
    await userEvent.click(screen.getByRole("button", { name: "Run backtest on SPY" }));
    expect(await screen.findByTestId("example-look-at")).toHaveTextContent("Validation tab");
  });

  it("shows no note after an ordinary run", async () => {
    vi.stubEnv("VITE_FEATURES", "onboarding");
    renderPage();
    await runAapl();
    expect(screen.queryByTestId("example-look-at")).toBeNull();
  });
});


// A user's own rule (strategy "rules"): validated as written, like any run.
describe("DashboardPage — own rule", () => {
  it("runs the rule, then validates that same rule", async () => {
    api.validateStrategy.mockResolvedValue({ ...demoValidation, strategy: "rules" });
    renderPage({ entry: { pathname: "/dashboard", state: { params: { ...DEFAULTS, strategy: "rules" } } } });
    expect(screen.getByTestId("rule-builder")).toBeInTheDocument();
    await runAapl();
    const sent = expect.objectContaining({ strategy: "rules", rule: expect.objectContaining({ direction: "long" }) });
    expect(api.runBacktest).toHaveBeenCalledWith(sent);
    await userEvent.click(screen.getByRole("tab", { name: /Validation/ }));
    await waitFor(() => expect(api.validateStrategy).toHaveBeenCalledWith(sent));
    expect(await screen.findByText("Above zero")).toBeInTheDocument();
  });
});
