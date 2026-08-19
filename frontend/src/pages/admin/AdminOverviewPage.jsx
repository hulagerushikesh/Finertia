import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { getAdminStats } from "../../api";
import { CHART } from "../../chartTheme";

function KpiCard({ label, value, sub }) {
  return (
    <div className="panel p-5">
      <p className="text-xs text-text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className="text-3xl font-bold font-mono text-text-primary">{value}</p>
      {sub && <p className="text-xs text-text-muted mt-1">{sub}</p>}
    </div>
  );
}

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

export default function AdminOverviewPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAdminStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" /></div>;
  if (error) return <div className="text-danger bg-danger/10 border border-danger/20 rounded-xl px-5 py-4">{error}</div>;

  return (
    <div className="flex flex-col gap-6">
      {/* KPI row 1 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Total Users" value={stats.total_users.toLocaleString()} />
        <KpiCard label="Total Runs" value={stats.total_runs.toLocaleString()} />
        <KpiCard label="Runs Today" value={stats.runs_today.toLocaleString()} />
        <KpiCard label="Runs This Week" value={stats.runs_this_week.toLocaleString()} />
      </div>

      {/* KPI row 2 */}
      <div className="grid grid-cols-2 gap-4">
        <KpiCard label="Avg Sharpe Ratio" value={stats.avg_sharpe?.toFixed(2) ?? "—"} />
        <KpiCard label="Avg Total Return" value={fmtPct(stats.avg_total_return)} />
      </div>

      {/* Top tickers bar chart */}
      {stats.top_tickers?.length > 0 && (
        <div className="panel p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4">Top 5 Tickers</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={stats.top_tickers}
              layout="vertical"
              margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
            >
              <XAxis type="number" tick={{ fill: CHART.axisText, fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="ticker"
                width={52}
                tick={{ fill: CHART.textPrimary, fontSize: 12, fontFamily: CHART.mono }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{ background: CHART.surface, border: "1px solid #33405C", borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: "rgba(99,102,241,0.1)" }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {stats.top_tickers.map((_, i) => (
                  <Cell key={i} fill={CHART.strategy} fillOpacity={1 - i * 0.12} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
