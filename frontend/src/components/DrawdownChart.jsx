import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
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
      <p className="text-danger">{(payload[0]?.value * 100)?.toFixed(2)}%</p>
    </div>
  );
}

export default function DrawdownChart({ data }) {
  const thinned = data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 300)) === 0);

  return (
    <div className="panel p-5">
      <h2 className="text-sm font-semibold text-text-primary mb-4">Drawdown</h2>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={thinned} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART.danger} stopOpacity={0.4} />
              <stop offset="95%" stopColor={CHART.danger} stopOpacity={0} />
            </linearGradient>
          </defs>
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
            tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
            width={52}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART.danger}
            strokeWidth={1.5}
            fill="url(#ddGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
