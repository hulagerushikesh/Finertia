import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useReducedMotion } from "motion/react";
import { CHART, AXIS, thin } from "../chartTheme";
import ChartFrame, { HatchDefs } from "./ChartFrame";
import ChartTip from "./ChartTip";

const formatDate = (d) => d?.slice(0, 7);

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <ChartTip
      label={label}
      rows={[{ label: "Drawdown", value: `${(payload[0]?.value * 100)?.toFixed(2)}%`, className: "text-loss" }]}
    />
  );
}

export default function DrawdownChart({ data }) {
  const off = useReducedMotion();
  const points = thin(data);
  const worst = Math.min(...data.map((d) => d.value));

  return (
    <ChartFrame
      title="Drawdown"
      caption="How far below its previous peak the equity sat, day by day."
      aside={
        <p className="text-2xs font-mono text-graphite">
          worst <span className="text-loss">{(worst * 100).toFixed(1)}%</span>
        </p>
      }
    >
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <HatchDefs />
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDate} {...AXIS} interval="preserveStartEnd" minTickGap={40} />
          <YAxis {...AXIS} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} width={44} />
          <Tooltip content={<Tip />} cursor={{ stroke: CHART.pencil, strokeDasharray: "2 3" }} />
          <Area
            type="monotone" dataKey="value" stroke={CHART.loss} strokeWidth={1.5} fill="url(#lossGrad)"
            isAnimationActive={!off} animationDuration={700}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
