import React from "react";

function fmt(value, type) {
  if (value === null || value === undefined) return "—";
  if (type === "pct") return `${(value * 100).toFixed(2)}%`;
  if (type === "ratio") return value.toFixed(2);
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
  if (value === null || value === undefined) return "text-text-muted";
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

const CARDS = [
  { key: "total_return", label: "Total Return", type: "pct", tone: "signed", tooltip: "Cumulative return over the entire backtest period." },
  { key: "annualized_return", label: "Ann. Return", type: "pct", tone: "signed", tooltip: "Total return scaled to an annual rate (CAGR)." },
  { key: "annualized_volatility", label: "Ann. Volatility", type: "pct", tone: "neutral", tooltip: "Annualised standard deviation of daily returns. Neither good nor bad on its own — it is the denominator of the Sharpe ratio." },
  { key: "sharpe_ratio", label: "Sharpe Ratio", type: "ratio", tone: "signed", tooltip: "Annualised return divided by annualised volatility. Useful for comparing two strategies on the same data; close to meaningless in isolation." },
  { key: "max_drawdown", label: "Max Drawdown", type: "pct", tone: "loss", tooltip: "Largest peak-to-trough decline in the equity curve. Usually the number that decides whether a strategy is actually holdable." },
  { key: "calmar_ratio", label: "Calmar Ratio", type: "ratio", tone: "signed", tooltip: "Annualised return divided by absolute max drawdown — return per unit of pain." },
  { key: "win_rate", label: "Win Rate", type: "pct", tone: "neutral", tooltip: "Share of active days that were positive. Deliberately not a headline number: a strategy can win most days and still lose money." },
  { key: "profit_factor", label: "Profit Factor", type: "ratio", tone: "over1", tooltip: "Gross gains divided by gross losses. Above 1 means the winners outweigh the losers." },
  { key: "num_trades", label: "# Trades", type: "int", tone: "neutral", tooltip: "Number of position changes. More trades means more cost, not more skill." },
  { key: "best_day", label: "Best Day", type: "pct", tone: "gain", tooltip: "Single best daily return in the backtest." },
  { key: "worst_day", label: "Worst Day", type: "pct", tone: "loss", tooltip: "Single worst daily return in the backtest." },
];

export default function MetricsGrid({ metrics }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
      {CARDS.map(({ key, label, type, tone, tooltip }) => (
        <div
          key={key}
          title={tooltip}
          className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-1 cursor-help"
        >
          <span className="text-xs text-text-muted font-medium uppercase tracking-wider truncate">
            {label}
          </span>
          <span
            className={`text-lg font-mono font-semibold ${toneClass(tone, metrics[key])}`}
          >
            {fmt(metrics[key], type)}
          </span>
        </div>
      ))}
    </div>
  );
}
