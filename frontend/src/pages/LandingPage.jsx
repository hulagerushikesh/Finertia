import React from "react";
import { Link } from "react-router-dom";

const features = [
  {
    title: "Overfitting Checks",
    desc: "Walk-forward validation scores your parameters on data they were never fitted to. A permutation test shuffles your signals 500 times to see whether timing actually beat luck.",
    icon: "🎯",
  },
  {
    title: "Three Strategies",
    desc: "Momentum and MACD follow trends; Bollinger fades them. Run one ticker or a 10-name portfolio, with stops and volatility-targeted sizing on top.",
    icon: "⚙",
  },
  {
    title: "Hand-Written Engine",
    desc: "Zero external backtesting libraries. Every signal, position, and metric is pure Python with pandas + numpy, so you can read the exact lines behind your Sharpe ratio.",
    icon: "📊",
  },
];

export default function LandingPage() {
  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-32">
      {/* Hero */}
      <div className="text-center mb-20">
        <div className="inline-flex items-center gap-2 bg-accent/10 border border-accent/20 text-accent text-xs font-medium px-3 py-1 rounded-full mb-6">
          Momentum · MACD · Mean Reversion
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-text-primary mb-6 leading-tight">
          Backtest a Strategy.
          <br />
          <span className="text-accent">Then Find Out If It's Real.</span>
        </h1>
        <p className="text-lg text-text-muted max-w-2xl mx-auto mb-10">
          Any backtest can be tuned until it looks good. Finertia scores your parameters on
          data they were never fitted to, and checks whether your signal timing beats random
          entries — so you learn which results survive contact with reality.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            to="/register"
            className="bg-accent hover:bg-indigo-500 text-white font-semibold px-7 py-3 rounded-xl transition-colors text-sm"
          >
            Start Backtesting
          </Link>
          <Link
            to="/login"
            className="border border-border hover:border-accent/50 text-text-muted hover:text-text-primary font-semibold px-7 py-3 rounded-xl transition-colors text-sm"
          >
            Sign In
          </Link>
        </div>
      </div>

      {/* Features */}
      <div className="grid sm:grid-cols-3 gap-6">
        {features.map((f) => (
          <div
            key={f.title}
            className="bg-surface border border-border rounded-2xl p-6 hover:border-accent/30 transition-colors"
          >
            <div className="text-2xl mb-3">{f.icon}</div>
            <h3 className="font-semibold text-text-primary mb-2">{f.title}</h3>
            <p className="text-sm text-text-muted leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>

      {/* Stat strip */}
      <div className="mt-20 grid grid-cols-3 divide-x divide-border border border-border rounded-2xl overflow-hidden">
        {[
          { label: "External backtesting deps", value: "0" },
          { label: "Performance metrics", value: "12" },
          { label: "Tests on the engine", value: "379" },
        ].map((s) => (
          <div key={s.label} className="bg-surface px-6 py-8 text-center">
            <p className="text-3xl font-bold font-mono text-accent mb-1">{s.value}</p>
            <p className="text-xs text-text-muted">{s.label}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
