import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const api = vi.hoisted(() => ({ getHistory: vi.fn(), compareRuns: vi.fn() }));
vi.mock("../api", () => api);
vi.mock("../hooks/useToast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));
vi.mock("../components/ComparisonPanel", () => ({ default: () => null }));

import HistoryPage from "./HistoryPage";

const RUN = {
  id: "r1", ticker: "AAPL", strategy: "momentum", start: "2020-01-01", end: "2024-01-01",
  createdAt: "2026-10-13T10:00:00Z", params: { ticker: "AAPL", strategy: "momentum" },
  metrics: { total_return: 0.1, sharpe_ratio: 0.5, max_drawdown: -0.2 },
};

const renderPage = () => render(
  <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <HistoryPage />
  </MemoryRouter>
);

beforeEach(() => {
  api.getHistory.mockReset();
});
afterEach(() => vi.unstubAllEnvs());

// Sprint 2 item 3, behind the "onboarding" switch until the round closes.
describe("HistoryPage — empty states (switch)", () => {
  it("keeps the plain empty state while the switch is off", async () => {
    vi.stubEnv("VITE_FEATURES", "");
    api.getHistory.mockResolvedValue({ runs: [], total: 0 });
    renderPage();
    expect(await screen.findByText("No runs yet.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open in the workspace" })).toBeNull();
  });

  it("links each example into the workspace when there are no runs", async () => {
    vi.stubEnv("VITE_FEATURES", "onboarding");
    api.getHistory.mockResolvedValue({ runs: [], total: 0 });
    renderPage();
    const links = await screen.findAllByRole("link", { name: "Open in the workspace" });
    expect(links).toHaveLength(3);
    expect(links[1].getAttribute("href")).toMatch(/^\/dashboard\?.*ticker=SPY.*strategy=bollinger/);
  });

  it("says how to get a second run to compare", async () => {
    vi.stubEnv("VITE_FEATURES", "onboarding");
    api.getHistory.mockResolvedValue({ runs: [RUN], total: 1 });
    renderPage();
    expect(await screen.findByTestId("compare-hint")).toHaveTextContent("Compare needs two runs");
  });
});

describe("HistoryPage — portfolio runs", () => {
  const BASKET = {
    runId: "p1", kind: "portfolio", ticker: null, tickers: ["AAPL", "MSFT"], strategy: "momentum",
    start: "2020-01-01", end: "2024-01-01", createdAt: "2026-10-14T10:00:00Z",
    params: { weighting: "equal" }, metrics: { total_return: 0.2, sharpe_ratio: 0.9, max_drawdown: -0.1 },
  };

  it("names the basket and cannot be picked for compare", async () => {
    api.getHistory.mockResolvedValue({ runs: [BASKET, { ...RUN, runId: "r1" }], total: 2 });
    renderPage();
    expect(await screen.findByText("AAPL · MSFT")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /AAPL · MSFT/ })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Select AAPL run for comparison" })).not.toBeDisabled();
  });
});
