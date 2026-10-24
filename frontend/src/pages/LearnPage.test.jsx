import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// AuthContext imports the Firebase app, which needs an API key CI does not have.
vi.mock("../firebase", () => ({ auth: {}, db: {} }));

import LearnPage from "./LearnPage";
import { ARTICLES } from "./learn/articles";
import { AuthContext } from "../context/AuthContext";
import { PAGE_META } from "../lib/pageMeta";

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

  it("is the 404 for an article that does not exist", () => {
    renderAt("/learn/rsi");
    expect(screen.getByText(/Nothing at this address/)).toBeInTheDocument();
  });
});
