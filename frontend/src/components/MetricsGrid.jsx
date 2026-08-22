import React from "react";
import Tooltip from "./Tooltip";

/**
 * Signs are written out rather than left to colour alone.
 *
 * Red/green is the convention in finance and worth keeping, but as the *only*
 * carrier of direction it fails for roughly one in twelve men, and it fails
 * completely in a printed or screenshotted result. A leading + or − says the
 * same thing in a way that survives both.
 *
 * The plus is only added where the sign means something, which is why `tone`
 * has to reach this far. A win rate is not "+47.64%" and a profit factor is not
 * "+1.11" — neither quantity can be negative, so a plus in front of it implies
 * a direction it does not have, which is the opposite of the clarity the sign
 * was added for.
 */
const SIGNED_TONES = new Set(["signed", "gain"]);

function fmt(value, type, tone) {
  if (value === null || value === undefined) return "—";
  const sign = SIGNED_TONES.has(tone) && value > 0 ? "+" : "";
  if (type === "pct") return `${sign}${(value * 100).toFixed(2)}%`;
  if (type === "ratio") return `${sign}${value.toFixed(2)}`;
  if (type === "int") return value.toLocaleString();
  return value.toFixed(4);
}

/**
 * Colour by what the number *means*, not by its sign.
 *
 * Sign alone is misleading here. Max drawdown and worst day are always
 * negative, so colouring them by sign painted a −42% drawdown in the same green
 * as a +68% return — the worse the drawdown, the more reassuring it looked.
 * Volatility and trade count have no good or bad direction at all, so colouring
 * them says something the number does not support.
 *
 *   signed   — up is good, down is bad (returns, risk-adjusted ratios)
 *   loss     — always a loss; never dress it up
 *   gain     — always a gain
 *   over1    — good above 1.0, bad below (profit factor)
 *   neutral  — carries no direction on its own
 */
function toneClass(tone, value) {
  if (value === null || value === undefined) return "text-text-faint";
  switch (tone) {
    case "signed":
      return value > 0 ? "text-success" : value < 0 ? "text-danger" : "text-text-muted";
    case "loss":
      return value < 0 ? "text-danger" : "text-text-muted";
    case "gain":
      return value > 0 ? "text-success" : "text-text-muted";
    case "over1":
      return value > 1 ? "text-success" : value < 1 ? "text-danger" : "text-text-muted";
    default:
      return "text-text-primary";
  }
}

/**
 * Split into the numbers that decide something and the numbers that describe
 * it. Eleven identically-sized cards gave a reader no way to tell that max
 * drawdown decides whether a strategy is holdable while best day is trivia —
 * so the grid said everything mattered equally, which is worse than saying
 * nothing.
 */
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

export default function MetricsGrid({ metrics }) {
  return (
    <div className="flex flex-col gap-3">
      {/* The four numbers a decision actually rests on. */}
      {/* Four-up only from xl. The dashboard puts a 21rem sidebar beside this
          column, so at lg these cards were ~150px wide and every label but
          "Sharpe" truncated — "TOTAL RE…", "MAX DRAW…". Measured: the labels
          need up to 179px including the tooltip. */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {HEADLINE.map(({ key, label, type, tone, tip }) => (
          <div
            key={key}
            className="panel p-4 sm:p-5 flex flex-col gap-2 relative overflow-visible"
          >
            <div className="flex items-start gap-1.5 min-w-0">
              {/* Wraps rather than truncates. A clipped label loses the word
                  that distinguishes it; a second line costs 16px. */}
              <span className="eyebrow">{label}</span>
              <Tooltip label={tip} align="start" />
            </div>
            <span
              className={`text-2xl sm:text-display-sm font-mono font-medium leading-none tracking-tight ${toneClass(
                tone,
                metrics[key],
              )}`}
            >
              {fmt(metrics[key], type, tone)}
            </span>
          </div>
        ))}
      </div>

      {/* Everything else, at the weight it deserves. */}
      {/* Was one row of seven. Seven cells need ~1477px and this column is
          ~650px on a 1024 screen, so the labels overran their cells and
          collided with the next one — CSS grid items default to
          min-width:auto and refuse to shrink, so `truncate` never fired.
          Now it wraps to as many rows as it needs.

          Borders live on the cells rather than in the gaps, which is what
          makes wrapping safe: a row with an empty trailing slot draws no
          stray hairline, because there is no cell there to draw one. The
          negative margins push the outer edges under the panel's own border,
          and overflow-hidden clips them at the rounded corners. */}
      <div className="panel overflow-hidden">
        {/* One column below sm: there the cell puts label and value on the same
            row, so a second column left "ANN. VOLATILITY" 60px of the 122 it
            needs. Full width gives the label the room and costs nothing —
            seven short rows are no taller than four cramped ones. */}
        <div className="grid sm:grid-cols-3 lg:grid-cols-4 -mr-px -mb-px">
        {SECONDARY.map(({ key, label, type, tone, tip }) => (
          <div
            key={key}
            className="min-w-0 border-r border-b border-border px-4 py-3 flex items-center justify-between gap-2 sm:flex-col sm:items-start sm:gap-1.5"
          >
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="eyebrow truncate">{label}</span>
              <Tooltip label={tip} align="start" />
            </div>
            <span
              className={`text-sm font-mono font-medium ${toneClass(tone, metrics[key])}`}
            >
              {fmt(metrics[key], type, tone)}
            </span>
          </div>
        ))}
        </div>
      </div>
    </div>
  );
}
