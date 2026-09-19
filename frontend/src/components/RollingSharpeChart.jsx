import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from "recharts";
import { useReducedMotion } from "motion/react";
import { CHART, AXIS, thin } from "../chartTheme";
import ChartFrame from "./ChartFrame";
import ChartTip from "./ChartTip";

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <ChartTip label={label} rows={[{ label: "Sharpe", value: v.toFixed(2), className: v >= 0 ? "text-gain" : "text-loss" }]} />
  );
}

export default function RollingSharpeChart({ data, window = 60 }) {
  const off = useReducedMotion();
  if (!data || data.length === 0) {
    return (
      <section className="sheet px-5 py-4">
        <h2 className="font-display text-lg font-semibold text-foreground">Rolling Sharpe</h2>
        <p className="text-xs text-graphite mt-1">
          Needs at least {window} trading days. Try a longer date range.
        </p>
      </section>
    );
  }

  const points = thin(data);
  const values = data.map((d) => d.value);
  const latest = values[values.length - 1];
  const best = Math.max(...values);
  const worst = Math.min(...values);
  const timeAbove = values.filter((v) => v > 0).length / values.length;

  return (
    <ChartFrame
      title="Rolling Sharpe"
      caption={`Trailing ${window}-day risk-adjusted return. Steady above zero beats one lucky spike.`}
      aside={
        <div className="flex gap-4 text-2xs font-mono text-graphite">
          <span>latest <span className={latest >= 0 ? "text-gain" : "text-loss"}>{latest.toFixed(2)}</span></span>
          <span>range <span className="text-foreground">{worst.toFixed(2)} → {best.toFixed(2)}</span></span>
          <span>above 0 <span className="text-foreground">{(timeAbove * 100).toFixed(0)}%</span></span>
        </div>
      }
    >
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={points} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="date" {...AXIS} minTickGap={40} tickFormatter={(d) => d?.slice(0, 7)} />
          <YAxis {...AXIS} axisLine={false} width={36} />
          <Tooltip content={<Tip />} cursor={{ stroke: CHART.pencil, strokeDasharray: "2 3" }} />
          {/* Zero, in pencil: the line the reading is checked against. */}
          <ReferenceLine y={0} stroke={CHART.pencil} strokeDasharray="3 3" />
          <Line
            type="monotone" dataKey="value" stroke={CHART.strategy} strokeWidth={1.6} dot={false}
            isAnimationActive={!off} animationDuration={800}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
