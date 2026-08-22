import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory, compareRuns } from "../api";
import { SkeletonRows } from "../components/SkeletonRow";
import { DEFAULTS, STRATEGIES } from "../components/ConfigPanel";
import ComparisonPanel from "../components/ComparisonPanel";
import { useToast } from "../hooks/useToast";

// Matches the server-side cap in CompareRequest. Beyond four the chart stops
// being readable and each run costs a data fetch plus a full recompute.
const MAX_COMPARE = 4;

const strategyLabel = (id) =>
  STRATEGIES.find((s) => s.id === id)?.label || "Momentum";

const PAGE_SIZE = 20;

// Mirrors the 8 columns of the history table so the skeleton matches its shape.
const SKELETON_WIDTHS = ["70%", "45%", "85%", "55%", "40%", "50%", "40%", "45%"];

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

function fmtDate(ts) {
  if (!ts) return "—";
  const d = ts.toDate ? ts.toDate() : new Date(ts._seconds * 1000);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  const [picked, setPicked] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError("");
    getHistory(PAGE_SIZE, page * PAGE_SIZE)
      .then((d) => {
        setRuns(d.runs);
        setTotal(d.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function togglePick(runId) {
    setPicked((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId);
      if (prev.length >= MAX_COMPARE) {
        showToast(`Compare up to ${MAX_COMPARE} runs at once`, "info");
        return prev;
      }
      return [...prev, runId];
    });
  }

  async function handleCompare() {
    setError("");
    setComparing(true);
    try {
      const data = await compareRuns(picked);
      setComparison(data);
      if (data.overlapping_days === 0) {
        showToast("These runs cover periods that never overlap", "info");
      }
    } catch (err) {
      const message = err.message || "Comparison failed.";
      setError(message);
      showToast(message, "error");
    } finally {
      setComparing(false);
    }
  }

  function clearComparison() {
    setComparison(null);
    setPicked([]);
  }

  function handleReRun(run) {
    // Start from DEFAULTS so every strategy's parameters exist, then layer the
    // run's own values on top — otherwise switching strategy in the panel would
    // hit undefined inputs. Older runs have no `strategy` field; those are momentum.
    navigate("/dashboard", {
      state: {
        params: {
          ...DEFAULTS,
          ...run.params,
          strategy: run.strategy || "momentum",
          ticker: run.ticker,
          start: run.start,
          end: run.end,
        },
      },
    });
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-baseline justify-between gap-4 flex-wrap mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Run History</h1>
        {!comparison && runs.length > 1 && (
          <p className="text-xs text-text-muted">
            Tick two or more runs to overlay their equity curves
          </p>
        )}
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-5 py-4 mb-5">{error}</div>
      )}

      {comparison ? (
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h2 className="text-sm font-semibold text-text-primary">Comparison</h2>
            <button
              onClick={clearComparison}
              className="text-xs text-text-muted hover:text-accent border border-border hover:border-accent rounded-lg px-3 py-1.5 transition-colors"
            >
              ← Back to history
            </button>
          </div>
          <ComparisonPanel data={comparison} />
        </div>
      ) : (
      <>
          <div className="panel overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs uppercase tracking-wider">
                  <th className="w-10 px-4 py-3" />
                  <th className="text-left px-5 py-3">Date</th>
                  <th className="text-left px-5 py-3">Ticker</th>
                  <th className="text-left px-5 py-3">Period</th>
                  <th className="text-right px-5 py-3">Total Return</th>
                  <th className="text-right px-5 py-3">Sharpe</th>
                  <th className="text-right px-5 py-3">Max DD</th>
                  <th className="text-right px-5 py-3">Duration</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {loading && <SkeletonRows rows={8} widths={SKELETON_WIDTHS} />}
                {!loading && runs.map((run) => (
                  <tr
                    key={run.runId}
                    className="border-b border-border/50 hover:bg-border/20 cursor-pointer transition-colors"
                    onClick={() => setSelected(run)}
                  >
                    <td className="w-10 px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={picked.includes(run.runId)}
                        onChange={() => togglePick(run.runId)}
                        aria-label={`Select ${run.ticker} run for comparison`}
                        className="w-4 h-4 accent-accent cursor-pointer align-middle"
                      />
                    </td>
                    <td className="px-5 py-3 text-text-muted font-mono text-xs">{fmtDate(run.createdAt)}</td>
                    <td className="px-5 py-3 font-semibold text-text-primary font-mono">
                      <div className="flex items-center gap-2">
                        {run.ticker}
                        <span className="text-2xs font-mono font-normal uppercase tracking-wider text-text-muted border border-border rounded px-1.5 py-0.5">
                          {strategyLabel(run.strategy)}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-text-muted text-xs font-mono">{run.start} → {run.end}</td>
                    <td className={`px-5 py-3 text-right font-mono text-xs ${run.metrics?.total_return >= 0 ? "text-success" : "text-danger"}`}>
                      {fmtPct(run.metrics?.total_return)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-xs text-text-primary">
                      {run.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-xs text-danger">
                      {fmtPct(run.metrics?.max_drawdown)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-xs text-text-muted">
                      {run.durationMs ? `${(run.durationMs / 1000).toFixed(1)}s` : "—"}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleReRun(run); }}
                        className="text-xs text-accent hover:underline"
                      >
                        Re-run
                      </button>
                    </td>
                  </tr>
                ))}
                {!loading && runs.length === 0 && (
                  <tr>
                    <td colSpan={9} className="text-center py-12 text-text-muted">
                      No runs yet. Go to Dashboard to run your first backtest.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {!loading && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="text-sm text-text-muted hover:text-text-primary disabled:opacity-30"
              >
                ← Previous
              </button>
              <span className="text-xs text-text-muted">{page + 1} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page === totalPages - 1}
                className="text-sm text-text-muted hover:text-text-primary disabled:opacity-30"
              >
                Next →
              </button>
            </div>
          )}
      </>
      )}

      {/* Compare bar — only once a comparison is actually possible */}
      {!comparison && picked.length > 0 && (
        <div className="sticky bottom-4 mt-4 flex items-center justify-between gap-3 flex-wrap bg-surface border border-accent/40 rounded-xl px-5 py-3 shadow-2xl">
          <span className="text-sm text-text-primary">
            {picked.length} run{picked.length === 1 ? "" : "s"} selected
            {picked.length === 1 && (
              <span className="text-text-muted"> — pick one more to compare</span>
            )}
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPicked([])}
              className="text-xs text-text-muted hover:text-text-primary transition-colors"
            >
              Clear
            </button>
            <button
              onClick={handleCompare}
              disabled={picked.length < 2 || comparing}
              className="btn-primary px-5 py-2 text-sm"
            >
              {comparing ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Recomputing…
                </>
              ) : (
                "Compare"
              )}
            </button>
          </div>
        </div>
      )}

      {/* Detail Drawer */}
      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end" onClick={() => setSelected(null)}>
          <div
            className="w-full max-w-md bg-surface border-l border-border h-full overflow-y-auto p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-text-primary">{selected.ticker} Details</h2>
              <button onClick={() => setSelected(null)} className="text-text-muted hover:text-text-primary">✕</button>
            </div>
            <p className="text-xs text-text-muted font-mono mb-4">
              {selected.start} → {selected.end}
              <span className="ml-2 text-accent">{strategyLabel(selected.strategy)}</span>
            </p>

            <div className="grid grid-cols-2 gap-3 mb-5">
              {Object.entries(selected.metrics || {}).map(([k, v]) => (
                <div key={k} className="bg-bg border border-border rounded-lg p-3">
                  <p className="text-xs text-text-muted uppercase tracking-wider mb-1">{k.replace(/_/g, " ")}</p>
                  <p className="text-sm font-mono text-text-primary">
                    {typeof v === "number" ? v.toFixed(4) : v}
                  </p>
                </div>
              ))}
            </div>

            <div className="border-t border-border pt-4">
              <p className="text-xs text-text-muted mb-2 font-semibold uppercase tracking-wider">Parameters</p>
              <pre className="text-xs text-text-muted font-mono bg-bg rounded-lg p-3 overflow-x-auto">
                {JSON.stringify(selected.params, null, 2)}
              </pre>
            </div>

            <button
              onClick={() => handleReRun(selected)}
              className="btn-primary mt-5 w-full py-2.5 text-sm"
            >
              Re-run this configuration
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
