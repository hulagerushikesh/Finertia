import React, { useState, useEffect, useCallback } from "react";
import { getAdminRuns } from "../../api";

const PAGE_SIZE = 50;

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

function fmtDate(ts) {
  if (!ts) return "—";
  const d = ts._seconds ? new Date(ts._seconds * 1000) : new Date(ts);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export default function AdminRunsPage() {
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [tickerFilter, setTickerFilter] = useState("");
  const [uidFilter, setUidFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    getAdminRuns(PAGE_SIZE, page * PAGE_SIZE, { ticker: tickerFilter, uid: uidFilter })
      .then((d) => { setRuns(d.runs); setTotal(d.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [page, tickerFilter, uidFilter]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-3 mb-5 flex-wrap">
        <input
          className="field-input px-4 py-2 w-36"
          placeholder="Ticker filter…"
          value={tickerFilter}
          onChange={(e) => { setTickerFilter(e.target.value.toUpperCase()); setPage(0); }}
        />
        <input
          className="field-input px-4 py-2 w-72"
          placeholder="User UID filter…"
          value={uidFilter}
          onChange={(e) => { setUidFilter(e.target.value); setPage(0); }}
        />
        {(tickerFilter || uidFilter) && (
          <button
            onClick={() => { setTickerFilter(""); setUidFilter(""); setPage(0); }}
            className="text-sm text-text-muted hover:text-text-primary"
          >
            Clear filters
          </button>
        )}
      </div>

      {error && <div className="text-danger bg-danger/10 border border-danger/20 rounded-xl px-5 py-4 mb-4 text-sm">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" /></div>
      ) : (
        <>
          <div className="panel overflow-x-auto">
            <table className="w-full text-sm min-w-[48rem]">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-5 py-3">User</th>
                  <th className="text-left px-5 py-3">Ticker</th>
                  <th className="text-left px-5 py-3">Period</th>
                  <th className="text-right px-5 py-3">Total Return</th>
                  <th className="text-right px-5 py-3">Sharpe</th>
                  <th className="text-right px-5 py-3">Max DD</th>
                  <th className="text-right px-5 py-3">Date</th>
                  <th className="text-right px-5 py-3">Duration</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.runId} className="border-b border-border/50 hover:bg-border/20 transition-colors">
                    <td className="px-5 py-3 text-text-muted text-xs font-mono truncate max-w-[160px]">{run.email}</td>
                    <td className="px-5 py-3 font-semibold text-text-primary font-mono text-xs">{run.ticker}</td>
                    <td className="px-5 py-3 text-text-muted text-xs font-mono">{run.start} → {run.end}</td>
                    <td className={`px-5 py-3 text-right font-mono text-xs ${run.metrics?.total_return >= 0 ? "text-success" : "text-danger"}`}>
                      {fmtPct(run.metrics?.total_return)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-xs">{run.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}</td>
                    <td className="px-5 py-3 text-right font-mono text-xs text-danger">{fmtPct(run.metrics?.max_drawdown)}</td>
                    <td className="px-5 py-3 text-right text-xs text-text-muted">{fmtDate(run.createdAt)}</td>
                    <td className="px-5 py-3 text-right font-mono text-xs text-text-muted">
                      {run.durationMs ? `${(run.durationMs / 1000).toFixed(1)}s` : "—"}
                    </td>
                  </tr>
                ))}
                {runs.length === 0 && (
                  <tr><td colSpan={8} className="text-center py-12 text-text-muted">No runs found.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="text-sm text-text-muted hover:text-text-primary disabled:opacity-30">← Previous</button>
              <span className="text-xs text-text-muted">{page + 1} / {totalPages}</span>
              <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page === totalPages - 1} className="text-sm text-text-muted hover:text-text-primary disabled:opacity-30">Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
