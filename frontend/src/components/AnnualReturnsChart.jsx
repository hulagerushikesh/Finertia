import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { CHART } from "../chartTheme";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const strat = payload.find((p) => p.dataKey === "strategy")?.value ?? 0;
  const bench = payload.find((p) => p.dataKey === "benchmark")?.value ?? 0;
  const diff = strat - bench;
  return (
    <div className="bg-bg border border-border rounded-lg px-3 py-2 shadow-lg">
      <p className="text-tick font-mono text-text-muted mb-1">{label}</p>
      <p className="text-xs font-mono text-accent">Strategy {(strat * 100).toFixed(2)}%</p>
      <p className="text-xs font-mono text-text-muted">Buy &amp; hold {(bench * 100).toFixed(2)}%</p>
      <p className={`text-tick font-mono mt-1 ${diff >= 0 ? "text-success" : "text-danger"}`}>
        {diff >= 0 ? "beat by " : "behind by "}
        {Math.abs(diff * 100).toFixed(2)}%
      </p>
    </div>
  );
}

export default function AnnualReturnsChart({ data }) {
  if (!data || data.length === 0) return null;

  const wins = data.filter((d) => d.strategy > d.benchmark).length;

  return (
    <div className="panel rounded-2xl p-5">
      <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">Annual returns</h2>
          <p className="text-2xs text-text-muted mt-0.5">
            Strategy against buy-and-hold, year by year.
          </p>
        </div>
        <span className="text-2xs font-mono text-text-muted">
          beat benchmark in{" "}
          <span className={wins > data.length / 2 ? "text-success" : "text-danger"}>
            {wins} / {data.length}
          </span>{" "}
          years
        </span>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="year" tick={{ fill: CHART.axisText, fontSize: 10 }} stroke={CHART.grid} />
          <YAxis
            tick={{ fill: CHART.axisText, fontSize: 10 }}
            stroke={CHART.grid}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Legend
            wrapperStyle={{ fontSize: 11, color: CHART.axisText }}
            formatter={(value) => (value === "strategy" ? "Strategy" : "Buy & hold")}
          />
          <ReferenceLine y={0} stroke={CHART.axisText} />
          <Bar dataKey="strategy" fill={CHART.strategy} radius={[2, 2, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="benchmark" fill={CHART.benchmark} radius={[2, 2, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
