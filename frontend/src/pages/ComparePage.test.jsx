import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// StrategyPage's AuthContext imports the Firebase app, which needs an API key CI does not have.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import ComparePage from "./ComparePage";
import { AuthContext } from "../context/AuthContext";
import StrategyPage from "./StrategyPage";
import results from "../lib/stockResults.json";
import { PAIRS, STOCKS, STRATEGY_LABEL } from "../lib/stockMeta";
import { PAGE_META } from "../lib/pageMeta";

function renderAt(path) {
  return render(
    <AuthContext.Provider value={{ user: null }}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          {PAIRS.map((p) => (
            <Route
              key={p.slug}
              path={p.path}
              element={<ComparePage slug={p.slug} />}
            />
          ))}
          <Route path="/strategies/:id" element={<StrategyPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("compare pages", () => {
  it("has a pre-rendered page for every pair, and no page without one", () => {
    const pages = Object.keys(PAGE_META).filter((k) =>
      k.startsWith("compare-"),
    );
    expect(pages.sort()).toEqual(PAIRS.map((p) => `compare-${p.slug}`).sort());
  });

  for (const p of PAIRS) {
    it(`${p.slug}: names both rules and links every stock`, () => {
      renderAt(p.path);
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        `${p.label}, on ${STOCKS.length} stocks.`,
      );
      const hrefs = screen
        .getAllByRole("link")
        .map((l) => l.getAttribute("href"));
      for (const s of STOCKS) expect(hrefs).toContain(s.path);
      for (const id of [p.a, p.b]) expect(hrefs).toContain(`/strategies/${id}`);
      for (const o of PAIRS.filter((o) => o.slug !== p.slug))
        expect(hrefs).toContain(o.path);
    });
  }

  it("quotes each stock's own figures", () => {
    renderAt("/strategies/momentum-vs-macd");
    const r = results.stocks.nvda.strategies;
    const row = screen.getByRole("link", { name: "Nvidia" }).closest("tr");
    const cells = within(row)
      .getAllByRole("cell")
      .map((c) => c.textContent);
    const fmt = (x) => (x < 0 ? `−${Math.abs(x).toFixed(2)}` : x.toFixed(2));
    expect(cells.slice(1)).toEqual([
      fmt(r.momentum.defaults.sharpe_ratio),
      fmt(r.macd.defaults.sharpe_ratio),
      fmt(r.momentum.walk_forward.out_of_sample_sharpe),
      fmt(r.macd.walk_forward.out_of_sample_sharpe),
    ]);
  });

  it("takes /strategies/<pair> ahead of the /strategies/:id route", () => {
    renderAt("/strategies/macd-vs-bollinger");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      `${STRATEGY_LABEL.macd} vs ${STRATEGY_LABEL.bollinger}`,
    );
  });
});
