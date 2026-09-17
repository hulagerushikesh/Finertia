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
import { CHART, AXIS, thin } from "../chartTheme";
import ChartFrame from "./ChartFrame";
import ChartTip from "./ChartTip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

// Four distinct marks rather than shades of one — the whole point of the
// chart is telling the lines apart, and the run cap is four for the same
// reason. Ink first, then pencil, then the two semantic hues.
const COLORS = [CHART.strategy, CHART.pencil, CHART.gain, CHART.warn];

const label = (s) =>
  `${s.ticker} · ${STRATEGIES.find((x) => x.id === s.strategy)?.label || s.strategy}`;

const pct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)}%`;

function Tip({ active, payload, label: date, series }) {
  if (!active || !payload?.length) return null;
  return (
    <ChartTip
      label={date}
      rows={payload.map((p) => {
        const s = series.find((x) => x.runId === p.dataKey);
        return { label: s ? label(s) : p.dataKey, value: p.value?.toFixed(4) };
      })}
    />
  );
}

export default function ComparisonPanel({ data }) {
  const { series, chart, overlapping_days: overlap } = data;

  // Same thinning rule as the single-run chart: recharts slows noticeably past a
  // few hundred points and the shape does not change.
  const thinned = thin(chart);

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
        <Alert className="border-l-2 border-l-warn">
          <AlertDescription className="text-xs text-graphite">
            These runs cover periods that never overlap, so the lines share an axis but not a
            moment in time. Their end values are not comparable.
          </AlertDescription>
        </Alert>
      )}

      <ChartFrame
        title={`Equity curves — ${series.length} runs`}
        aside={
          <span className="text-2xs font-mono text-graphite">
            {overlap} overlapping day{overlap === 1 ? "" : "s"}
          </span>
        }
      >
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={thinned} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={CHART.grid} vertical={false} />
            <XAxis dataKey="date" tickFormatter={(d) => d?.slice(0, 7)} {...AXIS} interval="preserveStartEnd" minTickGap={40} />
            <YAxis {...AXIS} axisLine={false} tickFormatter={(v) => v.toFixed(2)} width={44} />
            <Tooltip content={<Tip series={series} />} cursor={{ stroke: CHART.pencil, strokeDasharray: "2 3" }} />
            <Legend iconType="plainline" wrapperStyle={{ fontSize: 11, fontFamily: CHART.mono, color: CHART.axisText }} />
            {series.map((s, i) => (
              <Line
                key={s.runId}
                type="monotone"
                dataKey={s.runId}
                name={label(s)}
                stroke={COLORS[i % COLORS.length]}
                strokeDasharray={i === 0 ? undefined : i === 1 ? "6 3" : i === 2 ? "2 3" : "8 3 2 3"}
                dot={false}
                strokeWidth={i === 0 ? 2 : 1.6}
                // A run with no bar on a date is absent from that row rather
                // than zero; connecting across keeps the line continuous.
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

      <section className="sheet overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-5">Run</TableHead>
                <TableHead>Period</TableHead>
                <TableHead className="text-right">Total return</TableHead>
                <TableHead className="text-right">Sharpe</TableHead>
                <TableHead className="text-right pr-5">Max DD</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {series.map((s, i) => (
                <TableRow key={s.runId} className="font-mono text-xs">
                  <TableCell className="pl-5">
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-0.5 shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-foreground">{label(s)}</span>
                    </span>
                  </TableCell>
                  <TableCell className="text-graphite whitespace-nowrap">{s.start} → {s.end}</TableCell>
                  <TableCell className={cn("text-right", s.metrics?.total_return === best.total_return ? "text-gain font-medium pencil-mark" : "text-foreground")}>
                    {pct(s.metrics?.total_return)}
                  </TableCell>
                  <TableCell className={cn("text-right", s.metrics?.sharpe_ratio === best.sharpe_ratio ? "text-gain font-medium pencil-mark" : "text-foreground")}>
                    {s.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}
                  </TableCell>
                  <TableCell className={cn("text-right pr-5", s.metrics?.max_drawdown === best.max_drawdown ? "text-gain font-medium pencil-mark" : "text-loss")}>
                    {pct(s.metrics?.max_drawdown)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-faint px-5 py-3 border-t border-border leading-relaxed">
          The pencil-marked value is the best in each column. Comparing runs on different tickers
          or periods compares two different markets as much as two strategies — the fair test holds
          everything but one variable fixed.
        </p>
      </section>
    </div>
  );
}
