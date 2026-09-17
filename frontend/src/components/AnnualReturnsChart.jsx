import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from "recharts";
import { useReducedMotion } from "motion/react";
import { CHART, AXIS } from "../chartTheme";
import ChartFrame, { HatchDefs } from "./ChartFrame";
import ChartTip from "./ChartTip";

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const strat = payload.find((p) => p.dataKey === "strategy")?.value ?? 0;
  const bench = payload.find((p) => p.dataKey === "benchmark")?.value ?? 0;
  const diff = strat - bench;
  return (
    <ChartTip
      label={label}
      rows={[
        { label: "Strategy", value: `${(strat * 100).toFixed(2)}%`, className: "text-foreground" },
        { label: "Buy & hold", value: `${(bench * 100).toFixed(2)}%`, className: "text-graphite" },
        {
          label: diff >= 0 ? "beat by" : "behind by",
          value: `${Math.abs(diff * 100).toFixed(2)}%`,
          className: diff >= 0 ? "text-gain" : "text-loss",
        },
      ]}
    />
  );
}

export default function AnnualReturnsChart({ data }) {
  const off = useReducedMotion();
  if (!data || data.length === 0) return null;
  const wins = data.filter((d) => d.strategy > d.benchmark).length;

  return (
    <ChartFrame
      title="Annual returns"
      caption="Strategy against buy-and-hold, year by year."
      aside={
        <span className="text-2xs font-mono text-graphite">
          beat buy &amp; hold in{" "}
          <span className={wins > data.length / 2 ? "text-gain" : "text-loss"}>
            {wins} / {data.length}
          </span>{" "}
          years
        </span>
      }
    >
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barGap={2}>
          <HatchDefs />
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="year" {...AXIS} />
          <YAxis {...AXIS} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} width={40} />
          <Tooltip content={<Tip />} cursor={{ fill: CHART.cursor }} />
          <Legend
            iconType="square"
            wrapperStyle={{ fontSize: 11, fontFamily: CHART.mono, color: CHART.axisText }}
            formatter={(value) => (value === "strategy" ? "Strategy" : "Buy & hold")}
          />
          <ReferenceLine y={0} stroke={CHART.borderStrong} />
          <Bar dataKey="strategy" fill={CHART.strategy} isAnimationActive={!off} animationDuration={600} />
          <Bar dataKey="benchmark" fill="url(#hatch)" stroke={CHART.benchmark} strokeWidth={0.5} isAnimationActive={!off} animationDuration={600} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
