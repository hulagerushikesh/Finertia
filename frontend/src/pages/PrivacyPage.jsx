import React from "react";
import { Link } from "react-router-dom";
import { DocSection as Section, DocHeader } from "../components/Prose";
import { Rise } from "../components/motion";
import { SUPPORT_EMAIL } from "../lib/contact";
import { usePageTitle } from "../hooks/usePageTitle";

/** Last changed. Update it with any change to what is collected or why. */
const UPDATED = "24 November 2026";

/**
 * The privacy notice (India's DPDP Act 2023 asks for one; it is also simply
 * what a user is owed). Every claim here is checked against the code: what the
 * API stores (users/{uid}, runs/{id}), what Sentry receives (uid only,
 * send_default_pii off), and Vercel's cookieless page counter.
 */
export default function PrivacyPage() {
  usePageTitle("privacy");
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow="Privacy" title="What Finertia keeps about you, and why.">
          Finertia is a free, non-commercial personal project. It keeps as little as it can, sells
          nothing, and shows no ads. Last updated {UPDATED}.
        </DocHeader>
      </Rise>

      <div className="flex flex-col gap-12">
        <Section id="collected" title="What is stored">
          <p>
            <strong className="text-foreground font-medium">Your account:</strong> your email address and a
            password handled by Google Firebase Authentication (Finertia never sees the password), and
            the date you joined.
          </p>
          <p>
            <strong className="text-foreground font-medium">Your runs:</strong> the settings of each backtest
            you save (ticker, dates, strategy, parameters) and its summary figures, so History and
            Compare work.
          </p>
          <p>
            <strong className="text-foreground font-medium">Usage counters:</strong> how many runs and
            validations you have used this month, to apply the fair-use limits.
          </p>
          <p>
            <strong className="text-foreground font-medium">Error reports:</strong> when something breaks,
            the error and your account id (not your email, and not what you typed) go to Sentry, an
            error-tracking service.
          </p>
          <p>
            <strong className="text-foreground font-medium">Visits:</strong> page views are counted by
            Vercel Web Analytics without cookies and without identifying you.
          </p>
        </Section>

        <Section id="not-collected" title="What is not">
          <p>
            No payment details (nothing is sold), no tracking or advertising cookies, no selling or
            sharing of your data with anyone for marketing.
          </p>
        </Section>

        <Section id="where" title="Where it lives">
          <p>
            On Google Cloud and Firebase (United States) and Vercel. Backups are kept for up to 14
            weeks so a mistake can be undone.
          </p>
        </Section>

        <Section id="rights" title="Your choices">
          <p>
            From your <Link to="/profile" className="text-pencil underline underline-offset-2">profile</Link>{" "}
            you can download everything stored about you, and delete your account and all its runs.
            Deletion removes them from the live database at once; backups age out within 14 weeks.
          </p>
          <p>
            Questions, or a request you cannot make from the profile:{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-pencil underline underline-offset-2">
              {SUPPORT_EMAIL}
            </a>
            .
          </p>
        </Section>
      </div>
    </div>
  );
}
