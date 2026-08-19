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
import { CHART } from "../chartTheme";

function formatDate(dateStr) {
  return dateStr?.slice(0, 7);
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-raised border border-border-strong shadow-pop rounded-lg px-3 py-2 text-xs font-mono">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value?.toFixed(4)}
        </p>
      ))}
    </div>
  );
}

export default function EquityCurveChart({ data }) {
  const thinned = data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 300)) === 0);

  return (
    <div className="panel p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">Equity Curve</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={thinned} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
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
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 12, color: CHART.axisText }}
          />
          <Line
            type="monotone"
            dataKey="strategy"
            name="Strategy"
            stroke={CHART.strategy}
            dot={false}
            strokeWidth={2}
          />
          {/* Mint, matching every other place a reference series appears in
              this app. The dash is kept so the two lines stay separable in
              greyscale and for a reader who cannot split violet from teal. */}
          <Line
            type="monotone"
            dataKey="benchmark"
            name="Buy &amp; hold"
            stroke={CHART.benchmark}
            dot={false}
            strokeWidth={1.5}
            strokeDasharray="5 3"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
