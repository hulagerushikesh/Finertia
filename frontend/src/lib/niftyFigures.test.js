import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { NIFTY } from "./niftyFigures";
import { PAGE_META } from "./pageMeta";

const research = path.resolve(__dirname, "../../../planning/research");
const funnelData = JSON.parse(readFileSync(path.join(research, "nifty-funnel.json"), "utf8"));
const writeup = readFileSync(path.join(research, "nifty-write-up.md"), "utf8");

const rows = (universe = "start_2011", cost = "default") => funnelData.universes[universe][cost].rows;
const funnel = (universe = "start_2011", cost = "default") => funnelData.universes[universe][cost].funnel;
const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
// The study prints a minus sign, not a hyphen, and two decimals for medians.
const fmt = (x, digits) => x.toFixed(digits).replace("-", "−");
const LABEL = { momentum: "Momentum", macd: "MACD", bollinger: "Bollinger" };

describe("Nifty study figures quoted on /learn", () => {
  it("funnel, costs and the comparison list match the saved results", () => {
    const f = funnel();
    expect(NIFTY.funnel).toEqual({
      tested: f.tested,
      beatInSample: f.beat_in_sample,
      aheadOutOfSample: f.ahead_out_of_sample,
      survives: f.survives,
    });
    expect(NIFTY.survivesHalfCost).toBe(funnel("start_2011", "half").survives);
    expect(NIFTY.survivesDoubleCost).toBe(funnel("start_2011", "double").survives);
    expect(NIFTY.today).toEqual({ tested: funnel("today").tested, survives: funnel("today").survives });
    expect(NIFTY.stocks).toBe(f.tested / 3);
    expect(NIFTY.missing).toBe(funnelData.missing_from_yahoo.length);
  });

  it("medians match the saved results", () => {
    const r = rows();
    expect(NIFTY.medianInSample).toBe(fmt(median(r.map((x) => x.is_sharpe)), 2));
    expect(NIFTY.medianOutOfSample).toBe(fmt(median(r.map((x) => x.oos_sharpe)), 2));
    // One buy-and-hold figure per stock: every third row.
    expect(NIFTY.medianHoldOutOfSample).toBe(fmt(median(r.filter((_, i) => i % 3 === 0).map((x) => x.bh_oos_sharpe)), 2));
  });

  it("pairs beating holding on the unseen years, per strategy", () => {
    const r = rows();
    const beat = (s) => r.filter((x) => x.strategy === s && x.oos_sharpe > x.bh_oos_sharpe).length;
    expect(NIFTY.beatHoldUnseen).toEqual({
      momentum: beat("momentum"),
      macd: beat("macd"),
      bollinger: beat("bollinger"),
      total: r.filter((x) => x.oos_sharpe > x.bh_oos_sharpe).length,
    });
  });

  it("the four survivors are the saved ones, with their unseen-years figures", () => {
    const saved = rows().filter((x) => x.survives);
    expect(saved).toHaveLength(NIFTY.survivors.length);
    for (const s of NIFTY.survivors) {
      const hit = saved.find((x) => LABEL[x.strategy] === s.strategy && fmt(x.oos_sharpe, 3) === s.oos);
      expect(hit, `${s.stock} ${s.strategy}`).toBeTruthy();
      expect(fmt(hit.bh_oos_sharpe, 3)).toBe(s.hold);
    }
  });

  it("survivorship figures: 2011 list against today's list", () => {
    const S = NIFTY.survivorship;
    const t = funnel("today");
    expect(S.todayFunnel).toEqual({
      tested: t.tested,
      beatInSample: t.beat_in_sample,
      aheadOutOfSample: t.ahead_out_of_sample,
      survives: t.survives,
    });
    expect(S.todaySurvivesDoubleCost).toBe(funnel("today", "double").survives);
    const todaySurvivors = rows("today").filter((x) => x.survives);
    expect(todaySurvivors.map((x) => [x.symbol, LABEL[x.strategy]])).toEqual([["ADANIENT.NS", S.todaySurvivor.strategy]]);

    const perStock = (u) => rows(u).filter((_, i) => i % 3 === 0);
    expect(S.holdTuning2011).toBe(fmt(median(perStock("start_2011").map((x) => x.bh_is_sharpe)), 2));
    expect(S.holdTuningToday).toBe(fmt(median(perStock("today").map((x) => x.bh_is_sharpe)), 2));
    expect(S.holdNegative2011).toBe(perStock("start_2011").filter((x) => x.bh_is_sharpe < 0).length);
    expect(S.stocksToday).toBe(perStock("today").length);
    expect(S.holdNegativeToday).toBe(perStock("today").filter((x) => x.bh_is_sharpe < 0).length);

    const todaySymbols = new Set(rows("today").map((x) => x.symbol));
    expect(S.stillInIndex).toBe(perStock("start_2011").filter((x) => todaySymbols.has(x.symbol)).length);
    const survivorSymbols = new Set(rows().filter((x) => x.survives).map((x) => x.symbol));
    expect(S.survivorStocksStillIn).toBe([...survivorSymbols].filter((s) => todaySymbols.has(s)).length);
    expect(S.missingNames).toEqual(funnelData.missing_from_yahoo.map((m) => m.name));

    // The search description quotes the same two medians.
    const desc = PAGE_META["learn-survivorship-bias-nifty-50"].description;
    expect(desc).toContain(`median Sharpe of ${S.holdTuningToday}`);
    expect(desc).toContain(`2011 list, ${S.holdTuning2011}`);

    // The study's own sentence quotes the same medians and today's survivor.
    expect(writeup).toContain(`gave a Sharpe of ${S.holdTuningToday} over the tuning years`);
    expect(writeup).toContain(`against ${S.holdTuning2011} on the 2011 list`);
    expect(writeup).toContain(`(${S.todaySurvivor.stock}, momentum)`);
  });

  it("every survivor row is the published study's own", () => {
    for (const s of NIFTY.survivors) {
      const line = writeup.split("\n").find((l) => l.startsWith(`| ${s.stock} | ${s.strategy === "Momentum" ? "momentum" : s.strategy} |`));
      expect(line, `${s.stock} ${s.strategy}`).toContain(`${s.oos.replace("−", "−")} (${s.hold})`);
    }
  });
});
