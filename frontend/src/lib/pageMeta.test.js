import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { DEFAULT_TITLE, PAGE_META, shellFor, structuredData } from "./pageMeta";

const index = readFileSync(path.resolve(__dirname, "../../index.html"), "utf8");
const vercel = JSON.parse(readFileSync(path.resolve(__dirname, "../../vercel.json"), "utf8"));

describe("page shells", () => {
  for (const [name, meta] of Object.entries(PAGE_META)) {
    it(`${name}: every tag swapped, and vercel.json routes ${meta.path} to it`, () => {
      const html = shellFor(index, meta);
      const url = `https://finertia.hulage.in${meta.path}`;
      expect(html).toContain(`<link rel="canonical" href="${url}"`);
      expect(html).toContain(`property="og:url" content="${url}"`);
      expect(html).toContain(`property="og:image" content="${meta.image}"`);
      expect(html.match(/<title>([^<]*)<\/title>/)[1].replace(/&amp;/g, "&")).toBe(meta.title);
      expect(html).not.toContain('content="https://finertia.hulage.in/"');
      expect(vercel.rewrites).toContainEqual({ source: meta.path, destination: `/${name}.html` });
    });
  }

  it("every page's card is a file in public/ (stock cards: backend/scripts/build_stock_cards.py)", () => {
    for (const meta of Object.values(PAGE_META)) {
      const file = path.resolve(__dirname, "../../public", meta.image.replace("https://finertia.hulage.in/", ""));
      expect(existsSync(file), meta.image).toBe(true);
    }
  });

  it("every page carries its breadcrumb trail, and articles an Article, as JSON-LD", () => {
    for (const meta of Object.values(PAGE_META)) {
      const html = shellFor(index, meta);
      const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => JSON.parse(m[1]));
      const own = blocks.find(Array.isArray);
      const crumbs = own.find((d) => d["@type"] === "BreadcrumbList").itemListElement;
      expect(crumbs.at(-1)).toMatchObject({ name: meta.name, item: `https://finertia.hulage.in${meta.path}` });
      expect(crumbs.every((c) => c.name)).toBe(true);
      const article = own.find((d) => d["@type"] === "Article");
      if (meta.type === "article") expect(article.datePublished).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      else expect(article).toBeUndefined();
    }
  });

  it("an article under a section has three crumbs, the middle one the section", () => {
    const crumbs = structuredData(PAGE_META["learn-lookahead-bias"])[0].itemListElement.map((c) => c.name);
    expect(crumbs).toEqual(["Finertia", "Learn", "Lookahead bias"]);
  });

  it("DEFAULT_TITLE is index.html's title", () => {
    expect(index.match(/<title>([^<]*)<\/title>/)[1]).toBe(DEFAULT_TITLE);
  });

  it("the shell rewrites sit before the catch-all", () => {
    const sources = vercel.rewrites.map((r) => r.source);
    const catchAll = sources.findIndex((s) => s.startsWith("/((?!"));
    for (const meta of Object.values(PAGE_META)) expect(sources.indexOf(meta.path)).toBeLessThan(catchAll);
  });

  it("every other route gets app.html, the shell without pre-rendered content", () => {
    // index.html carries the landing page's content (scripts/prerender.mjs),
    // so serving it on /dashboard would flash the landing page there.
    expect(vercel.rewrites.at(-1)).toEqual({ source: "/((?!assets/|api/).*)", destination: "/app.html" });
  });

  it("a tag that stops matching fails the build instead of shipping the landing card", () => {
    expect(() => shellFor(index.replace(/<link rel="canonical"[^>]*>/, ""), PAGE_META.demo)).toThrow(/canonical/);
  });
});
