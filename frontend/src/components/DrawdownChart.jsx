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

function formatDate(dateStr) {
  return dateStr?.slice(0, 7);
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs font-mono">
      <p className="text-text-muted mb-1">{label}</p>
      <p className="text-danger">{(payload[0]?.value * 100)?.toFixed(2)}%</p>
    </div>
  );
}

export default function DrawdownChart({ data }) {
  const thinned = data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 300)) === 0);

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">Drawdown</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={thinned} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#2a2d3a" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
            width={52}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#ef4444"
            strokeWidth={1.5}
            fill="url(#ddGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
