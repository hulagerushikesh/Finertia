import React from "react";
import { Link } from "react-router-dom";
import { Wordmark } from "./Navbar";

const LINKS = [
  ["/docs", "How it works"],
  ["/demo", "A real result"],
  ["/pricing", "Pricing"],
  ["/support", "Support"],
];

/**
 * The colophon. Exists mainly so /support and /docs are reachable from every
 * page, and to carry the disclaimer where a research note would carry it —
 * at the foot, in small type, on every copy.
 */
export default function Footer() {
  return (
    <footer className="border-t border-border mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 grid gap-8 md:grid-cols-[1fr_auto] items-start">
        <div className="max-w-xl">
          <Wordmark className="text-lg" />
          <p className="text-xs text-graphite leading-relaxed mt-3">
            Backtested results are hypothetical and do not reflect what trading
            this strategy would have returned. Past performance says nothing
            about future performance. Finertia is a research tool, not
            investment advice.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2" aria-label="Footer">
          {LINKS.map(([to, label]) => (
            <Link
              key={to}
              to={to}
              className="text-xs text-graphite hover:text-foreground transition-colors rounded-sm"
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
