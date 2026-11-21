import React from "react";

/**
 * Shown under every /learn article. Finertia is a research tool: it does not
 * predict prices or tell anyone what to buy or sell, and articles must not
 * suggest it does (see learnCompliance.test.jsx and planning/SEO-PLAN.md,
 * "SEBI"). Kept apart from LearnPage so the test can render it without
 * loading Firebase.
 */
export function ResearchNote() {
  return (
    <aside aria-label="About this article" className="border-l-2 border-border pl-4 text-xs text-graphite leading-relaxed max-w-prose">
      Educational research on historical prices. Backtested results are hypothetical: they are
      not what trading would have returned, and past results say nothing about future ones.
      Finertia does not predict prices and does not recommend buying, selling or holding any
      security. It is not investment advice, and Finertia is not a SEBI-registered investment
      adviser or research analyst.
    </aside>
  );
}
