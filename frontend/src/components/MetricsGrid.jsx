import React from "react";
import Tooltip from "./Tooltip";
import { Stagger, StaggerItem } from "./motion";
import { cn } from "@/lib/utils";

/**
 * Signs are written out rather than left to colour alone.
 *
 * Red/green is the convention in finance and worth keeping, but as the *only*
 * carrier of direction it fails for roughly one in twelve men, and it fails
 * completely in a printed result. A leading + or − says the same thing in a
 * way that survives both. The plus is only added where the sign means
 * something: a win rate is not "+47.64%".
 */
const SIGNED_TONES = new Set(["signed", "gain"]);

export function fmt(value, type, tone) {
  if (value === null || value === undefined) return "—";
  const sign = SIGNED_TONES.has(tone) && value > 0 ? "+" : "";
  if (type === "pct") return `${sign}${(value * 100).toFixed(2)}%`;
  if (type === "ratio") return `${sign}${value.toFixed(2)}`;
  if (type === "int") return value.toLocaleString();
  return value.toFixed(4);
}

/**
 * Colour by what the number *means*, not by its sign. Max drawdown is always
 * negative, so colouring it by sign painted a −42% drawdown in the same green
 * as a +68% return.
 *
 *   signed — up is good, down is bad · loss — always a loss · gain — always a
 *   gain · over1 — good above 1.0 · neutral — carries no direction
 */
export function toneClass(tone, value) {
  if (value === null || value === undefined) return "text-faint";
  switch (tone) {
    case "signed":
      return value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-graphite";
    case "loss":
      return value < 0 ? "text-loss" : "text-graphite";
    case "gain":
      return value > 0 ? "text-gain" : "text-graphite";
    case "over1":
      return value > 1 ? "text-gain" : value < 1 ? "text-loss" : "text-graphite";
    default:
      return "text-foreground";
  }
}

/**
 * A metric printed on its own reads as a property of the strategy, the way a
 * ruler reports 30cm. It is not — it is one draw from one sample path. The
 * band is the part that says so.
 *
 * The one signal worth interrupting for is an interval that still contains
 * the null: a Sharpe whose interval spans zero is not weak evidence of an
 * edge, it is no evidence. That case is the only one coloured.
 */
function fmtBound(value, type, tone) {
  // Coarser than the point estimate on purpose: printing a bound as
  // "+404.95%" claims a precision the interval is in the middle of denying.
  const sign = SIGNED_TONES.has(tone) && value > 0 ? "+" : "";
  if (type === "pct") return `${sign}${Math.round(value * 100)}%`;
  if (type === "ratio") return `${sign}${value.toFixed(2)}`;
  return fmt(value, type, tone);
}

function Band({ band, type, tone }) {
  if (!band) return null;
  const spansNull = band.null_value !== null && band.excludes_null === false;
  const range = `${fmtBound(band.low, type, tone)} to ${fmtBound(band.high, type, tone)}`;

  return (
    <span className={cn("text-2xs font-mono leading-tight block", spansNull ? "text-warn" : "text-faint")}>
      <span className="block">{range}</span>
      {spansNull && <span className="block font-sans">spans {band.null_value === 1 ? "1" : "0"}</span>}
      {band.reliability === "understates" && (
        <span className="block font-sans text-faint">interval understated</span>
      )}
    </span>
  );
}

/** The interval belongs to the number, so its caveats belong in the same note. */
function tipWith(tip, band, ci, type, tone) {
  if (!band) return tip;
  const parts = [tip];
  parts.push(
    `${Math.round(ci.confidence * 100)}% interval from a block bootstrap: ` +
      `${fmt(band.low, type, tone)} to ${fmt(band.high, type, tone)}.`,
  );
  if (band.null_value !== null && band.excludes_null === false) {
    parts.push(
      `It still contains ${fmt(band.null_value, type, "neutral")}, so this backtest is not evidence that the true value is anything else.`,
    );
  }
  if (band.reliability_note) parts.push(band.reliability_note);
  return parts.join(" ");
}

const HEADLINE = [
  { key: "total_return", label: "Total return", type: "pct", tone: "signed", tip: "Cumulative return over the entire backtest period." },
  { key: "annualized_return", label: "Annualised", type: "pct", tone: "signed", tip: "Total return scaled to an annual rate (CAGR). The fair way to compare periods of different lengths." },
  { key: "sharpe_ratio", label: "Sharpe", type: "ratio", tone: "signed", tip: "Annualised return divided by annualised volatility. Useful for comparing two strategies on the same data; close to meaningless in isolation." },
  { key: "max_drawdown", label: "Max drawdown", type: "pct", tone: "loss", tip: "Largest peak-to-trough decline in the equity curve. Usually the number that decides whether a strategy is actually holdable." },
];

const SECONDARY = [
  { key: "annualized_volatility", label: "Ann. volatility", type: "pct", tone: "neutral", tip: "Annualised standard deviation of daily returns. Neither good nor bad on its own — it is the denominator of the Sharpe ratio." },
  { key: "calmar_ratio", label: "Calmar", type: "ratio", tone: "signed", tip: "Annualised return divided by absolute max drawdown — return per unit of pain." },
  { key: "win_rate", label: "Win rate", type: "pct", tone: "neutral", tip: "Share of active days that were positive. Deliberately not a headline number: a strategy can win most days and still lose money." },
  { key: "profit_factor", label: "Profit factor", type: "ratio", tone: "over1", tip: "Gross gains divided by gross losses. Above 1 means the winners outweigh the losers." },
  { key: "num_trades", label: "Trades", type: "int", tone: "neutral", tip: "Number of position changes. More trades means more cost, not more skill." },
  { key: "best_day", label: "Best day", type: "pct", tone: "gain", tip: "Single best daily return in the backtest." },
  { key: "worst_day", label: "Worst day", type: "pct", tone: "loss", tip: "Single worst daily return in the backtest." },
];

/** The four numbers a decision actually rests on. */
export function HeadlineMetrics({ metrics, confidenceIntervals }) {
  const ci = confidenceIntervals?.available ? confidenceIntervals : null;
  const bands = ci?.metrics ?? {};
  return (
    // Four-up only from xl: beside a 21rem sidebar these are ~150px wide at lg.
    <Stagger className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {HEADLINE.map(({ key, label, type, tone, tip }) => (
        <StaggerItem key={key} className="sheet p-4 sm:p-5 flex flex-col gap-2 min-h-[6.5rem]">
          <div className="flex items-start gap-1.5 min-w-0">
            <span className="eyebrow">{label}</span>
            <Tooltip label={ci ? tipWith(tip, bands[key], ci, type, tone) : tip} align="start" />
          </div>
          <span
            className={cn(
              "font-display text-3xl sm:text-display-sm font-semibold leading-none tracking-tight",
              toneClass(tone, metrics[key]),
            )}
          >
            {fmt(metrics[key], type, tone)}
          </span>
          <span className="mt-auto">
            <Band band={bands[key]} type={type} tone={tone} />
          </span>
        </StaggerItem>
      ))}
    </Stagger>
  );
}

/** Everything else, at the weight it deserves, plus the note on the intervals. */
export function MoreMetrics({ metrics, confidenceIntervals }) {
  const ci = confidenceIntervals?.available ? confidenceIntervals : null;
  const bands = ci?.metrics ?? {};
  return (
    <div className="flex flex-col gap-3">
      {/* Borders live on the cells rather than in the gaps so wrapping is safe. */}
      <div className="sheet overflow-hidden">
        <div className="grid sm:grid-cols-3 lg:grid-cols-4 -mr-px -mb-px">
          {SECONDARY.map(({ key, label, type, tone, tip }) => (
            <div
              key={key}
              className="min-w-0 border-r border-b border-border px-4 py-3 flex items-center justify-between gap-2 sm:flex-col sm:items-start sm:gap-1.5"
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="eyebrow truncate">{label}</span>
                <Tooltip label={ci ? tipWith(tip, bands[key], ci, type, tone) : tip} align="start" />
              </div>
              <span className={cn("text-sm font-mono font-medium", toneClass(tone, metrics[key]))}>
                {fmt(metrics[key], type, tone)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {ci && (
        <p className="text-2xs text-faint leading-relaxed max-w-prose">
          Ranges are {Math.round(ci.confidence * 100)}% confidence intervals from{" "}
          {ci.n_resamples.toLocaleString()} block-bootstrap resamples
          {ci.block?.block_length > 1
            ? ` (blocks averaging ${ci.block.block_length} bars, chosen from this series' own autocorrelation)`
            : " (the series showed no serial dependence, so blocks are single days)"}
          . They measure how much of this result came from the order the returns arrived in — not
          whether the strategy works on data it has never seen.{" "}
          <span className="text-warn">Amber</span> marks an interval that still contains the value
          meaning "no effect". Intervals marked understated are known to be too narrow: measured
          coverage for volatility was 74% against a nominal 95%. Max drawdown used to carry the
          same mark and no longer does — its interval was not too narrow, it was mis-centred by a
          bias correction that does not apply to a path-dependent statistic. Suppressing that
          correction took its coverage from 79% to 95%.
        </p>
      )}

      {confidenceIntervals && !confidenceIntervals.available && (
        <p className="text-2xs text-faint leading-relaxed">
          No confidence intervals for this run — {confidenceIntervals.reason}
        </p>
      )}
    </div>
  );
}

/** Both halves together — the demo page and anything that wants the full sheet. */
export default function MetricsGrid(props) {
  return (
    <div className="flex flex-col gap-3">
      <HeadlineMetrics {...props} />
      <MoreMetrics {...props} />
    </div>
  );
}
