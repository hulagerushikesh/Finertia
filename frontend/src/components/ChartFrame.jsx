import React from "react";
import { cn } from "@/lib/utils";

/**
 * The frame every chart sits in: a sheet with a title row, then the plot on
 * graph paper. The grid is drawn by the sheet, not by the chart library, so
 * it is the same 24px grid on every chart and it extends under the axes.
 */
export default function ChartFrame({ title, caption, aside, className, children }) {
  return (
    <section className={cn("sheet overflow-hidden", className)}>
      <div className="flex items-start justify-between gap-4 flex-wrap px-5 pt-4 pb-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-foreground leading-tight">{title}</h2>
          {caption && <p className="text-2xs text-graphite mt-0.5">{caption}</p>}
        </div>
        {aside}
      </div>
      <div className="px-2 pb-3">{children}</div>
    </section>
  );
}

/** SVG defs shared by the bar charts: a graphite hatch for the benchmark. */
export function HatchDefs() {
  return (
    <defs>
      <pattern id="hatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="5" stroke="hsl(var(--muted-foreground))" strokeWidth="1.6" />
      </pattern>
      <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="hsl(var(--loss))" stopOpacity={0.28} />
        <stop offset="100%" stopColor="hsl(var(--loss))" stopOpacity={0.02} />
      </linearGradient>
    </defs>
  );
}
