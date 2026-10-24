import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// AuthContext imports the Firebase app, which needs an API key CI does not have.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import StrategyPage from "./StrategyPage";
import { AuthContext } from "../context/AuthContext";

function renderAt(path, user = null) {
  return render(
    <AuthContext.Provider value={{ user }}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/strategies" element={<StrategyPage />} />
          <Route path="/strategies/:id" element={<StrategyPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("strategy pages", () => {
  it("lists the three strategies on /strategies", () => {
    renderAt("/strategies");
    for (const path of ["/strategies/momentum", "/strategies/macd", "/strategies/bollinger"]) {
      expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === path)).toBe(true);
    }
  });

  it("writes out the rule, the grid and the write-up's result", () => {
    renderAt("/strategies/macd");
    expect(screen.getByRole("heading", { level: 1, name: "MACD." })).toBeInTheDocument();
    expect(screen.getByText(/best in-sample combination on the first window was 16 \/ 34 \/ 9/)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "MACD validation grid" }).children).toHaveLength(4);
    expect(screen.getByText("−0.300")).toBeInTheDocument();
  });

  it("opens the same set-up in the workspace for a signed-in user", () => {
    renderAt("/strategies/bollinger", { uid: "u1" });
    const href = screen.getByRole("link", { name: "Open in the workspace" }).getAttribute("href");
    expect(href).toMatch(/^\/dashboard\?/);
    const q = new URLSearchParams(href.split("?")[1]);
    expect([q.get("ticker"), q.get("strategy"), q.get("start")]).toEqual(["AAPL", "bollinger", "2018-01-01"]);
  });

  // Signing up on the way must not lose the set-up (utils/returnTo.js).
  it("carries the same set-up through registration for a visitor", () => {
    renderAt("/strategies/macd");
    const href = screen.getByRole("link", { name: "Create a free account" }).getAttribute("href");
    expect(href).toMatch(/^\/register\?next=/);
    const next = new URLSearchParams(href.split("?")[1]).get("next");
    expect(next).toMatch(/^\/dashboard\?/);
    expect(new URLSearchParams(next.split("?")[1]).get("strategy")).toBe("macd");
  });

  it("is the 404 for a strategy that does not exist", () => {
    renderAt("/strategies/rsi");
    expect(screen.getByText(/Nothing at this address/)).toBeInTheDocument();
  });
});
