import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("./firebase", () => ({ app: null, auth: null, db: null }));

const { PAGES, render } = await import("./prerender.jsx");

describe("build-time render of the public pages", () => {
  for (const [name, path] of Object.entries(PAGES)) {
    it(`${name} (${path}): its own heading, visible, signed out`, async () => {
      const html = await render(name);
      expect(html).toMatch(/<h1[\s>]/);
      // A copy still at the start of its entrance motion would be invisible.
      expect(html).not.toMatch(/opacity:\s*0[;"]/);
      expect(html).toContain("Sign in");
      // The page itself, not the 404 or the loading skeleton.
      expect(html).not.toContain("Nothing at this address");
      expect(html).not.toMatch(/<main[^>]*><div class="max-w-6xl mx-auto px-4 py-16"><div class="h-8 w-48/);
    });
  }

  it("covers every page in the sitemap", () => {
    const sitemap = readFileSync(path.resolve(__dirname, "../public/sitemap.xml"), "utf8");
    const listed = [...sitemap.matchAll(/<loc>https:\/\/finertia\.hulage\.in([^<]*)<\/loc>/g)].map((m) => m[1]);
    expect(listed.sort()).toEqual(Object.values(PAGES).sort());
  });
});
