import React from "react";
import { Badge } from "@/components/ui/badge";
import RegimeTable from "./RegimeTable";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

const VERDICT = {
  consistent: {
    label: "Consistent",
    tone: "gain",
    blurb: "Every fold earned out-of-sample and so did the stitched record. The edge did not depend on which year the split fell in.",
  },
  regime_dependent: {
    label: "Regime-dependent",
    tone: "warn",
    blurb: "Some folds earned and some lost. The single split above is one draw from this distribution — its verdict depends on where the line fell.",
  },
  failed: {
    label: "Failed",
    tone: "loss",
    blurb: "No fold earned out-of-sample. Re-optimising each year did not help; there was nothing to find.",
  },
};

const FOLD_VERDICT = {
  held_up: ["held up", "text-gain"],
  weakened: ["weakened", "text-warn"],
  overfit: ["overfit", "text-loss"],
  failed: ["failed", "text-loss"],
  inconclusive: ["inconclusive", "text-graphite"],
};

const PARAM_LABELS = {
  momentum_lookback: "lookback",
  ma_window: "MA",
  momentum_threshold: "threshold",
  macd_fast: "fast",
  macd_slow: "slow",
  macd_signal: "signal",
  bb_window: "window",
  bb_std: "std",
};

const ORDER = Object.keys(PARAM_LABELS);
/** Same key order on every row, whatever order the backend sent. */
const params = (p) =>
  p
    ? Object.entries(p)
        .sort(([a], [b]) => ORDER.indexOf(a) - ORDER.indexOf(b))
        .map(([k, v]) => `${PARAM_LABELS[k] || k} ${v}`)
        .join(" · ")
    : "—";
const pct = (v, dp = 1) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(dp)}%`);
const num = (v) => (v === null || v === undefined ? "—" : v.toFixed(2));
const tone = (v) => (v === null || v === undefined ? "text-graphite" : v >= 0 ? "text-gain" : "text-loss");

/**
 * The walk-forward split, walked forward.
 *
 * The section above picks one date and reports what happened either side of
 * it. This one anchors the in-sample start, moves the split through the
 * later part of the period in equal steps, re-optimises the grid at each
 * step, and scores each winner only on the stretch that follows — with the
 * market's own return and volatility beside it, so a fold that lost in a
 * year the market lost reads differently from one that lost in a rally.
 */
export default function RollingWalkForward({ rolling }) {
  if (!rolling) return null;

  if (!rolling.computable && rolling.computable !== undefined) {
    return (
      <section className="sheet p-6">
        <h2 className="font-display text-xl font-semibold text-foreground">Walking the split forward</h2>
        <p className="text-xs text-graphite mt-2 leading-relaxed">{rolling.reason}</p>
      </section>
    );
  }

  const v = VERDICT[rolling.verdict] || VERDICT.regime_dependent;
  const stitched = rolling.out_of_sample_stitched;
  const ci = stitched?.sharpe_interval;
  const stability = rolling.parameter_stability;
  const [lo, hi] = rolling.out_of_sample_sharpe_range || [];

  return (
    <section className="sheet p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="max-w-lg">
          <h2 className="font-display text-xl font-semibold text-foreground">Walking the split forward</h2>
          <p className="text-xs text-graphite mt-1 leading-relaxed">
            The split above is one date. Here it starts at{" "}
            <span className="font-mono text-foreground">{rolling.first_split_date}</span> and moves forward
            in {rolling.n_folds} equal steps. At each step the grid is re-optimised on everything before
            the line and the winner is scored only on the stretch after it, with the market's own return
            beside it. Only the green column is evidence.
          </p>
        </div>
        <Badge variant={v.tone} className="shrink-0">{v.label}</Badge>
      </div>

      <p className="margin-note mt-4 mb-5">{v.blurb}</p>

      <div className="flex flex-wrap gap-x-6 gap-y-2 text-2xs font-mono text-graphite mb-4">
        <span>
          <span className="text-foreground">{rolling.folds_positive}</span> of {rolling.n_folds} folds earned
        </span>
        <span>
          fold Sharpe from <span className={tone(lo)}>{num(lo)}</span> to <span className={tone(hi)}>{num(hi)}</span>
        </span>
        {stability && (
          <span>
            {stability.distinct_parameter_sets === 1
              ? "same parameters every fold"
              : `${stability.distinct_parameter_sets} different parameter sets across ${rolling.n_folds} folds`}
          </span>
        )}
      </div>

      <div className="overflow-x-auto -mx-6">
        <Table className="text-xs font-mono">
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6">Fold</TableHead>
              <TableHead>Scored on</TableHead>
              <TableHead>Chosen parameters</TableHead>
              <TableHead className="text-right">Tuned Sharpe</TableHead>
              <TableHead className="text-right text-pencil">Unseen Sharpe</TableHead>
              <TableHead className="text-right">Return</TableHead>
              <TableHead className="text-right">Market</TableHead>
              <TableHead className="text-right">Vol</TableHead>
              <TableHead className="pr-6">Verdict</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rolling.folds.map((f) => {
              const [label, cls] = FOLD_VERDICT[f.verdict] || FOLD_VERDICT.inconclusive;
              return (
                <TableRow key={f.fold}>
                  <TableCell className="pl-6 text-graphite">{f.fold + 1}</TableCell>
                  <TableCell className="whitespace-nowrap text-foreground">
                    {f.out_of_sample_start_date} <span className="text-faint">→</span> {f.out_of_sample_end_date}
                    <span className="block text-2xs text-faint">{f.out_of_sample_bars} bars · {f.gap_bars}-bar gap</span>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-graphite">{params(f.best_params)}</TableCell>
                  <TableCell className="text-right text-graphite">{num(f.in_sample_sharpe)}</TableCell>
                  <TableCell className={cn("text-right pencil-mark", tone(f.out_of_sample_sharpe))}>
                    {num(f.out_of_sample_sharpe)}
                  </TableCell>
                  <TableCell className={cn("text-right", tone(f.out_of_sample_return))}>{pct(f.out_of_sample_return)}</TableCell>
                  <TableCell className={cn("text-right", tone(f.benchmark_return))}>{pct(f.benchmark_return)}</TableCell>
                  <TableCell className="text-right text-graphite">{pct(f.realised_volatility, 0)}</TableCell>
                  <TableCell className={cn("pr-6 font-sans", cls)}>{label}</TableCell>
                </TableRow>
              );
            })}
            {stitched && (
              <TableRow className="bg-muted/40">
                <TableCell className="pl-6 font-sans text-foreground font-medium" colSpan={3}>
                  Stitched out-of-sample record
                  <span className="block text-2xs font-mono font-normal text-faint">
                    {stitched.start_date} → {stitched.end_date} · {stitched.bars} bars
                  </span>
                </TableCell>
                <TableCell />
                <TableCell className={cn("text-right whitespace-nowrap pencil-mark", tone(stitched.sharpe_ratio))}>
                  {num(stitched.sharpe_ratio)}
                  {ci && ci.low !== undefined && (
                    <span className="block text-2xs text-faint font-normal">
                      [{num(ci.low)}, {num(ci.high)}]
                    </span>
                  )}
                </TableCell>
                <TableCell className={cn("text-right", tone(stitched.total_return))}>{pct(stitched.total_return)}</TableCell>
                <TableCell colSpan={2} />
                <TableCell className="pr-6 whitespace-nowrap font-sans text-2xs text-graphite">
                  max drawdown <span className="font-mono text-loss">{pct(stitched.max_drawdown)}</span>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {stability && stability.distinct_parameter_sets > 1 && (
        <p className="text-xs text-graphite mt-4 leading-relaxed">
          {stability.distinct_parameter_sets === rolling.n_folds
            ? `A different parameter set won every one of the ${rolling.n_folds} folds.`
            : `The winning parameters changed across the ${rolling.n_folds} folds; the most common choice (${params(stability.modal_params)}) won ${Math.round(stability.modal_share * rolling.n_folds)} of them.`}{" "}
          A strategy whose best settings move every year is being re-fitted to each year, not tuned once.
        </p>
      )}

      {ci && ci.low !== undefined && ci.low < 0 && ci.high > 0 && (
        <p className="text-xs text-warn mt-3 leading-relaxed">
          The interval on the stitched Sharpe straddles zero: on this much unseen data the record cannot
          be told apart from no edge at all.
        </p>
      )}

      {stitched?.regimes && (
        <div className="mt-6 pt-5 border-t border-border">
          <RegimeTable regimes={stitched.regimes} title="The unseen record, by market regime" compact />
        </div>
      )}
    </section>
  );
}
