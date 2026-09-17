import React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

const REGIME = {
  low: { label: "Calm", sub: "lowest third of days by market volatility" },
  mid: { label: "Middling", sub: "middle third" },
  high: { label: "Turbulent", sub: "highest third" },
};

const pct = (v, dp = 0) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(dp)}%`);
const num = (v) => (v === null || v === undefined ? "—" : v.toFixed(2));
const sharpeTone = (v) => (v === null || v === undefined ? "text-graphite" : v >= 0 ? "text-gain" : "text-loss");

/**
 * The same return, broken down by how volatile the *market* was on each day.
 *
 * Every bar is labelled calm / middling / turbulent by the trailing 21-day
 * realised volatility of the market, split into thirds for this period. A
 * strategy that earned its whole return in one third is reported as exactly
 * that. Used on the backtest itself and on the stitched out-of-sample record
 * from the rolling walk-forward, so both take the same shape.
 *
 *   title    — the section heading; omit for an embedded, heading-less table
 *   compact  — fewer columns, for use inside another section
 */
export default function RegimeTable({ regimes, title = "By market regime", compact = false }) {
  if (!regimes) return null;

  if (!regimes.computable) {
    return (
      <section className={cn(!compact && "sheet p-6")}>
        {title && <h2 className="font-display text-xl font-medium text-foreground">{title}</h2>}
        <p className="text-xs text-graphite mt-2 leading-relaxed">{regimes.reason}</p>
      </section>
    );
  }

  const t = regimes.thresholds;
  const rows = ["low", "mid", "high"].map((k) => ({ key: k, ...REGIME[k], ...regimes.regimes[k] }));
  const best = regimes.best_regime;
  const worst = regimes.worst_regime;

  return (
    <section className={cn(!compact && "sheet overflow-hidden")}>
      {title && (
        <div className={cn("flex items-start justify-between gap-4 flex-wrap", compact ? "mb-3" : "px-6 pt-6 pb-4")}>
          <div className="max-w-lg">
            <h2 className={cn("font-display font-medium text-foreground", compact ? "text-sm" : "text-xl")}>{title}</h2>
            <p className="text-xs text-graphite mt-1 leading-relaxed">
              Each day is labelled by how volatile the market was over the previous {regimes.window} days,
              split into thirds for this period: calm below {pct(t.low_max)} annualised, turbulent above{" "}
              {pct(t.high_min)}. The same money, sorted by the weather it was made in.
            </p>
          </div>
          {best && worst && best !== worst && (
            <p className="text-2xs font-mono text-graphite shrink-0">
              best <span className="text-gain">{REGIME[best].label.toLowerCase()}</span> · worst{" "}
              <span className="text-loss">{REGIME[worst].label.toLowerCase()}</span> · spread{" "}
              <span className="text-foreground">{num(regimes.sharpe_spread)}</span>
            </p>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        <Table className="text-xs font-mono">
          <TableHeader>
            <TableRow>
              <TableHead className={cn(!compact && "pl-6")}>Regime</TableHead>
              <TableHead className="text-right">Days</TableHead>
              <TableHead className="text-right">Sharpe</TableHead>
              <TableHead className="text-right">Market Sharpe</TableHead>
              <TableHead className="text-right">Contribution</TableHead>
              {!compact && <TableHead className="text-right">Hit rate</TableHead>}
              {!compact && <TableHead className="text-right pr-6">In market</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => {
              const empty = !r.bars;
              return (
                <TableRow key={r.key} className={cn(r.key === best && "bg-pencil/5")}>
                  <TableCell className={cn("font-sans", !compact && "pl-6")}>
                    <span className="text-foreground font-medium">{r.label}</span>
                    {!compact && <span className="block text-2xs text-faint">{r.sub}</span>}
                  </TableCell>
                  <TableCell className="text-right text-graphite">
                    {r.bars} <span className="text-faint">({pct(r.share_of_bars)})</span>
                  </TableCell>
                  <TableCell className={cn("text-right", sharpeTone(r.sharpe_ratio), r.key === best && "pencil-mark")}>
                    {empty ? "—" : num(r.sharpe_ratio)}
                  </TableCell>
                  <TableCell className={cn("text-right", sharpeTone(r.market_sharpe_ratio))}>
                    {empty ? "—" : num(r.market_sharpe_ratio)}
                  </TableCell>
                  <TableCell className={cn("text-right", sharpeTone(r.contribution))}>
                    {empty ? "—" : pct(r.contribution, 1)}
                    {!compact && r.share_of_return !== null && r.share_of_return !== undefined && (
                      <span className="text-faint"> · {pct(r.share_of_return)} of total</span>
                    )}
                  </TableCell>
                  {!compact && <TableCell className="text-right text-graphite">{empty ? "—" : pct(r.hit_rate)}</TableCell>}
                  {!compact && (
                    <TableCell className="text-right text-graphite pr-6">{empty ? "—" : pct(r.time_in_market)}</TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {!compact && (
        <p className="text-2xs text-faint leading-relaxed px-6 pt-3 pb-5">
          Sharpe per regime is computed over the days in that regime, which are not consecutive.
          Contributions are arithmetic and sum to the arithmetic total. The first{" "}
          {regimes.unlabelled_bars} days have no label — the window has not filled yet.
        </p>
      )}
    </section>
  );
}
