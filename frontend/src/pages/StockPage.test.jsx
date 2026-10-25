import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// AuthContext imports the Firebase app, which needs an API key CI does not have.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import StockPage from "./StockPage";
import { AuthContext } from "../context/AuthContext";
import results from "../lib/stockResults.json";
import { STOCKS } from "../lib/stockMeta";

function renderAt(path, user = null) {
  return render(
    <AuthContext.Provider value={{ user }}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/stocks" element={<StockPage />} />
          <Route path="/stocks/:slug" element={<StockPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("stock pages", () => {
  it("lists every stock on /stocks", () => {
    renderAt("/stocks");
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    for (const s of STOCKS) expect(hrefs).toContain(s.path);
  });

  it("says any ticker runs in the workspace, through sign-up for a visitor", () => {
    renderAt("/stocks");
    expect(screen.getByText(/a sample, not a limit/)).toBeInTheDocument();
    // authPath leaves out next= when it is the default landing, /dashboard.
    expect(screen.getByRole("link", { name: "workspace" })).toHaveAttribute("href", "/register");
  });

  for (const s of STOCKS) {
    it(`${s.slug}: renders its own figures`, () => {
      renderAt(s.path);
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(s.label);
      const r = results.stocks[s.slug];
      // The buy-and-hold row quotes this stock's result, not another's.
      const row = screen.getByText("Buy and hold").closest("tr");
      expect(row).toHaveTextContent(`${Math.round(Math.abs(r.buy_and_hold.total_return) * 100).toLocaleString("en-US")}%`);
    });
  }

  it("Indian tickers read without the exchange suffix, and an index without a symbol", () => {
    expect(STOCKS.find((s) => s.slug === "reliance").label).toBe("Reliance Industries (RELIANCE)");
    expect(STOCKS.find((s) => s.slug === "nifty-50").label).toBe("Nifty 50");
    expect(STOCKS.find((s) => s.slug === "spy").label).toBe("S&P 500 ETF (SPY)");
  });

  it("opens each strategy on this stock through sign-up for a visitor", () => {
    renderAt("/stocks/reliance");
    const href = screen.getByRole("link", { name: "MACD on Reliance Industries" }).getAttribute("href");
    const next = new URLSearchParams(href.split("?").slice(1).join("?")).get("next");
    const q = new URLSearchParams(next.split("?")[1]);
    expect([q.get("ticker"), q.get("strategy"), q.get("start"), q.get("end")]).toEqual(["RELIANCE.NS", "macd", "2019-01-01", "2025-01-01"]);
  });

  it("is the 404 for a stock without a page", () => {
    renderAt("/stocks/zzzz");
    expect(screen.getByText(/Nothing at this address/)).toBeInTheDocument();
  });
});
