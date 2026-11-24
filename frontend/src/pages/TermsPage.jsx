import React from "react";
import { Link } from "react-router-dom";
import { DocSection as Section, DocHeader } from "../components/Prose";
import { Rise } from "../components/motion";
import { SUPPORT_EMAIL } from "../lib/contact";
import { usePageTitle } from "../hooks/usePageTitle";

const UPDATED = "24 November 2026";

/**
 * Terms of use. Written to match what Finertia is (a free, non-commercial
 * personal project on Yahoo Finance data, no advice) and kept in step with
 * planning/PRODUCT-PLAN.md section 6. Not reviewed by a lawyer; that review
 * comes before anything commercial.
 */
export default function TermsPage() {
  usePageTitle("terms");
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow="Terms" title="Terms of use.">
          Plain terms for a free research tool. By using Finertia you agree to them. Last updated{" "}
          {UPDATED}.
        </DocHeader>
      </Rise>

      <div className="flex flex-col gap-12">
        <Section id="what" title="What Finertia is">
          <p>
            A free, non-commercial personal project for learning about and testing trading rules on
            past prices. It is provided as is, without warranties of any kind, and may change, pause or
            stop at any time.
          </p>
        </Section>

        <Section id="not-advice" title="Not advice">
          <p>
            Nothing on Finertia is investment, financial, tax or legal advice, or a recommendation to
            buy or sell any security. Results are hypothetical, computed on past data, and say nothing
            about future performance. Finertia is not registered with the Securities and Exchange
            Board of India (SEBI) as an investment adviser or research analyst, and is not a
            registered investment adviser or broker-dealer in the United States or anywhere else. Any
            decision you make with real money is yours alone.
          </p>
        </Section>

        <Section id="data" title="The data">
          <p>
            Prices come from Yahoo Finance through the open-source yfinance library and may be
            delayed, adjusted, incomplete or wrong. Finertia is not affiliated with, endorsed by, or
            connected to Yahoo. Use what you see for personal, non-commercial purposes only, and do not
            use Finertia to collect or redistribute price data.
          </p>
        </Section>

        <Section id="use" title="Fair use">
          <p>
            Use Finertia as a person would: no automated scraping, no attempts to get around the{" "}
            <Link to="/limits" className="text-pencil underline underline-offset-2">limits</Link>, no
            attacks on the service. Accounts that abuse it may be suspended.
          </p>
        </Section>

        <Section id="liability" title="Liability">
          <p>
            To the extent the law allows, the author is not liable for any loss arising from use of
            Finertia, including losses from trading decisions.
          </p>
        </Section>

        <Section id="contact" title="Contact">
          <p>
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-pencil underline underline-offset-2">
              {SUPPORT_EMAIL}
            </a>
            . How your data is handled is in the{" "}
            <Link to="/privacy" className="text-pencil underline underline-offset-2">privacy notice</Link>.
          </p>
        </Section>
      </div>
    </div>
  );
}
