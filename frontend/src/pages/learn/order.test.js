import { describe, expect, it } from "vitest";
import { ARTICLES } from "./articles";
import { NEWEST_FIRST, published } from "./order";

describe("/learn list order", () => {
  it("is newest first, and the last article added is at the top", () => {
    expect(NEWEST_FIRST).toHaveLength(ARTICLES.length);
    for (let k = 1; k < NEWEST_FIRST.length; k++) {
      const [prev, cur] = [NEWEST_FIRST[k - 1], NEWEST_FIRST[k]];
      expect(published(prev) >= published(cur), `${prev.id} before ${cur.id}`).toBe(true);
      if (published(prev) === published(cur)) {
        expect(ARTICLES.indexOf(prev)).toBeGreaterThan(ARTICLES.indexOf(cur));
      }
    }
    const newest = [...ARTICLES].reverse().reduce((best, a) => (published(a) > published(best) ? a : best));
    expect(NEWEST_FIRST[0]).toBe(newest);
  });
});
