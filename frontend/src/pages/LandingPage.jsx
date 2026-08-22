import React from "react";
import { Link } from "react-router-dom";
import RealityTape from "../components/RealityTape";

/**
 * No icons here.
 *
 * The three emoji that used to head these blocks said nothing the sentence
 * underneath did not already say, and a target/gear/chart-bar set is the same
 * one every tool ships. What actually distinguishes these three is *what the
 * engine has to do* to support them, so each leads with that instead.
 */
const CAPABILITIES = [
  {
    tag: "The check",
    title: "Scored on data it never saw",
    desc: "Walk-forward validation refits your parameters on a rolling window and grades them only on the bars that came after. A permutation test then shuffles your signals 500 times to see whether the timing beat luck.",
  },
  {
    tag: "The strategies",
    title: "Three, and they disagree",
    desc: "Momentum and MACD ride trends. Bollinger fades them. Running the same market through strategies that want opposite things is the fastest way to find out what the market was actually doing.",
  },
  {
    tag: "The engine",
    title: "Written out, not imported",
    desc: "No backtesting library. Every signal, position, cost, and metric is pandas and numpy you can read — including the shift that stops tomorrow's price from reaching yesterday's decision.",
  },
];

export default function LandingPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 sm:pt-20 pb-20">
      {/* Hero. Left-aligned: the tape below is read left-to-right off a zero
          line, and a centred headline above it would fight that axis. */}
      <div className="max-w-2xl animate-rise-in">
        <p className="eyebrow mb-5">Backtesting · Walk-forward · Permutation</p>
        <h1 className="text-display-md sm:text-6xl font-extrabold tracking-[-0.03em] leading-[1.02] text-text-primary mb-6">
          Your backtest looks good.
          <br />
          <span className="text-text-faint">That&apos;s the problem.</span>
        </h1>
        <p className="text-base sm:text-lg text-text-muted leading-relaxed mb-8">
          Any strategy can be tuned until its chart points up. Finertia scores
          your parameters on data they were never fitted to, and checks your
          signal timing against random entries — so you find out which results
          survive contact with reality.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/register" className="btn-primary px-6 py-3 text-sm">
            Start backtesting
          </Link>
          <Link to="/demo" className="btn-secondary px-6 py-3 text-sm">
            See a real result
          </Link>
        </div>
      </div>

      {/* The signature. A live artifact rather than a claim about one. */}
      <div className="mt-14 sm:mt-16">
        <RealityTape />
      </div>

      {/* Capabilities. Hairline rules instead of three more cards — the tape is
          the only box on this page that should read as an object. */}
      <div className="mt-20 grid sm:grid-cols-3 gap-px bg-border">
        {CAPABILITIES.map((c) => (
          <div key={c.tag} className="bg-bg sm:px-6 py-6 sm:py-7 first:sm:pl-0 last:sm:pr-0">
            <p className="eyebrow mb-3">{c.tag}</p>
            <h2 className="text-base font-semibold text-text-primary mb-2">
              {c.title}
            </h2>
            <p className="text-sm text-text-muted leading-relaxed">{c.desc}</p>
          </div>
        ))}
      </div>

      {/* Proof, stated once and quietly. Three big numbers in boxes claimed
          more importance than a dependency count deserves. */}
      <p className="mt-12 text-xs font-mono text-text-faint leading-relaxed">
        0 external backtesting dependencies · 12 performance metrics · 404 tests
        on the engine
      </p>
    </div>
  );
}
