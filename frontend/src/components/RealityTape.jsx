import React from "react";

/**
 * The landing page's one bold element: five years of a real result, laid out
 * the way the product thinks.
 *
 * Every screen in Finertia sets a number you measured beside the thing that
 * tests it, so the palette is two-toned throughout — violet is the strategy,
 * mint is the reference it has to beat. This is that idea at full size, and it
 * does the argument better than a claim could: the strategy below beat simply
 * holding the stock in exactly one year out of five, and that year was the one
 * the market fell.
 *
 * Numbers are copied from `src/demoData.json` (AAPL, momentum 20/50, 0.1% cost)
 * rather than imported: that file is 43 kB of equity curve, and pulling it into
 * the landing bundle to read five rows would cost first paint more than the
 * duplication costs maintenance.
 */
const YEARS = [
  { year: 2019, strategy: 0.29297, benchmark: 0.887425 },
  { year: 2020, strategy: 0.261048, benchmark: 0.823067 },
  { year: 2021, strategy: 0.228419, benchmark: 0.346482 },
  { year: 2022, strategy: -0.228735, benchmark: -0.264042 },
  { year: 2023, strategy: 0.090031, benchmark: 0.490081 },
];

// Zero sits left of centre because the losing year is far smaller than the best
// winning one — centring it would waste most of the track on empty space.
const ZERO = 22;
const SPAN = 100 - ZERO;
const MAX = Math.max(...YEARS.flatMap((r) => [Math.abs(r.strategy), Math.abs(r.benchmark)]));

function pct(v) {
  return `${v > 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
}

function Bar({ value, tone, delay }) {
  const width = (Math.abs(value) / MAX) * SPAN;
  const positive = value >= 0;
  return (
    <span
      className={`absolute top-0 bottom-0 rounded-[2px] animate-sweep-in ${
        tone === "strategy" ? "bg-accent" : "bg-check/70"
      }`}
      style={{
        left: positive ? `${ZERO}%` : `${ZERO - width}%`,
        width: `${width}%`,
        // Grow away from the zero line, so the axis stays put and only the
        // reading moves — the way a needle behaves.
        transformOrigin: positive ? "left" : "right",
        animationDelay: `${delay}ms`,
      }}
    />
  );
}

export default function RealityTape() {
  const wins = YEARS.filter((r) => r.strategy > r.benchmark).length;

  return (
    <figure className="panel-lifted overflow-hidden">
      <figcaption className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 border-b border-border">
        <span className="eyebrow">AAPL · Momentum 20/50 · 0.1% cost</span>
        <span className="flex-1" />
        <span className="flex items-center gap-1.5 text-2xs font-mono text-text-muted">
          <span className="w-2 h-2 rounded-[2px] bg-accent" aria-hidden="true" />
          Strategy
        </span>
        <span className="flex items-center gap-1.5 text-2xs font-mono text-text-muted">
          <span className="w-2 h-2 rounded-[2px] bg-check/70" aria-hidden="true" />
          Buy &amp; hold
        </span>
      </figcaption>

      <div className="px-5 py-5 flex flex-col gap-3.5">
        {YEARS.map((row, i) => {
          const beat = row.strategy > row.benchmark;
          return (
            <div key={row.year} className="flex items-center gap-3 sm:gap-4">
              <span className="w-9 shrink-0 text-2xs font-mono text-text-faint">
                {row.year}
              </span>

              <span className="relative flex-1 h-7 min-w-0">
                {/* The zero line. Everything is read against it. */}
                <span
                  aria-hidden="true"
                  className="absolute top-0 bottom-0 w-px bg-border-strong"
                  style={{ left: `${ZERO}%` }}
                />
                <span className="absolute inset-x-0 top-0 h-3">
                  <Bar value={row.strategy} tone="strategy" delay={i * 90} />
                </span>
                <span className="absolute inset-x-0 bottom-0 h-3">
                  <Bar value={row.benchmark} tone="benchmark" delay={i * 90 + 45} />
                </span>
              </span>

              <span className="w-[5.5rem] sm:w-28 shrink-0 text-right text-2xs font-mono leading-tight">
                <span className={beat ? "text-accent" : "text-text-muted"}>
                  {pct(row.strategy)}
                </span>
                <span className="text-text-faint px-1">vs</span>
                <span className="text-text-muted">{pct(row.benchmark)}</span>
              </span>
            </div>
          );
        })}
      </div>

      <p className="border-t border-border px-5 py-3.5 text-xs text-text-muted leading-relaxed">
        <span className="text-text-primary font-medium">
          Beat buy &amp; hold in {wins} year of {YEARS.length}
        </span>{" "}
        — the one the market fell. Over the full period the strategy returned
        <span className="font-mono text-text-primary"> +68.4%</span> against
        <span className="font-mono text-text-primary"> +408%</span> for holding
        the stock. That is the engine's real output, not an illustration.
      </p>
    </figure>
  );
}
