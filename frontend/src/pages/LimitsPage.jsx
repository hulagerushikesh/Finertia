import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPlans } from "../api";
import { DocSection as Section, DocHeader } from "../components/Prose";
import { Rise } from "../components/motion";
import { SUPPORT_EMAIL } from "../lib/contact";
import { usePageTitle } from "../hooks/usePageTitle";
// The plan the API serves, kept in step by a backend test (tests/test_plans.py).
// The page starts from this copy so the build can pre-render it and a cold API
// never leaves it empty; /api/plans then confirms it.
import PLANS from "../lib/plans.json";

/**
 * What Finertia costs (nothing) and the fair-use limits that keep it running.
 *
 * Replaced the pricing page on 24 Nov (DECISIONS: personal project, Yahoo
 * data). Nothing is for sale, so there is no plan comparison and no checkout.
 */
export default function LimitsPage() {
  usePageTitle("limits");
  const [plan, setPlan] = useState(PLANS[0]);

  useEffect(() => {
    getPlans()
      .then((d) => d.plans?.[0] && setPlan(d.plans[0]))
      // The build's copy is already on screen; nothing to tell the reader.
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow="Limits" title="Free to use, with fair-use limits.">
          Finertia is a personal, non-commercial project. Nothing is for sale: no plans, no card, no
          ads. The limits below keep one small shared server and its free data source working for
          everyone.
        </DocHeader>
      </Rise>

      <div className="flex flex-col gap-12">
        <Section id="limits" title="Every account gets">
          <ul className="flex flex-col gap-2" data-testid="limits-list">
            {plan.features.map((f) => (
              <li key={f} className="pl-4 border-l-2 border-pencil/40">
                {f}
              </li>
            ))}
          </ul>
          <p>
            Limits count per calendar month in UTC and reset on the first. A short per-minute limit
            also stops bursts; waiting a few seconds clears it.
          </p>
        </Section>

        <Section id="why-free" title="Why it is free">
          <p>
            Prices come from Yahoo Finance through the open-source yfinance library. That data may be
            used for personal, non-commercial purposes, so Finertia stays a free project and never
            charges for access. Finertia is not affiliated with, endorsed by, or connected to Yahoo.
          </p>
        </Section>

        <Section id="more" title="Need more?">
          <p>
            If you are using Finertia for study or research and the limits get in the way, write to{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-pencil underline underline-offset-2">
              {SUPPORT_EMAIL}
            </a>
            . Read the <Link to="/terms" className="text-pencil underline underline-offset-2">terms of use</Link>{" "}
            and the <Link to="/privacy" className="text-pencil underline underline-offset-2">privacy notice</Link>.
          </p>
        </Section>
      </div>
    </div>
  );
}
