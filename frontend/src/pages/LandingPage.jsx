import React from "react";
import { Link } from "react-router-dom";
import { m, useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/button";
import RealityTape from "../components/RealityTape";
import { Rise, Stagger, StaggerItem, EASE_OUT } from "../components/motion";

/**
 * Three things, one sentence each. The method names (walk-forward,
 * deflated Sharpe, permutation) live in /docs; a first-time reader should
 * get the idea without them. No icons: a target/gear/chart-bar set is the
 * same one every tool ships.
 */
const CAPABILITIES = [
  {
    tag: "The check",
    title: "Tested on years it never saw",
    desc: "Parameters are chosen on the early part of the period and scored on the later part. Only the later score counts.",
  },
  {
    tag: "The correction",
    title: "Graded against cherry-picking",
    desc: "Try sixteen settings and keep the best, and the best will look good on its own. The result is marked against that.",
  },
  {
    tag: "The engine",
    title: "Maths you can read",
    desc: "No backtesting library. Every signal, cost and metric is plain pandas and numpy you can open and check.",
  },
];

/**
 * The split, drawn. In-sample on the left in ink, a purged gap, then the
 * out-of-sample stretch marked in pencil — the only bars that count.
 */
function SplitDiagram() {
  const off = useReducedMotion();
  return (
    <svg viewBox="0 0 600 64" className="w-full h-16" aria-hidden="true">
      <line x1="0" y1="40" x2="600" y2="40" stroke="hsl(var(--border-strong))" strokeWidth="1" />
      <m.rect
        x="0" y="34" width="400" height="12" fill="hsl(var(--foreground))"
        initial={off ? false : { scaleX: 0 }} animate={{ scaleX: 1 }}
        transition={{ duration: 0.8, ease: EASE_OUT }} style={{ transformOrigin: "0 40px" }}
      />
      <rect x="400" y="34" width="24" height="12" fill="hsl(var(--border))" />
      <m.rect
        x="424" y="34" width="176" height="12" fill="hsl(var(--pencil))"
        initial={off ? false : { scaleX: 0 }} animate={{ scaleX: 1 }}
        transition={{ duration: 0.6, delay: 0.6, ease: EASE_OUT }} style={{ transformOrigin: "424px 40px" }}
      />
      <text x="0" y="20" fontFamily="IBM Plex Mono" fontSize="10" fill="hsl(var(--muted-foreground))" letterSpacing="1.4">
        TUNED HERE · 70%
      </text>
      <text x="412" y="60" fontFamily="IBM Plex Mono" fontSize="9" fill="hsl(var(--muted-foreground))" textAnchor="middle">
        gap
      </text>
      <text x="600" y="20" fontFamily="IBM Plex Mono" fontSize="10" fill="hsl(var(--pencil))" letterSpacing="1.4" textAnchor="end">
        SCORED HERE · 30%
      </text>
    </svg>
  );
}

export default function LandingPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-20">
      {/* Hero. Left-aligned: the tape below is read left-to-right off a zero
          line, and a centred headline above it would fight that axis. */}
      <Rise className="max-w-3xl">
        <p className="eyebrow mb-6">Backtest · then check it&apos;s real</p>
        <h1 className="font-display font-medium text-display-md sm:text-display-lg lg:text-display-xl tracking-[-0.02em] text-foreground text-balance">
          Your backtest looks good.
          <br />
          That&apos;s the <em className="italic text-pencil">problem.</em>
        </h1>
        <p className="text-base sm:text-lg text-graphite leading-relaxed mt-7 max-w-2xl">
          Pick a stock and a strategy. Finertia runs it on real prices, then re-tests the result
          on years it was never tuned on. If the number was luck, you find out here — not after
          you trade it.
        </p>
        <div className="flex flex-wrap items-center gap-3 mt-9">
          <Button asChild size="lg">
            <Link to="/register">Run a backtest</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/demo">See a real result</Link>
          </Button>
        </div>
      </Rise>

      {/* The signature. A live artifact rather than a claim about one. */}
      <Rise delay={0.12} className="mt-16 sm:mt-20">
        <RealityTape />
      </Rise>

      {/* Capabilities. Hairline rules instead of three more cards — the tape
          is the only box on this page that should read as an object. */}
      <Stagger className="mt-20 grid sm:grid-cols-3 gap-px bg-border border-y border-border">
        {CAPABILITIES.map((c) => (
          <StaggerItem key={c.tag} className="bg-background py-7 sm:px-6 first:sm:pl-0 last:sm:pr-0">
            <p className="eyebrow mb-3">{c.tag}</p>
            <h2 className="font-display text-xl font-medium text-foreground mb-2 text-balance">{c.title}</h2>
            <p className="text-sm text-graphite leading-relaxed">{c.desc}</p>
          </StaggerItem>
        ))}
      </Stagger>
      <p className="mt-4 text-sm">
        <Link to="/docs" className="text-pencil hover:underline underline-offset-4">
          How each check works, with the formulas →
        </Link>
      </p>

      {/* The method, drawn once. */}
      <div className="mt-20 grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-10 items-center">
        <div>
          <p className="eyebrow mb-3">How to read a result</p>
          <h2 className="font-display text-display-sm font-medium text-foreground text-balance">
            The blue stretch is the only part that counts.
          </h2>
          <p className="text-sm text-graphite leading-relaxed mt-4 max-w-md">
            Parameters are tuned on the first 70% of the period. The last 30% is scored untouched.
            Every number from that stretch is{" "}
            <span className="pencil-mark text-foreground">underlined like this</span> across the
            app, so you always know which figures were actually checked.
          </p>
        </div>
        <div className="sheet px-6 py-6 graph-paper">
          <SplitDiagram />
        </div>
      </div>

      {/* Proof, stated once and quietly. */}
      <p className="mt-16 text-xs font-mono text-faint leading-relaxed">
        0 external backtesting dependencies · 12 metrics, each with a confidence interval · 603
        tests on the engine
      </p>
    </div>
  );
}
