import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { CHART } from "../chartTheme";

const MAX_POINTS = 300;

function thin(data) {
  if (data.length <= MAX_POINTS) return data;
  const step = Math.ceil(data.length / MAX_POINTS);
  const kept = data.filter((_, i) => i % step === 0);
  // Always keep the final point so the line ends where the data does.
  if (kept[kept.length - 1] !== data[data.length - 1]) kept.push(data[data.length - 1]);
  return kept;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <div className="bg-bg border border-border rounded-lg px-3 py-2 shadow-lg">
      <p className="text-[10px] font-mono text-text-muted mb-0.5">{label}</p>
      <p className={`text-xs font-mono ${v >= 0 ? "text-success" : "text-danger"}`}>
        Sharpe {v.toFixed(2)}
      </p>
    </div>
  );
}

export default function RollingSharpeChart({ data, window = 60 }) {
  if (!data || data.length === 0) {
    return (
      <div className="panel rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-1">Rolling Sharpe</h3>
        <p className="text-xs text-text-muted">
          Needs at least {window} trading days. Try a longer date range.
        </p>
      </div>
    );
  }

  const points = thin(data);
  const values = data.map((d) => d.value);
  const latest = values[values.length - 1];
  const best = Math.max(...values);
  const worst = Math.min(...values);
  const timeAbove = values.filter((v) => v > 0).length / values.length;

  return (
    <div className="panel rounded-2xl p-5">
      <div className="flex items-start justify-between mb-1 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Rolling Sharpe</h3>
          <p className="text-[11px] text-text-muted mt-0.5">
            Trailing {window}-day risk-adjusted return. Steady above zero beats one lucky spike.
          </p>
        </div>
        <div className="flex gap-4 text-[10px] font-mono text-text-muted">
          <span>
            latest <span className={latest >= 0 ? "text-success" : "text-danger"}>{latest.toFixed(2)}</span>
          </span>
          <span>
            range <span className="text-text-primary">{worst.toFixed(2)} → {best.toFixed(2)}</span>
          </span>
          <span>
            above 0 <span className="text-text-primary">{(timeAbove * 100).toFixed(0)}%</span>
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={points} margin={{ top: 12, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: CHART.axisText, fontSize: 10 }}
            stroke={CHART.grid}
            minTickGap={40}
          />
          <YAxis tick={{ fill: CHART.axisText, fontSize: 10 }} stroke={CHART.grid} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke={CHART.axisText} strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="value"
            stroke={CHART.strategy}
            strokeWidth={1.6}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
