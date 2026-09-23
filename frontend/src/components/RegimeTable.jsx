import React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

const REGIME = {
  low: { label: "Calm", sub: "lowest third of days by market volatility" },
  mid: { label: "Middling", sub: "middle third" },
  high: { label: "Turbulent", sub: "highest third" },
};
const TREND = {
  down: { label: "Falling", sub: "market down more than one standard deviation over the window" },
  flat: { label: "Flat", sub: "move inside one standard deviation of its own noise" },
  up: { label: "Rising", sub: "market up more than one standard deviation" },
};
const VOL_KEYS = ["low", "mid", "high"];
const TREND_KEYS = ["down", "flat", "up"];

const pct = (v, dp = 0) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(dp)}%`);
const num = (v) => (v === null || v === undefined ? "—" : v.toFixed(2));
const sharpeTone = (v) => (v === null || v === undefined ? "text-graphite" : v >= 0 ? "text-gain" : "text-loss");

/**
 * The same return, broken down by how volatile the *market* was on each day.
 *
 * Every bar is labelled calm / middling / turbulent by the trailing 21-day
 * realised volatility of the market, split into thirds for this period. A
 * strategy that earned its whole return in one third is reported as exactly
 * that. Since the trend label landed the same bars are also labelled falling
 * / flat / rising by the market's 60-day direction, and the two labels are
 * crossed into a 3 x 3 grid — so "earns in turbulence" can be read as "earns
 * when turbulence had a direction" when that is what the numbers say. Used on
 * the backtest itself and on the stitched out-of-sample record from the
 * rolling walk-forward, so both take the same shape.
 *
 *   title    — the section heading; omit for an embedded, heading-less table
 *   compact  — fewer columns, for use inside another section
 */
export default function RegimeTable({ regimes, title = "By market regime", compact = false }) {
  if (!regimes) return null;

  if (!regimes.computable) {
    return (
      <section className={cn(!compact && "sheet p-6")}>
        {title && <h2 className="font-display text-xl font-semibold text-foreground">{title}</h2>}
        <p className="text-xs text-graphite mt-2 leading-relaxed">{regimes.reason}</p>
      </section>
    );
  }

  const t = regimes.thresholds;
  const rows = ["low", "mid", "high"].map((k) => ({ key: k, ...REGIME[k], ...regimes.regimes[k] }));
  const best = regimes.best_regime;
  const worst = regimes.worst_regime;
  const trend = regimes.trend;
  const joint = regimes.joint;

  return (
    <section className={cn(!compact && "sheet overflow-hidden")}>
      {title && (
        <div className={cn("flex items-start justify-between gap-4 flex-wrap", compact ? "mb-3" : "px-6 pt-6 pb-4")}>
          <div className="max-w-lg">
            <h2 className={cn("font-display font-semibold text-foreground", compact ? "text-sm" : "text-xl")}>{title}</h2>
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

      <BreakdownTable rows={rows} best={best} firstHead="Regime" compact={compact} />

      {trend && !trend.computable && (
        <p className={cn("text-2xs text-faint leading-relaxed", compact ? "pt-3" : "px-6 pt-3")}>
          No direction label: {trend.reason}
        </p>
      )}

      {trend?.computable && (
        <div className={cn(compact ? "mt-5" : "px-6 pt-6")}>
          <div className="flex items-start justify-between gap-4 flex-wrap mb-3">
            <div className="max-w-lg">
              <h3 className={cn("font-display font-semibold text-foreground", compact ? "text-sm" : "text-base")}>
                Which way the market was going
              </h3>
              <p className="text-xs text-graphite mt-1 leading-relaxed">
                The same days, labelled by the market's move over the previous {trend.window} days: rising or
                falling when that move is more than {trend.threshold_sigma} standard deviation of its own noise,
                flat otherwise. A fixed cut, not a third — so flat means flat.
              </p>
            </div>
            {trend.best_regime !== trend.worst_regime && (
              <p className="text-2xs font-mono text-graphite shrink-0">
                best <span className="text-gain">{TREND[trend.best_regime].label.toLowerCase()}</span> · worst{" "}
                <span className="text-loss">{TREND[trend.worst_regime].label.toLowerCase()}</span> · spread{" "}
                <span className="text-foreground">{num(trend.sharpe_spread)}</span>
              </p>
            )}
          </div>
          <BreakdownTable
            rows={TREND_KEYS.map((k) => ({ key: k, ...TREND[k], ...trend.regimes[k] }))}
            best={trend.best_regime}
            firstHead="Direction"
            compact={compact}
            flush
          />
        </div>
      )}

      {joint?.computable && <JointGrid joint={joint} compact={compact} />}

      {!compact && (
        <p className="text-2xs text-faint leading-relaxed px-6 pt-3 pb-5">
          Sharpe per regime is computed over the days in that regime, which are not consecutive.
          Contributions are arithmetic and sum to the arithmetic total. The first{" "}
          {regimes.unlabelled_bars} days have no volatility label
          {trend?.computable ? ` and the first ${trend.unlabelled_bars} no direction label` : ""} — the window has
          not filled yet.
        </p>
      )}
    </section>
  );
}

/** One breakdown table — the volatility rows or the direction rows. */
function BreakdownTable({ rows, best, firstHead, compact, flush = false }) {
  const pad = !compact && !flush;
  return (
    <div className="overflow-x-auto">
      <Table className="text-xs font-mono">
        <TableHeader>
          <TableRow>
            <TableHead className={cn(pad && "pl-6")}>{firstHead}</TableHead>
            <TableHead className="text-right">Days</TableHead>
            <TableHead className="text-right">Sharpe</TableHead>
            <TableHead className="text-right">Market Sharpe</TableHead>
            <TableHead className="text-right">Contribution</TableHead>
            {!compact && <TableHead className="text-right">Hit rate</TableHead>}
            {!compact && <TableHead className={cn("text-right", pad && "pr-6")}>In market</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => {
            const empty = !r.bars;
            return (
              <TableRow key={r.key} className={cn(r.key === best && "bg-pencil/5")}>
                <TableCell className={cn("font-sans", pad && "pl-6")}>
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
                  <TableCell className={cn("text-right text-graphite", pad && "pr-6")}>
                    {empty ? "—" : pct(r.time_in_market)}
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * Volatility x direction, Sharpe per cell. A cell with fewer days than one
 * volatility window shows its count and no number — a Sharpe off a handful
 * of days would be noise about the sample.
 */
function JointGrid({ joint, compact }) {
  const isCell = (c, v, t) => c && c.vol === v && c.trend === t;
  return (
    <div className={cn(compact ? "mt-5" : "px-6 pt-6")}>
      <div className="max-w-lg mb-3">
        <h3 className={cn("font-display font-semibold text-foreground", compact ? "text-sm" : "text-base")}>
          Volatility × direction
        </h3>
        <p className="text-xs text-graphite mt-1 leading-relaxed">
          The two labels crossed. Best cell{" "}
          <span className="text-gain">
            {REGIME[joint.best_cell.vol].label.toLowerCase()} &amp; {TREND[joint.best_cell.trend].label.toLowerCase()}
          </span>{" "}
          ({num(joint.best_cell.sharpe_ratio)}), worst{" "}
          <span className="text-loss">
            {REGIME[joint.worst_cell.vol].label.toLowerCase()} &amp; {TREND[joint.worst_cell.trend].label.toLowerCase()}
          </span>{" "}
          ({num(joint.worst_cell.sharpe_ratio)}). Cells under {joint.min_cell_bars} days show the count only.
        </p>
      </div>
      <div className="overflow-x-auto">
        <Table className="text-xs font-mono">
          <TableHeader>
            <TableRow>
              <TableHead>Sharpe</TableHead>
              {TREND_KEYS.map((t) => (
                <TableHead key={t} className="text-right">
                  {TREND[t].label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {VOL_KEYS.map((v) => (
              <TableRow key={v}>
                <TableCell className="font-sans text-foreground font-medium">{REGIME[v].label}</TableCell>
                {TREND_KEYS.map((t) => {
                  const c = joint.cells[v][t];
                  const scored = c.sharpe_ratio !== null && c.sharpe_ratio !== undefined;
                  return (
                    <TableCell
                      key={t}
                      className={cn(
                        "text-right",
                        scored ? sharpeTone(c.sharpe_ratio) : "text-faint",
                        isCell(joint.best_cell, v, t) && "bg-pencil/5 pencil-mark",
                        isCell(joint.worst_cell, v, t) && "bg-loss/5",
                      )}
                    >
                      {scored ? num(c.sharpe_ratio) : "—"}
                      <span className="block text-2xs text-faint">{c.bars} d</span>
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
