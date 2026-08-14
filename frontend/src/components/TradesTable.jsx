import React, { useState } from "react";

const PAGE_SIZE = 20;

function posLabel(pos) {
  if (pos === 1) return { text: "Long", cls: "text-success bg-success/10" };
  if (pos === -1) return { text: "Short", cls: "text-danger bg-danger/10" };
  return { text: "Flat", cls: "text-text-muted bg-border/40" };
}

export default function TradesTable({ trades }) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(trades.length / PAGE_SIZE);
  const slice = trades.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">Trade Log</h3>
        <span className="text-xs text-text-muted">{trades.length} entries</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-border text-text-muted">
              <th className="text-left pb-2 pr-4">Date</th>
              <th className="text-left pb-2 pr-4">Position</th>
              <th className="text-right pb-2 pr-4">Daily Return</th>
              <th className="text-right pb-2">Equity</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((row, i) => {
              const { text, cls } = posLabel(row.position);
              const retColor =
                row.daily_return > 0
                  ? "text-success"
                  : row.daily_return < 0
                  ? "text-danger"
                  : "text-text-muted";
              return (
                <tr
                  key={i}
                  className={`border-b border-border/40 hover:bg-border/20 transition-colors ${
                    row.position === 1
                      ? "bg-success/5"
                      : row.position === -1
                      ? "bg-danger/5"
                      : ""
                  }`}
                >
                  <td className="py-1.5 pr-4 text-text-muted">{row.date}</td>
                  <td className="py-1.5 pr-4">
                    <span className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${cls}`}>
                      {text}
                    </span>
                  </td>
                  <td className={`py-1.5 pr-4 text-right ${retColor}`}>
                    {(row.daily_return * 100).toFixed(3)}%
                  </td>
                  <td className="py-1.5 text-right text-text-primary">
                    {row.equity.toFixed(4)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="text-xs text-text-muted hover:text-text-primary disabled:opacity-30 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs text-text-muted">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="text-xs text-text-muted hover:text-text-primary disabled:opacity-30 transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
