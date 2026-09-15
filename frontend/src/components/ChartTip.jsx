import React from "react";

/**
 * The tooltip every chart shares. A small card in the sheet colour with a
 * mono body — the same treatment as a margin note, so it reads as part of
 * the document rather than a library default.
 */
export default function ChartTip({ label, rows }) {
  return (
    <div className="bg-popover text-popover-foreground shadow-pop rounded-md px-3 py-2 text-2xs font-mono min-w-[9rem]">
      {label && <p className="text-graphite mb-1">{label}</p>}
      <div className="flex flex-col gap-0.5">
        {rows.map((r) => (
          <p key={r.label} className="flex items-baseline justify-between gap-4">
            <span className="text-graphite">{r.label}</span>
            <span className={r.className || "text-foreground"}>{r.value}</span>
          </p>
        ))}
      </div>
    </div>
  );
}
