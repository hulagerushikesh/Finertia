import React from "react";
import { cn } from "@/lib/utils";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Colour a cell by return, scaled against the largest absolute move in the
 * grid so a quiet strategy is not washed out and a violent one not saturated.
 * Alpha over the semantic gain/loss tokens, so it holds in both themes.
 */
function cellStyle(value, peak) {
  if (value === null || value === undefined) return {};
  if (peak === 0) return { background: "hsl(var(--muted))" };
  const intensity = Math.min(Math.abs(value) / peak, 1);
  const alpha = 0.1 + intensity * 0.6;
  return { background: `hsl(var(${value >= 0 ? "--gain" : "--loss"}) / ${alpha.toFixed(2)})` };
}

export default function MonthlyHeatmap({ data }) {
  if (!data || data.length === 0) return null;

  const years = [...new Set(data.map((d) => d.year))].sort((a, b) => a - b);
  const byYearMonth = new Map(data.map((d) => [`${d.year}-${d.month}`, d.return]));
  const peak = Math.max(...data.map((d) => Math.abs(d.return)), 0);
  const yearTotal = (year) =>
    data.filter((d) => d.year === year).reduce((acc, d) => acc * (1 + d.return), 1) - 1;

  return (
    <section className="sheet px-5 py-4">
      <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
        <h2 className="font-display text-lg font-semibold text-foreground">Monthly returns</h2>
        <div className="flex items-center gap-2 text-2xs font-mono text-graphite">
          <span>loss</span>
          <span className="flex">
            {[-1, -0.6, -0.25, 0.25, 0.6, 1].map((v) => (
              <span key={v} className="w-4 h-2.5 first:rounded-l-sm last:rounded-r-sm" style={cellStyle(v, 1)} />
            ))}
          </span>
          <span>gain</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-separate" style={{ borderSpacing: "2px", minWidth: "560px" }}>
          <thead>
            <tr>
              <th className="w-12" />
              {MONTHS.map((m) => (
                <th key={m} className="text-tick font-mono text-graphite font-normal pb-1">{m}</th>
              ))}
              <th className="text-tick font-mono text-graphite font-normal pb-1 pl-2">Year</th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => {
              const total = yearTotal(year);
              return (
                <tr key={year}>
                  <td className="text-2xs font-mono text-graphite pr-2 whitespace-nowrap">{year}</td>
                  {MONTHS.map((m, i) => {
                    const v = byYearMonth.get(`${year}-${i + 1}`);
                    const has = v !== undefined;
                    return (
                      <td
                        key={m}
                        title={has ? `${m} ${year}: ${(v * 100).toFixed(2)}%` : `${m} ${year}: no data`}
                        className={cn(
                          "text-center text-tick font-mono rounded-sm h-7 align-middle",
                          has ? "text-foreground" : "text-faint bg-muted/40",
                        )}
                        style={has ? cellStyle(v, peak) : undefined}
                      >
                        {has ? (v * 100).toFixed(1) : "·"}
                      </td>
                    );
                  })}
                  <td
                    className={cn(
                      "text-center text-tick font-mono h-7 pl-2 font-medium",
                      total >= 0 ? "text-gain" : "text-loss",
                    )}
                  >
                    {(total * 100).toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-2xs text-graphite mt-3">Values are percent. Hover any cell for the exact figure.</p>
    </section>
  );
}
