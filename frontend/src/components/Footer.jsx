import React from "react";
import { Link } from "react-router-dom";

const LINKS = [
  ["/docs", "How it works"],
  ["/demo", "Live demo"],
  ["/pricing", "Pricing"],
  ["/support", "Support"],
];

/**
 * Exists mainly so /support and /docs are reachable from every page. The navbar
 * is already at its limit — adding two more links there is what breaks it on a
 * phone.
 */
export default function Footer() {
  return (
    <footer className="border-t border-border mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <span className="font-bold text-sm text-text-primary">
            Finertia<span className="text-accent">.</span>
          </span>
          {LINKS.map(([to, label]) => (
            <Link
              key={to}
              to={to}
              className="text-xs text-text-muted hover:text-text-primary transition-colors"
            >
              {label}
            </Link>
          ))}
        </div>
        <p className="text-xs text-text-faint leading-relaxed max-w-2xl">
          Backtested results are hypothetical and do not reflect what trading
          this strategy would have returned. Past performance says nothing about
          future performance. Finertia is a research tool, not investment
          advice.
        </p>
      </div>
    </footer>
  );
}
