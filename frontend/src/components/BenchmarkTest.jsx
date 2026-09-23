import React from "react";
import { Badge } from "@/components/ui/badge";
import Tooltip from "./Tooltip";
import { cn } from "@/lib/utils";

const num = (v) => (v === null || v === undefined ? "—" : v.toFixed(2));

/** A p-value is not a percentage and should never be rounded to one. */
function fmtP(p) {
  if (p === null || p === undefined) return "—";
  if (p < 0.001) return "< 0.001";
  return p.toFixed(3);
}

/**
 * The gap between the strategy's Sharpe and buy-and-hold's, with the only
 * thing that makes the comparison legible: how wide it would have to be.
 *
 * The results card prints one Sharpe and the equity chart draws the
 * benchmark's curve beside it. The comparison is irresistible and, as
 * printed, unmakeable — the two series share most of their bars, and nothing
 * says how far apart they would have to be before the difference meant
 * anything. `sharpe_test.py` (Ledoit-Wolf 2008) answers that; this strip is
 * where the answer goes.
 *
 * Three things it is careful about:
 *
 *   - The Sharpe pair here is the *arithmetic* one (mean / standard
 *     deviation), not the geometric figure on the headline card. They differ
 *     by up to 0.2 on real runs, so the strip shows its own pair rather than
 *     borrowing the card's and quietly testing something else. The tooltip
 *     says so in words.
 *   - The standard error is given equal billing with the gap. It is the
 *     number that turns "0.39 behind" into "0.39 behind, ±0.51" — which is
 *     the whole finding.
 *   - Not significant is written out, never left to the absence of colour.
 *     Colour only ever marks a difference the test actually called.
 */
export default function BenchmarkTest({ test, benchmarkLabel = "holding it" }) {
  if (!test) return null;

  if (!test.computable) {
    return (
      <p className="text-2xs text-faint leading-relaxed">
        No comparison with {benchmarkLabel} on this run — {test.reason}.
      </p>
    );
  }

  const { difference, significant, p_value: p } = test;
  const behind = difference < 0;
  // `faint` would be the obvious pill for "no call", but its muted-on-muted
  // pair measures 4.39:1 in light mode, and this is the most common case on
  // the page. `outline` puts the figure on the sheet's own ground instead.
  const tone = significant ? (behind ? "loss" : "gain") : "outline";

  const tip =
    `Ledoit-Wolf (2008) test of the difference between two Sharpe ratios. The two series are ` +
    `paired — the strategy trades the benchmark's own asset — and the standard error is HAC, so ` +
    `autocorrelation and volatility clustering are not assumed away. The p-value comes from ` +
    `${test.resamples.toLocaleString()} studentised bootstrap resamples (blocks averaging ` +
    `${test.block_length} ${test.block_length === 1 ? "bar" : "bars"}) rather than a normal ` +
    `approximation; the normal one is ${fmtP(test.p_value_normal)}. Two-sided, so a strategy ` +
    `significantly worse than the benchmark is flagged too. Sharpe here is mean over standard ` +
    `deviation annualised, which is why it can differ from the headline card's figure — that one ` +
    `is annualised return over annualised volatility, and compounding costs it about half a ` +
    `variance.`;

  return (
    <div className="sheet px-4 py-3 sm:px-5 flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        <span className="eyebrow">Against {benchmarkLabel}</span>
        <Tooltip label={tip} align="start" />
      </div>

      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 font-mono text-sm">
        <span className="text-foreground">
          strategy <span className="font-medium">{num(test.strategy_sharpe)}</span>
        </span>
        <span className="text-graphite">
          {benchmarkLabel} <span className="font-medium">{num(test.benchmark_sharpe)}</span>
        </span>
        {/* The sign is written out; the colour is reserved for a gap the test
            actually called. A red −0.39 that the p-value goes on to call
            noise would be the page contradicting itself. */}
        <span className={cn("font-medium", significant ? (behind ? "text-loss" : "text-gain") : "text-graphite")}>
          {difference > 0 ? "+" : ""}
          {num(difference)}
          <span className="text-faint font-normal"> ± {num(test.standard_error)}</span>
        </span>
        <Badge variant={tone} size="sm" className="font-mono">
          p {fmtP(p)}
        </Badge>
        {/* graphite, not faint: at 2xs the faint token measures 4.39:1 on the
            dark sheet, and this is a finding rather than a footnote. */}
        {!significant && <span className="text-2xs text-graphite font-sans">not significant</span>}
      </div>

      <p className="text-2xs text-graphite leading-relaxed max-w-prose">{test.verdict}</p>
    </div>
  );
}
