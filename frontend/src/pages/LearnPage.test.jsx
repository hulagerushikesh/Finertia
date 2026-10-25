import { describe, it, expect, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// AuthContext imports the Firebase app, which needs an API key CI does not have.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import LearnPage from "./LearnPage";
import { ARTICLES } from "./learn/articles";
import { AuthContext } from "../context/AuthContext";
import { PAGE_META } from "../lib/pageMeta";
import { STOCKS } from "../lib/stockMeta";
import { stockLinks } from "./learn/stockLinks";

function renderAt(path) {
  return render(
    <AuthContext.Provider value={{ user: null }}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/learn/:id" element={<LearnPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("learn pages", () => {
  it("has a pre-rendered page for every article, and no page without one", () => {
    const pages = Object.values(PAGE_META).filter((m) => m.path.startsWith("/learn/")).map((m) => m.path);
    expect(pages.sort()).toEqual(ARTICLES.map((a) => a.path).sort());
  });

  it("lists every article on /learn", () => {
    renderAt("/learn");
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    for (const a of ARTICLES) expect(hrefs).toContain(a.path);
  });

  for (const a of ARTICLES) {
    it(`${a.id}: renders its title and links to the others`, () => {
      renderAt(a.path);
      expect(screen.getByRole("heading", { level: 1, name: a.title })).toBeInTheDocument();
      const hrefs = screen.getAllByRole("link").map((l) => l.getAttribute("href"));
      for (const o of ARTICLES.filter((o) => o.id !== a.id)) expect(hrefs).toContain(o.path);
    });
  }

  it("quotes the write-up's figures, not stale copies", () => {
    renderAt("/learn/walk-forward-validation");
    expect(screen.getByText(/scored 0\.949 and then −0\.303 on 2022–2023/)).toBeInTheDocument();
  });

  it("links every article to stock pages that exist", () => {
    const paths = new Set(STOCKS.map((s) => s.path));
    for (const a of ARTICLES) {
      const { stocks } = stockLinks(a.id);
      expect(stocks.length, a.id).toBeGreaterThanOrEqual(4);
      for (const s of stocks) expect(paths.has(s.path), `${a.id} -> ${s.path}`).toBe(true);
      renderAt(a.path);
      const hrefs = screen.getAllByRole("link").map((l) => l.getAttribute("href"));
      for (const s of stocks) expect(hrefs).toContain(s.path);
      expect(hrefs).toContain("/stocks");
      cleanup();
    }
  });

  it("derives the stock sentences from the index", () => {
    const held = STOCKS.reduce((n, s) => n + s.held_up, 0);
    expect(stockLinks("walk-forward-validation").lead).toContain(`${held} of ${STOCKS.length * 3} held up`);
    const top = [...STOCKS].sort((a, b) => b.buy_and_hold_sharpe - a.buy_and_hold_sharpe)[0];
    expect(stockLinks("sharpe-ratio").lead).toContain(`${top.name} had the highest Sharpe`);
  });

  it("is the 404 for an article that does not exist", () => {
    renderAt("/learn/rsi");
    expect(screen.getByText(/Nothing at this address/)).toBeInTheDocument();
  });
});
