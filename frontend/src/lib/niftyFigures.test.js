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

  it("Bollinger figures match the saved results and the one-stock grid", () => {
    const B = NIFTY.bollinger;
    const boll = (u = "start_2011", c = "default") => rows(u, c).filter((x) => x.strategy === "bollinger");
    const count = (r) => ({
      beatInSample: r.filter((x) => x.beat_in_sample).length,
      aheadOutOfSample: r.filter((x) => x.ahead_out_of_sample).length,
      survives: r.filter((x) => x.survives).length,
    });
    const r = boll();
    expect(B.funnel).toEqual({ tested: r.length, ...count(r) });
    expect(B.half).toEqual(count(boll("start_2011", "half")));
    expect(B.double).toEqual(count(boll("start_2011", "double")));
    expect(B.today).toEqual({ tested: boll("today").length, ...count(boll("today")) });
    expect(B.medianInSample).toBe(fmt(median(r.map((x) => x.is_sharpe)), 2));
    expect(B.medianOutOfSample).toBe(fmt(median(r.map((x) => x.oos_sharpe)), 2));
    expect(B.positiveOutOfSample).toBe(r.filter((x) => x.oos_sharpe > 0).length);
    expect(r.filter((x) => x.ahead_out_of_sample).map((x) => x.symbol)).toEqual(["SAIL.NS"]);
    // "Failed two of the three luck checks": timing test and Deflated Sharpe.
    const sail = r.find((x) => x.symbol === "SAIL.NS");
    expect([sail.permutation_p >= 0.05, sail.deflated_sharpe <= 0.95, sail.pbo >= 0.5]).toEqual([true, true, false]);
    const picks = r.filter((x) => x.best_params.bb_window === B.commonPick.window && x.best_params.bb_std.toFixed(1) === B.commonPick.width);
    expect(picks).toHaveLength(B.commonPick.stocks);
    const tally = {};
    for (const x of r) tally[JSON.stringify(x.best_params)] = (tally[JSON.stringify(x.best_params)] || 0) + 1;
    expect(Math.max(...Object.values(tally))).toBe(B.commonPick.stocks);

    const grids = JSON.parse(readFileSync(path.resolve(__dirname, "strategyGrids.json"), "utf8"));
    expect(B.settings).toBe(grids.bollinger.grid.length);

    const g = JSON.parse(readFileSync(path.join(research, "nifty-grid.json"), "utf8"));
    const pts = g.points.filter((p) => p.strategy === "bollinger");
    const G = B.grid;
    expect(G.combinations).toBe(pts.length);
    expect(G.combinations).toBe(g.per_strategy.bollinger.combinations);
    const windows = pts.map((p) => p.params.bb_window);
    const widths = pts.map((p) => p.params.bb_std);
    expect(G.windows).toBe(`${Math.min(...windows)} to ${Math.max(...windows)}`);
    expect(G.widths).toBe(`${Math.min(...widths)} to ${Math.max(...widths)}`);
    expect(G.beatHold).toBe(pts.filter((p) => p.is_sharpe > g.bh_is_sharpe || p.oos_sharpe > g.bh_oos_sharpe).length);
    expect(G.holdInSample).toBe(g.bh_is_sharpe.toFixed(3));
    expect(G.holdOutOfSample).toBe(g.bh_oos_sharpe.toFixed(3));
    expect(g.pick.strategy).toBe("bollinger");
    expect(G.best).toEqual({
      window: g.pick.params.bb_window,
      width: g.pick.params.bb_std.toFixed(1),
      is: fmt(g.pick.is_sharpe, 3),
      oos: fmt(g.pick.oos_sharpe, 3),
      rank: g.pick.oos_rank_of_834,
      of: g.combinations,
    });
    const s = g.small_grid_same_strategy;
    expect(G.small).toEqual({
      window: s.best_params.bb_window,
      width: s.best_params.bb_std.toFixed(1),
      is: fmt(s.is_sharpe, 3),
      oos: fmt(s.oos_sharpe, 3),
    });
    expect(G.medianOutOfSample).toBe(fmt(median(pts.map((p) => p.oos_sharpe)), 2));
    expect(G.positiveOutOfSample).toBe(pts.filter((p) => p.oos_sharpe > 0).length);

    // The study's own text says the same about the pick and the grids.
    const flat = writeup.replace(/\s+/g, " ");
    expect(flat).toContain(`${B.settings} Bollinger`);
    expect(flat).toContain(`Bollinger with a ${G.best.window}-day window and bands ${G.best.width} wide, with a Sharpe of ${G.best.is}`);
    expect(flat).toContain(`it scored ${G.best.oos} and ranked ${G.best.rank}rd of ${G.best.of}`);
    expect(flat).toContain(`(window ${G.small.window}, width ${G.small.width}) with a tuning-years Sharpe of ${G.small.is}`);

    // The search description quotes the same funnel.
    const desc = PAGE_META["learn-bollinger-bands-nifty-50"].description;
    expect(desc).toContain(`${B.funnel.tested} Nifty 50 stocks`);
    expect(desc).toContain(`${B.funnel.beatInSample} beat holding on the tuning years`);
    expect(desc).toContain(`${B.funnel.aheadOutOfSample} stayed ahead`);
  });

  it("the backtesting guide's search description quotes the study's funnel", () => {
    const f = NIFTY.funnel;
    const desc = PAGE_META["learn-how-to-backtest-a-trading-strategy"].description;
    expect(desc).toContain(`${f.beatInSample} of ${f.tested} tests beat holding at first and ${f.survives} survived`);
  });

  it("every survivor row is the published study's own", () => {
    for (const s of NIFTY.survivors) {
      const line = writeup.split("\n").find((l) => l.startsWith(`| ${s.stock} | ${s.strategy === "Momentum" ? "momentum" : s.strategy} |`));
      expect(line, `${s.stock} ${s.strategy}`).toContain(`${s.oos.replace("−", "−")} (${s.hold})`);
    }
  });
});
