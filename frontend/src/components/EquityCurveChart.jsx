import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { useReducedMotion } from "motion/react";
import { CHART, AXIS, thin } from "../chartTheme";
import ChartFrame from "./ChartFrame";
import ChartTip from "./ChartTip";

const formatDate = (d) => d?.slice(0, 7);

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <ChartTip
      label={label}
      rows={payload.map((p) => ({
        label: p.name,
        value: p.value?.toFixed(4),
        className: p.dataKey === "strategy" ? "text-foreground" : "text-graphite",
      }))}
    />
  );
}

export default function EquityCurveChart({ data }) {
  const off = useReducedMotion();
  const points = thin(data);
  const last = data[data.length - 1];

  return (
    <ChartFrame
      title="Equity curve"
      caption="Growth of $1. Ink is the strategy; the dashed line is holding the stock."
      aside={
        last && (
          <p className="text-2xs font-mono text-graphite text-right">
            ends <span className="text-foreground">{last.strategy?.toFixed(2)}</span> vs{" "}
            <span className="text-foreground">{last.benchmark?.toFixed(2)}</span>
          </p>
        )
      }
    >
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="0" vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDate} {...AXIS} interval="preserveStartEnd" minTickGap={40} />
          <YAxis {...AXIS} axisLine={false} tickFormatter={(v) => v.toFixed(2)} width={44} />
          <Tooltip content={<Tip />} cursor={{ stroke: CHART.pencil, strokeDasharray: "2 3" }} />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 11, fontFamily: CHART.mono, color: CHART.axisText }} />
          {/* The line draws on when a run lands — the tape unrolling. */}
          <Line
            type="monotone" dataKey="strategy" name="Strategy"
            stroke={CHART.strategy} strokeWidth={2} dot={false}
            isAnimationActive={!off} animationDuration={900} animationEasing="ease-out"
          />
          <Line
            type="monotone" dataKey="benchmark" name="Buy & hold"
            stroke={CHART.benchmark} strokeWidth={1.5} strokeDasharray="4 4" dot={false}
            isAnimationActive={!off} animationDuration={900} animationEasing="ease-out"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
