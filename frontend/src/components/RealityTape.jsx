import React from "react";
import { m, useReducedMotion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { EASE_OUT } from "./motion";

/**
 * The landing page's one bold element: five years of a real result, marked
 * up the way the product marks everything.
 *
 * Ink is the strategy; graphite, hatched, is buy-and-hold — the reference it
 * has to beat. The verdict is stamped in the corner because that is what a
 * reviewer does with a result: reads it, then writes one word on it.
 *
 * Numbers are copied from `src/demoData.json` (AAPL, momentum 20/50, 0.1%
 * cost) rather than imported: that file is 43 kB of equity curve, and pulling
 * it into the landing bundle to read five rows would cost first paint more
 * than the duplication costs maintenance.
 */
const YEARS = [
  { year: 2019, strategy: 0.29297, benchmark: 0.887425 },
  { year: 2020, strategy: 0.261048, benchmark: 0.823067 },
  { year: 2021, strategy: 0.228419, benchmark: 0.346482 },
  { year: 2022, strategy: -0.228735, benchmark: -0.264042 },
  { year: 2023, strategy: 0.090031, benchmark: 0.490081 },
];

// Zero sits left of centre because the losing year is far smaller than the
// best winning one — centring it would waste most of the track.
const ZERO = 22;
const SPAN = 100 - ZERO;
const MAX = Math.max(...YEARS.flatMap((r) => [Math.abs(r.strategy), Math.abs(r.benchmark)]));

function pct(v) {
  return `${v > 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
}

function Bar({ value, tone, delay }) {
  const off = useReducedMotion();
  const width = (Math.abs(value) / MAX) * SPAN;
  const positive = value >= 0;
  return (
    <m.span
      initial={off ? false : { scaleX: 0 }}
      animate={{ scaleX: 1 }}
      transition={{ duration: 0.7, delay, ease: EASE_OUT }}
      className={
        tone === "strategy"
          ? "absolute top-0 bottom-0 bg-foreground rounded-[1px]"
          : "absolute top-0 bottom-0 rounded-[1px] bg-[repeating-linear-gradient(135deg,hsl(var(--muted-foreground))_0_2px,transparent_2px_5px)]"
      }
      style={{
        left: positive ? `${ZERO}%` : `${ZERO - width}%`,
        width: `${width}%`,
        // Grow away from the zero line, so the axis stays put and only the
        // reading moves — the way a needle behaves.
        transformOrigin: positive ? "left" : "right",
      }}
    />
  );
}

export default function RealityTape() {
  const wins = YEARS.filter((r) => r.strategy > r.benchmark).length;

  return (
    <figure className="sheet-lifted overflow-hidden relative">
      <figcaption className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 border-b border-border">
        <span className="eyebrow">AAPL · Momentum 20/50 · 0.1% cost · 2019–2023</span>
        <span className="flex-1" />
        <span className="flex items-center gap-1.5 text-2xs font-mono text-graphite">
          <span className="w-3 h-2 bg-foreground rounded-[1px]" aria-hidden="true" />
          Strategy
        </span>
        <span className="flex items-center gap-1.5 text-2xs font-mono text-graphite">
          <span
            className="w-3 h-2 rounded-[1px] bg-[repeating-linear-gradient(135deg,hsl(var(--muted-foreground))_0_2px,transparent_2px_5px)]"
            aria-hidden="true"
          />
          Buy &amp; hold
        </span>
      </figcaption>

      <div className="px-5 py-5 flex flex-col gap-3.5">
        {YEARS.map((row, i) => {
          const beat = row.strategy > row.benchmark;
          return (
            <div key={row.year} className="flex items-center gap-3 sm:gap-4">
              <span className="w-9 shrink-0 text-2xs font-mono text-graphite">{row.year}</span>

              <span className="relative flex-1 h-7 min-w-0">
                {/* The zero line. Everything is read against it. */}
                <span
                  aria-hidden="true"
                  className="absolute top-0 bottom-0 w-px bg-rule-strong"
                  style={{ left: `${ZERO}%` }}
                />
                <span className="absolute inset-x-0 top-0 h-3">
                  <Bar value={row.strategy} tone="strategy" delay={0.1 + i * 0.09} />
                </span>
                <span className="absolute inset-x-0 bottom-0 h-3">
                  <Bar value={row.benchmark} tone="benchmark" delay={0.15 + i * 0.09} />
                </span>
              </span>

              <span className="w-[5.5rem] sm:w-28 shrink-0 text-right text-2xs font-mono leading-tight">
                <span className={beat ? "pencil-mark" : "text-foreground"}>{pct(row.strategy)}</span>
                <span className="text-faint px-1">vs</span>
                <span className="text-graphite">{pct(row.benchmark)}</span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="border-t border-border px-5 py-4 flex items-start gap-4 justify-between flex-wrap">
        <p className="text-sm text-graphite leading-relaxed max-w-md">
          <span className="text-foreground font-medium">
            Beat buy &amp; hold in {wins} year of {YEARS.length}
          </span>{" "}
          — the one the market fell. Over the full period the strategy returned
          <span className="font-mono text-foreground"> +68.4%</span> against
          <span className="font-mono text-foreground"> +408%</span> for holding the stock.
          That is the engine's real output, not an illustration.
        </p>
        <Badge variant="loss" className="shrink-0">
          Lost to holding
        </Badge>
      </div>
    </figure>
  );
}
