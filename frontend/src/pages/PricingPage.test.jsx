import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const api = vi.hoisted(() => ({ getPlans: vi.fn(), startCheckout: vi.fn() }));
vi.mock("../api", () => api);
vi.mock("../hooks/useToast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));
// AuthContext imports the Firebase app, which needs an API key CI does not have.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import PricingPage from "./PricingPage";
import { AuthContext } from "../context/AuthContext";

const PLANS = [
  { id: "free", label: "Free", price_monthly: 0, features: ["50 backtests a month"] },
  { id: "pro", label: "Pro", price_monthly: 12, features: ["Validation"] },
];

function renderPage({ billing, user = null }) {
  api.getPlans.mockResolvedValue({ plans: PLANS, billing_enabled: billing });
  return render(
    <AuthContext.Provider value={{ user }}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <PricingPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

async function proCard() {
  const label = await screen.findByText("Pro", { selector: "p" });
  return label.closest("div.relative");
}

// A block body: a function returned from beforeEach is run as its teardown,
// and mockReset returns the mock, so the arrow form called getPlans after
// every test.
beforeEach(() => {
  api.getPlans.mockReset();
});

// Author, 13 Oct: with billing off, the Pro card's button made a free account
// and, signed in, read "Billing is not enabled on this deployment".
describe("Pro card while billing is off", () => {
  it("says coming soon and offers no way to 'buy' Pro", async () => {
    renderPage({ billing: false });
    const card = await proCard();
    expect(within(card).getByText("Coming soon")).toBeInTheDocument();
    expect(within(card).queryByText("Recommended")).toBeNull();
    expect(within(card).queryByRole("link", { name: "Create an account" })).toBeNull();
    expect(within(card).getByRole("link", { name: "support@hulage.in" })).toHaveAttribute("href", "mailto:support@hulage.in");
    expect(screen.queryByText(/Cancelling keeps Pro/)).toBeNull();
  });

  it("drops the developer wording for a signed-in user", async () => {
    renderPage({ billing: false, user: { uid: "u1" } });
    const card = await proCard();
    expect(within(card).getByText("Coming soon")).toBeInTheDocument();
    expect(screen.queryByText(/Billing is not enabled/)).toBeNull();
    expect(within(card).queryByRole("button", { name: "Upgrade to Pro" })).toBeNull();
  });
});

describe("Pro card once billing is on", () => {
  it("is recommended and sells Pro", async () => {
    renderPage({ billing: true, user: { uid: "u1" } });
    const card = await proCard();
    expect(within(card).getByText("Recommended")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Upgrade to Pro" })).toBeInTheDocument();
    expect(screen.getByText(/Cancelling keeps Pro/)).toBeInTheDocument();
  });
});

// The page starts from the build's copy of the plans (src/lib/plans.json), so
// the pre-render has the cards and a cold API is not a page of skeletons.
describe("before and without the API", () => {
  it("shows the plans before /api/plans answers, with Pro not on sale", async () => {
    let answer;
    api.getPlans.mockReturnValue(new Promise((resolve) => (answer = resolve)));
    render(
      <AuthContext.Provider value={{ user: null }}>
        <MemoryRouter>
          <PricingPage />
        </MemoryRouter>
      </AuthContext.Provider>
    );
    expect(screen.getByText("Pro", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("Unlimited backtests")).toBeInTheDocument();
    expect(screen.getByText("Coming soon")).toBeInTheDocument();
    answer({ plans: PLANS, billing_enabled: false });
    expect(await screen.findByText("50 backtests a month")).toBeInTheDocument();
  });

  it("keeps the plans and offers a retry when the API fails", async () => {
    api.getPlans.mockRejectedValue(new Error("Network error"));
    render(
      <AuthContext.Provider value={{ user: null }}>
        <MemoryRouter>
          <PricingPage />
        </MemoryRouter>
      </AuthContext.Provider>
    );
    expect(await screen.findByText("Try again")).toBeInTheDocument();
    expect(screen.getByText("Unlimited backtests")).toBeInTheDocument();
    expect(screen.getByText("$12")).toBeInTheDocument();
  });
});
