import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { PAGE_META } from "./pageMeta";
import { STRATEGY_PAGES } from "./strategyPages";
import grids from "./strategyGrids.json";

const writeup = readFileSync(path.resolve(__dirname, "../../../planning/write-up.md"), "utf8");

/** The write-up's table row for a strategy, from the first table that has one after `heading`. */
function row(heading, label) {
  const after = writeup.slice(writeup.indexOf(heading));
  const line = after.split("\n").find((l) => l.startsWith(`| ${label} |`));
  return line.replace(/\*\*/g, "");
}

describe("strategy pages", () => {
  it("cover every strategy the backend registers, each with a page", () => {
    expect(STRATEGY_PAGES.map((s) => s.id).sort()).toEqual(Object.keys(grids).sort());
    for (const s of STRATEGY_PAGES) expect(PAGE_META[`strategy-${s.id}`].path).toBe(s.path);
  });

  it("name one parameter per key the strategy takes", () => {
    for (const s of STRATEGY_PAGES) {
      const swept = new Set(s.grid.flatMap(Object.keys));
      for (const k of swept) expect(s.params.map(([key]) => key)).toContain(k);
    }
  });

  // The pages quote the write-up; reproduce_writeup.py re-runs the write-up.
  // A re-run that changes a figure fails here until the page says the same.
  for (const s of STRATEGY_PAGES) {
    it(`${s.id}: the AAPL figures are the write-up's`, () => {
      const { best, first, moved } = s.writeup;
      expect(row("## What the first window said", s.label)).toBe(
        `| ${s.label} | ${best} | ${first.is} | ${first.oos} | ${first.verdict} |`
      );
      expect(row("## Then the window moved", s.label)).toMatch(
        new RegExp(`^\\| ${s.label} \\| ${moved.is} \\| ${moved.oos} \\| ${moved.verdict} \\|`)
      );
    });
  }
});
