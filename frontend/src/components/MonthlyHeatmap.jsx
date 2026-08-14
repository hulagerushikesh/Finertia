import React from "react";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Colour a cell by return, scaled against the largest absolute move in the grid
 * so a quiet strategy is not washed out and a violent one is not saturated.
 */
function cellColor(value, peak) {
  if (value === null || value === undefined) return "transparent";
  if (peak === 0) return "rgba(148,163,184,0.10)";
  const intensity = Math.min(Math.abs(value) / peak, 1);
  const alpha = 0.12 + intensity * 0.68;
  return value >= 0 ? `rgba(34,197,94,${alpha})` : `rgba(239,68,68,${alpha})`;
}

export default function MonthlyHeatmap({ data }) {
  if (!data || data.length === 0) return null;

  const years = [...new Set(data.map((d) => d.year))].sort((a, b) => a - b);
  const byYearMonth = new Map(data.map((d) => [`${d.year}-${d.month}`, d.return]));
  const peak = Math.max(...data.map((d) => Math.abs(d.return)), 0);

  // Compounded total per year, shown in a trailing column.
  const yearTotal = (year) =>
    data
      .filter((d) => d.year === year)
      .reduce((acc, d) => acc * (1 + d.return), 1) - 1;

  return (
    <div className="bg-surface border border-border rounded-2xl p-5">
      <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-text-primary">Monthly returns</h3>
        <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
          <span>loss</span>
          <span className="flex">
            {[-1, -0.6, -0.25, 0.25, 0.6, 1].map((v) => (
              <span
                key={v}
                className="w-4 h-2.5 first:rounded-l last:rounded-r"
                style={{ background: cellColor(v, 1) }}
              />
            ))}
          </span>
          <span>gain</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-separate" style={{ borderSpacing: "2px", minWidth: "560px" }}>
          <thead>
            <tr>
              <th className="text-left text-[10px] font-mono text-text-muted font-normal pr-2 w-12" />
              {MONTHS.map((m) => (
                <th key={m} className="text-[10px] font-mono text-text-muted font-normal pb-1">
                  {m}
                </th>
              ))}
              <th className="text-[10px] font-mono text-text-muted font-normal pb-1 pl-2">Year</th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => {
              const total = yearTotal(year);
              return (
                <tr key={year}>
                  <td className="text-[11px] font-mono text-text-muted pr-2 whitespace-nowrap">
                    {year}
                  </td>
                  {MONTHS.map((m, i) => {
                    const v = byYearMonth.get(`${year}-${i + 1}`);
                    const has = v !== undefined;
                    return (
                      <td
                        key={m}
                        title={has ? `${m} ${year}: ${(v * 100).toFixed(2)}%` : `${m} ${year}: no data`}
                        className="text-center text-[10px] font-mono rounded h-7 align-middle"
                        style={{
                          background: has ? cellColor(v, peak) : "rgba(148,163,184,0.04)",
                          color: has ? "#f1f5f9" : "#3a5068",
                        }}
                      >
                        {has ? (v * 100).toFixed(1) : "·"}
                      </td>
                    );
                  })}
                  <td
                    className={`text-center text-[10px] font-mono rounded h-7 pl-2 font-semibold ${
                      total >= 0 ? "text-success" : "text-danger"
                    }`}
                  >
                    {(total * 100).toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-text-muted mt-3">
        Values are percent. Hover any cell for the exact figure.
      </p>
    </div>
  );
}
