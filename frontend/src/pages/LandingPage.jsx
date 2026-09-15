import React from "react";
import { Link } from "react-router-dom";
import { m, useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/button";
import RealityTape from "../components/RealityTape";
import { Rise, Stagger, StaggerItem, EASE_OUT } from "../components/motion";

/**
 * What distinguishes these three is what the engine has to *do* to support
 * them, so each leads with that. No icons: a target/gear/chart-bar set is the
 * same one every tool ships.
 */
const CAPABILITIES = [
  {
    tag: "The check",
    title: "Scored on data it never saw",
    desc: "Walk-forward validation refits your parameters on the earlier part of the period and grades them only on the bars that came after. A permutation test then shuffles your signals 500 times to see whether the timing beat luck.",
  },
  {
    tag: "The correction",
    title: "Deflated for the search that found it",
    desc: "Picking the best of sixteen combinations is itself a search, and the winner of any search looks good. The Sharpe is measured against what that search would have produced on data with no edge at all.",
  },
  {
    tag: "The engine",
    title: "Written out, not imported",
    desc: "No backtesting library. Every signal, position, cost, and metric is pandas and numpy you can read — including the one-bar shift that stops tomorrow's price from reaching yesterday's decision.",
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
        <p className="eyebrow mb-6">Backtesting · Walk-forward · Permutation · Bootstrap</p>
        <h1 className="font-display font-medium text-display-md sm:text-display-lg lg:text-display-xl tracking-[-0.02em] text-foreground text-balance">
          Your backtest looks good.
          <br />
          That&apos;s the <em className="italic text-pencil">problem.</em>
        </h1>
        <p className="text-base sm:text-lg text-graphite leading-relaxed mt-7 max-w-2xl">
          Any strategy can be tuned until its chart points up. Finertia scores your parameters on
          data they were never fitted to, checks your timing against random entries, and puts a
          confidence interval on every number — so you find out which results survive contact
          with reality.
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

      {/* The method, drawn once. */}
      <div className="mt-20 grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-10 items-center">
        <div>
          <p className="eyebrow mb-3">How a result gets marked</p>
          <h2 className="font-display text-display-sm font-medium text-foreground text-balance">
            Only the pencil-marked bars are evidence.
          </h2>
          <p className="text-sm text-graphite leading-relaxed mt-4 max-w-md">
            Parameters are chosen on the first 70% of the period, a purged gap removes the trade
            straddling the cut, and the remaining 30% is scored untouched. Every out-of-sample
            figure in the app is underlined in pencil, so you always know which number was checked.
          </p>
        </div>
        <div className="sheet px-6 py-6 graph-paper">
          <SplitDiagram />
        </div>
      </div>

      {/* Proof, stated once and quietly. */}
      <p className="mt-16 text-xs font-mono text-faint leading-relaxed">
        0 external backtesting dependencies · 12 metrics, each with a bootstrap interval · 535
        tests on the engine
      </p>
    </div>
  );
}
