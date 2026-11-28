import React from "react";
import { Link } from "react-router-dom";
import { Wordmark } from "./Navbar";

const LINKS = [
  ["/docs", "How it works"],
  ["/demo", "A real result"],
  ["/strategies", "Strategies"],
  ["/learn", "Learn"],
  ["/stocks", "Stocks"],
  ["/writeup", "The write-up"],
  ["/writeup/nifty-50", "The Nifty 50 study"],
  ["/limits", "Limits"],
  ["/support", "Support"],
  ["/privacy", "Privacy"],
  ["/terms", "Terms"],
];

/**
 * The colophon. Exists mainly so /support, /docs and the legal pages are
 * reachable from every page, and to carry the disclaimer where a research note
 * would carry it — at the foot, in small type, on every copy. The wording is
 * the checklist in planning/PRODUCT-PLAN.md section 6: not advice, not
 * registered (India or US), the data's source and terms, non-commercial.
 */
export default function Footer() {
  return (
    <footer className="border-t border-border mt-12">
      {/* Two equal columns on wide screens: with `1fr auto` the long link row
          took its full width and squeezed the disclaimer into a tall, narrow
          block, which made the footer most of a short page. */}
      <div className="max-w-[96rem] mx-auto px-4 sm:px-6 lg:px-8 py-8 grid gap-6 lg:grid-cols-2 items-start">
        <div className="max-w-2xl">
          <Wordmark className="text-lg" />
          <p className="text-xs text-graphite leading-relaxed mt-3" data-testid="disclaimer">
            Backtested results are hypothetical and do not reflect what trading
            this strategy would have returned. Past performance says nothing
            about future performance. Finertia is an educational research tool,
            not investment advice or a recommendation to buy or sell anything. It
            is not registered with SEBI as an investment adviser or research
            analyst, and is not a registered investment adviser in the US.
          </p>
          <p className="text-xs text-graphite leading-relaxed mt-2">
            Price data from Yahoo Finance via the open-source yfinance library,
            for personal, non-commercial use. Not affiliated with Yahoo. Finertia
            is a free, non-commercial personal project.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 lg:justify-end" aria-label="Footer">
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
