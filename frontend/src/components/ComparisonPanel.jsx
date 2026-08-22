import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { STRATEGIES } from "./ConfigPanel";
import { CHART } from "../chartTheme";

// Four distinct hues rather than shades of one — the whole point of the chart is
// telling the lines apart, and the run cap is four for the same reason.
const COLORS = [CHART.strategy, CHART.success, CHART.warning, CHART.info];

const label = (s) =>
  `${s.ticker} · ${STRATEGIES.find((x) => x.id === s.strategy)?.label || s.strategy}`;

const pct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)}%`;

function CustomTooltip({ active, payload, label: date, series }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-raised border border-border-strong shadow-pop rounded-lg px-3 py-2 text-xs font-mono">
      <p className="text-text-muted mb-1">{date}</p>
      {payload.map((p) => {
        const s = series.find((x) => x.runId === p.dataKey);
        return (
          <p key={p.dataKey} style={{ color: p.color }}>
            {s ? label(s) : p.dataKey}: {p.value?.toFixed(4)}
          </p>
        );
      })}
    </div>
  );
}

export default function ComparisonPanel({ data }) {
  const { series, chart, overlapping_days: overlap } = data;

  // Same thinning rule as the single-run chart: recharts slows noticeably past a
  // few hundred points and the shape does not change.
  const step = Math.max(1, Math.floor(chart.length / 300));
  const thinned = chart.filter((_, i) => i % step === 0);

  // Best value per metric, so the winner can be marked. Drawdown is negative,
  // so "best" there is the largest (closest to zero) rather than the smallest.
  const best = {
    total_return: Math.max(...series.map((s) => s.metrics?.total_return ?? -Infinity)),
    sharpe_ratio: Math.max(...series.map((s) => s.metrics?.sharpe_ratio ?? -Infinity)),
    max_drawdown: Math.max(...series.map((s) => s.metrics?.max_drawdown ?? -Infinity)),
  };

  return (
    <div className="flex flex-col gap-5">
      {overlap === 0 && (
        <div className="bg-warning/10 border border-warning/30 text-warning text-xs rounded-xl px-4 py-3">
          These runs cover periods that never overlap, so the lines share an axis
          but not a moment in time. Their end values are not comparable.
        </div>
      )}

      <div className="panel p-5">
        <div className="flex items-baseline justify-between mb-4 gap-3 flex-wrap">
          <h2 className="text-sm font-semibold text-text-primary">
            Equity Curves — {series.length} runs
          </h2>
          <span className="text-xs text-text-muted font-mono">
            {overlap} overlapping day{overlap === 1 ? "" : "s"}
          </span>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={thinned} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
            <XAxis
              dataKey="date"
              tickFormatter={(d) => d?.slice(0, 7)}
              tick={{ fill: CHART.axisText, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: CHART.grid }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: CHART.axisText, fontSize: 11, fontFamily: CHART.mono }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => v.toFixed(2)}
              width={48}
            />
            <Tooltip content={<CustomTooltip series={series} />} />
            <Legend wrapperStyle={{ fontSize: 12, color: CHART.axisText }} />
            {series.map((s, i) => (
              <Line
                key={s.runId}
                type="monotone"
                dataKey={s.runId}
                name={label(s)}
                stroke={COLORS[i % COLORS.length]}
                dot={false}
                strokeWidth={2}
                // A run with no bar on a date is absent from that row rather
                // than zero; connecting across keeps the line continuous.
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-muted text-xs uppercase tracking-wider">
                <th className="text-left px-5 py-3">Run</th>
                <th className="text-left px-5 py-3">Period</th>
                <th className="text-right px-5 py-3">Total Return</th>
                <th className="text-right px-5 py-3">Sharpe</th>
                <th className="text-right px-5 py-3">Max DD</th>
              </tr>
            </thead>
            <tbody>
              {series.map((s, i) => (
                <tr key={s.runId} className="border-b border-border/50 last:border-0">
                  <td className="px-5 py-3">
                    <span className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ background: COLORS[i % COLORS.length] }}
                      />
                      <span className="font-mono text-text-primary">{label(s)}</span>
                    </span>
                  </td>
                  <td className="px-5 py-3 text-text-muted text-xs font-mono whitespace-nowrap">
                    {s.start} → {s.end}
                  </td>
                  <td
                    className={`px-5 py-3 text-right font-mono text-xs ${
                      s.metrics?.total_return === best.total_return
                        ? "text-success font-bold"
                        : "text-text-primary"
                    }`}
                  >
                    {pct(s.metrics?.total_return)}
                  </td>
                  <td
                    className={`px-5 py-3 text-right font-mono text-xs ${
                      s.metrics?.sharpe_ratio === best.sharpe_ratio
                        ? "text-success font-bold"
                        : "text-text-primary"
                    }`}
                  >
                    {s.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}
                  </td>
                  <td
                    className={`px-5 py-3 text-right font-mono text-xs ${
                      s.metrics?.max_drawdown === best.max_drawdown
                        ? "text-success font-bold"
                        : "text-danger"
                    }`}
                  >
                    {pct(s.metrics?.max_drawdown)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-text-faint px-5 py-3 border-t border-border">
          Bold marks the best value in each column. Comparing runs on different
          tickers or periods compares two different markets as much as two
          strategies — the fair test holds everything but one variable fixed.
        </p>
      </div>
    </div>
  );
}
