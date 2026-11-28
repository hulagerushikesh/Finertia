import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";

const api = vi.hoisted(() => ({ runScan: vi.fn(), listRules: vi.fn() }));
vi.mock("../api", () => api);

import ScanPage, { scanSentence } from "./ScanPage";
import { DEFAULTS } from "../components/ConfigPanel";

const row = (ticker, sharpe, extra = {}) => ({
  ticker, status: "ok", total_return: 0.2, hold_total_return: 0.5, sharpe_ratio: sharpe,
  sharpe_vs_hold: -0.3, max_drawdown: -0.25, num_trades: 12, p_value: 0.6,
  beats_holding: false, survives_correction: false, ...extra,
});

const RESULT = {
  universe: "nasdaq100", universe_title: "Nasdaq-100", strategy: "momentum",
  summary: {
    stocks: 4, ran: 3, skipped: 1, made_money: 3, ahead_of_holding: 1,
    tested_against_holding: 3, beats_holding: 1, expected_by_chance: 0.15,
    survives_correction: 0, alpha: 0.05, median_sharpe: 0.4, median_excess_return: -0.3,
  },
  rows: [
    row("AAA", 0.2),
    row("BBB", 0.9, { sharpe_vs_hold: 0.5, p_value: 0.04, beats_holding: true }),
    row("CCC", 0.4),
    { ticker: "DDD", status: "skipped", reason: "DDD has no stored prices for this range yet" },
  ],
};

function Where() {
  const loc = useLocation();
  return <p data-testid="where">{loc.pathname} {loc.state?.params?.ticker} {loc.state?.params?.strategy}</p>;
}

const renderPage = (params = { ...DEFAULTS, strategy: "macd" }) =>
  render(
    <MemoryRouter initialEntries={[{ pathname: "/scan", state: { params } }]}>
      <Routes>
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/dashboard" element={<Where />} />
      </Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  api.runScan.mockReset();
  api.listRules.mockReset();
  api.listRules.mockResolvedValue({ rules: [], max: 20 });
});

describe("ScanPage", () => {
  it("scans the workspace set-up on the chosen index", async () => {
    api.runScan.mockResolvedValue(RESULT);
    renderPage();
    expect(screen.getByText("MACD", { exact: false })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Nasdaq-100" }));
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    expect(api.runScan).toHaveBeenCalledWith(expect.objectContaining({ strategy: "macd" }), "nasdaq100");
    expect(await screen.findByText(/Beat holding the stock on 1 of 3/)).toBeInTheDocument();
    expect(screen.getByText(/chance alone would give less than one/)).toBeInTheDocument();
    expect(screen.getByText(/Skipped: DDD/)).toBeInTheDocument();
  });

  it("sorts by Sharpe, best first, and flips on a second click", async () => {
    api.runScan.mockResolvedValue(RESULT);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    const order = () => screen.getAllByTestId("scan-row").map((r) => within(r).getAllByRole("cell")[0].textContent);
    expect(await screen.findAllByTestId("scan-row")).toHaveLength(3);
    expect(order()).toEqual(["BBB", "CCC", "AAA"]);
    await userEvent.click(screen.getByRole("button", { name: "Sort by Sharpe" }));
    expect(order()).toEqual(["AAA", "CCC", "BBB"]);
  });

  it("opens a stock in the workspace with the same set-up", async () => {
    api.runScan.mockResolvedValue(RESULT);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    await userEvent.click(await screen.findByRole("button", { name: "CCC" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/dashboard CCC macd");
  });

  it("shows the server's refusal", async () => {
    api.runScan.mockRejectedValue(new Error("Too many requests. Try again in 20 second(s)."));
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests");
  });
});

describe("ScanPage — a saved rule", () => {
  const RSI = {
    direction: "long",
    entry: { all: [{ left: { ind: "rsi", n: 14 }, op: "<", right: { value: 30 } }] },
    exit: { all: [{ left: { ind: "rsi", n: 14 }, op: ">", right: { value: 55 } }] },
  };

  it("scans a saved rule with the workspace's dates and costs", async () => {
    api.listRules.mockResolvedValue({ rules: [{ id: "r1", name: "RSI dip", rule: RSI }], max: 20 });
    api.runScan.mockResolvedValue(RESULT);
    renderPage({ ...DEFAULTS, strategy: "macd", start: "2018-01-01", transaction_cost: 0.002 });
    await userEvent.selectOptions(await screen.findByLabelText("What to scan"), "r1");
    expect(screen.getByText("Your rule “RSI dip”")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    expect(api.runScan).toHaveBeenCalledWith(
      expect.objectContaining({ strategy: "rules", rule: RSI, start: "2018-01-01", transaction_cost: 0.002 }),
      "nifty50"
    );
  });

  it("opens a stock from a saved-rule scan with that rule", async () => {
    api.listRules.mockResolvedValue({ rules: [{ id: "r1", name: "RSI dip", rule: RSI }], max: 20 });
    api.runScan.mockResolvedValue(RESULT);
    renderPage();
    await userEvent.selectOptions(await screen.findByLabelText("What to scan"), "r1");
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    await userEvent.click(await screen.findByRole("button", { name: "AAA" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/dashboard AAA rules");
  });

  it("offers no choice when there are no saved rules", async () => {
    renderPage();
    await screen.findByRole("button", { name: "Run scan" });
    expect(screen.queryByLabelText("What to scan")).toBeNull();
  });
});

describe("ScanPage — the S&P 500", () => {
  it("offers the S&P 500 and says it takes longer", async () => {
    let finish;
    api.runScan.mockReturnValue(new Promise((r) => (finish = r)));
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "S&P 500" }));
    await userEvent.click(screen.getByRole("button", { name: "Run scan" }));
    expect(api.runScan).toHaveBeenCalledWith(expect.anything(), "sp500");
    expect(screen.getByRole("status")).toHaveTextContent("up to a minute");
    finish(RESULT);
    expect(await screen.findByText(/Beat holding the stock on 1 of 3/)).toBeInTheDocument();
  });
});

describe("scanSentence", () => {
  it("says when something survives the correction", () => {
    const s = { ...RESULT.summary, tested_against_holding: 50, beats_holding: 6, expected_by_chance: 2.5, survives_correction: 2 };
    expect(scanSentence(s)).toBe(
      "Beat holding the stock on 6 of 50; chance alone would give about 2.5. 2 still stand after correcting for testing 50 stocks at once."
    );
  });
});
