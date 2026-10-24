import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { DEFAULT_TITLE, PAGE_META, shellFor } from "./pageMeta";

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

  it("DEFAULT_TITLE is index.html's title", () => {
    expect(index.match(/<title>([^<]*)<\/title>/)[1]).toBe(DEFAULT_TITLE);
  });

  it("the shell rewrites sit before the catch-all", () => {
    const sources = vercel.rewrites.map((r) => r.source);
    const catchAll = sources.findIndex((s) => s.startsWith("/((?!"));
    for (const meta of Object.values(PAGE_META)) expect(sources.indexOf(meta.path)).toBeLessThan(catchAll);
  });

  it("a tag that stops matching fails the build instead of shipping the landing card", () => {
    expect(() => shellFor(index.replace(/<link rel="canonical"[^>]*>/, ""), PAGE_META.demo)).toThrow(/canonical/);
  });
});
