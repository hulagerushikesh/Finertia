import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const getUsage = vi.hoisted(() => vi.fn());
vi.mock("../api", () => ({ getUsage }));

import UsageMeter from "./UsageMeter";

const FREE = {
  plan: "free",
  plan_label: "Free",
  period: "2026-10",
  used: 41,
  limit: 50,
  remaining: 9,
  validation: false,
  max_portfolio_size: 3,
};

const renderMeter = () => render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <UsageMeter />
    </MemoryRouter>
  );

// Braces matter: a function returned from beforeEach runs as a teardown, and
// mockReset() returns the mock itself.
beforeEach(() => {
  getUsage.mockReset();
});

describe("UsageMeter", () => {
  it("shows runs left, the Pro-only note and the plans link on Free", async () => {
    getUsage.mockResolvedValue(FREE);
    renderMeter();
    expect(await screen.findByText("9 left")).toBeInTheDocument();
    expect(screen.getByText("Pro only")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Compare plans/ })).toHaveAttribute("href", "/pricing");
  });

  // Amber before the wall, not at it.
  it("turns the bar amber at 80% and red at the limit", async () => {
    getUsage.mockResolvedValue(FREE);
    const { container, unmount } = renderMeter();
    await screen.findByText("9 left");
    expect(container.querySelector(".bg-warn")).toHaveStyle({ width: "82%" });
    unmount();

    getUsage.mockResolvedValue({ ...FREE, used: 50, remaining: 0 });
    const again = renderMeter();
    await screen.findByText("0 left");
    expect(again.container.querySelector(".bg-loss")).toHaveStyle({ width: "100%" });
  });

  it("shows no bar and no upsell on an uncapped plan", async () => {
    getUsage.mockResolvedValue({ ...FREE, plan: "pro", plan_label: "Pro", limit: null, validation: true });
    renderMeter();
    expect(await screen.findByText(/no limit/)).toBeInTheDocument();
    expect(screen.getByText("included")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Compare plans/ })).toBeNull();
  });

  it("says why when usage cannot load", async () => {
    getUsage.mockRejectedValue(new Error("Cannot reach the API"));
    renderMeter();
    expect(await screen.findByText(/Could not load usage — Cannot reach the API/)).toBeInTheDocument();
  });
});
