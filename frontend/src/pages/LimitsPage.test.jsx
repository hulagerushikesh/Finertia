import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const getPlans = vi.hoisted(() => vi.fn());
vi.mock("../api", () => ({ getPlans }));

import LimitsPage from "./LimitsPage";
import Footer from "../components/Footer";
import PLANS from "../lib/plans.json";

const inRouter = (ui) =>
  render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>);

// Braces matter: a function returned from beforeEach runs as a teardown.
beforeEach(() => {
  getPlans.mockReset();
});

// Personal, non-commercial project on Yahoo data (DECISIONS 24 Nov): nothing
// may read as an offer to buy.
const SALES = /\$\d|₹\d|\bPro\b|upgrade|subscribe|per month|\/ month|checkout/i;

describe("LimitsPage", () => {
  it("lists the free plan's limits before the API answers, and offers nothing for sale", () => {
    getPlans.mockReturnValue(new Promise(() => {}));
    const { container } = inRouter(<LimitsPage />);
    for (const line of PLANS[0].features) expect(screen.getByText(line)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(SALES);
    expect(screen.getByText(/not affiliated with, endorsed by, or connected to Yahoo/)).toBeInTheDocument();
  });

  it("takes the limits the API serves", async () => {
    getPlans.mockResolvedValue({ plans: [{ ...PLANS[0], features: ["7 backtests a month"] }] });
    inRouter(<LimitsPage />);
    expect(await screen.findByText("7 backtests a month")).toBeInTheDocument();
  });
});

describe("Footer", () => {
  it("carries the advice, registration and data disclaimers on every page", () => {
    inRouter(<Footer />);
    const text = screen.getByTestId("disclaimer").textContent;
    expect(text).toMatch(/not investment advice/);
    expect(text).toMatch(/not registered with SEBI/);
    expect(text).toMatch(/not a registered investment adviser in the US/);
    expect(screen.getByText(/Price data from Yahoo Finance/)).toHaveTextContent(/non-commercial/);
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/terms");
    expect(screen.queryByRole("link", { name: /Pricing/ })).toBeNull();
  });
});
