import React from "react";
import { Link } from "react-router-dom";

// Set VITE_SUPPORT_EMAIL at build time. The fallback is a placeholder on
// purpose — a wrong address that looks plausible is worse than an obvious one.
const SUPPORT_EMAIL = import.meta.env.VITE_SUPPORT_EMAIL || "support@example.com";

function Section({ id, title, children }) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="text-lg font-semibold text-text-primary mb-3">{title}</h2>
      <div className="flex flex-col gap-3 text-sm text-text-muted leading-relaxed">
        {children}
      </div>
    </section>
  );
}

function Problem({ message, children }) {
  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <p className="bg-bg px-4 py-2.5 font-mono text-xs text-danger border-b border-border">
        {message}
      </p>
      <div className="px-4 py-3 text-sm text-text-muted leading-relaxed">
        {children}
      </div>
    </div>
  );
}

function Question({ q, children }) {
  return (
    <div className="border-l-2 border-border pl-4 py-1">
      <p className="text-text-primary font-medium text-sm mb-1">{q}</p>
      <div className="text-sm text-text-muted leading-relaxed flex flex-col gap-2">
        {children}
      </div>
    </div>
  );
}

export default function SupportPage() {
  const mailto = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
    "Finertia support"
  )}`;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-2">Support</h1>
      <p className="text-sm text-text-muted mb-8">
        Most problems here are one of a handful of specific errors, so the
        common ones are written out below with what actually causes them. If
        yours isn't listed, email us.
      </p>

      {/* Contact */}
      <div className="bg-surface border border-border rounded-2xl p-6 mb-10">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          Get in touch
        </p>
        <a
          href={mailto}
          className="text-accent hover:underline font-mono text-sm break-all"
        >
          {SUPPORT_EMAIL}
        </a>
        <p className="text-sm text-text-muted mt-4 leading-relaxed">
          Include the <span className="text-text-primary">exact error text</span>{" "}
          and the ticker, date range, and strategy you ran. If the run saved, the
          run ID from{" "}
          <Link to="/history" className="text-accent hover:underline">
            History
          </Link>{" "}
          is enough on its own — every parameter is stored with it.
        </p>
        <p className="text-xs text-text-muted mt-3 leading-relaxed">
          This is a solo project, not a staffed desk. Expect a reply in a couple
          of days rather than a couple of hours.
        </p>
      </div>

      <div className="flex flex-col gap-10">
        <Section id="errors" title="Errors you might hit">
          <p>
            These are the messages the API actually returns, and what each one
            means.
          </p>

          <Problem message="No data found for XYZ">
            The symbol didn't resolve with the data provider. Symbols follow
            Yahoo Finance conventions, which differ from some brokers: class
            shares use a hyphen (<span className="font-mono">BRK-B</span>, not
            BRK.B), and non-US listings need their exchange suffix (
            <span className="font-mono">RELIANCE.NS</span>,{" "}
            <span className="font-mono">VOD.L</span>). A delisted ticker returns
            nothing for date ranges after it stopped trading.
          </Problem>

          <Problem message="Only N trading days returned … not enough history for the chosen indicator and sizing windows.">
            Every indicator needs a warm-up period before it can produce a
            signal — a 200-day moving average has no value until day 200 — and
            volatility-targeted sizing adds its own lookback on top. Your date
            range is shorter than the sum. Widen the range or shorten the
            windows. Note that a young stock truncates the range regardless of
            what you asked for: a 2018 start date on a company that listed in
            2021 gives you 2021 onward.
          </Problem>

          <Problem message="You have used all N runs on the free plan this month.">
            A monthly quota, not a speed limit. It resets at the start of the
            next calendar month, counted in UTC. The current allowance is on the{" "}
            <Link to="/pricing" className="text-accent hover:underline">
              pricing page
            </Link>
            , which reads it from the API rather than repeating it — Pro removes
            the cap entirely.
          </Problem>

          <Problem message="Walk-forward validation and the permutation test are Pro features.">
            A single validation run sweeps a whole parameter grid and then
            reshuffles the signals hundreds of times — it costs far more compute
            than one backtest, which is why it sits behind the paid plan rather
            than the quota.
          </Problem>

          <Problem message="Rate limit reached for … Try again in N second(s).">
            A short burst limit measured over the last minute, separate from the
            monthly quota. It means slow down, not upgrade. Waiting the stated
            number of seconds clears it.
          </Problem>

          <Problem message="Your account has been suspended.">
            An administrator has deactivated the account. Email us — it is
            reversible.
          </Problem>
        </Section>

        <Section id="results" title="Questions about the results">
          <Question q="Why are my numbers worse than the same strategy elsewhere?">
            <p>
              Usually because this engine refuses several shortcuts that flatter
              a backtest. Signals are shifted one bar before they are traded, so
              a signal computed from today's close is acted on tomorrow rather
              than at the price that generated it. Stops are evaluated at the
              close, not filled at the trigger price — if a bar gaps 10% through
              a 5% stop, you take the full 10%. Transaction costs are charged in
              proportion to how much the position moved.
            </p>
            <p>
              Together those are worth a lot of apparent performance.{" "}
              <Link to="/docs#lookahead" className="text-accent hover:underline">
                The docs explain each one.
              </Link>
            </p>
          </Question>

          <Question q="Where does the price data come from?">
            <p>
              Daily closing prices from Yahoo Finance, split- and
              dividend-adjusted. There is no intraday data, so the shortest
              holding period any strategy here can express is one day.
            </p>
          </Question>

          <Question q="My strategy shows a great return. Should I trade it?">
            <p>
              Not on the strength of one backtest. A result on a single ticker
              over a single period is one sample, and parameters chosen because
              they looked good on that sample are fitted to it by definition.
              Run walk-forward validation, which scores the same parameters on
              data they were never fitted to, and the permutation test, which
              checks whether your entry timing beat random entries.
            </p>
            <p>
              Nothing here is investment advice, and no backtest models
              liquidity, slippage on size, borrow costs for shorts, or tax.
            </p>
          </Question>

          <Question q="Can I export the results?">
            <p>
              Yes — the dashboard has CSV export for the equity curve and the
              trade list, and the run configuration is encoded in the page URL,
              so copying the address bar shares an exact reproducible setup.
            </p>
          </Question>
        </Section>

        <Section id="account" title="Account, billing, and data">
          <Question q="What do you store?">
            <p>
              Your email and display name, and for each run its configuration
              and summary metrics. Equity curves and drawdown series are{" "}
              <span className="text-text-primary">not</span> stored — they are
              recomputed from the parameters whenever you open a saved run.
            </p>
          </Question>

          <Question q="How do I cancel, or delete my account?">
            <p>
              Email us and we'll do both. There is no self-serve delete button
              yet — saying so is more useful than pointing you at one that
              doesn't exist. Cancelling leaves your saved runs readable on the
              free plan; deletion removes the account and every run with it, and
              cannot be undone.
            </p>
          </Question>

          <Question q="I never got the verification email.">
            <p>
              Check spam first — it comes from a Firebase address, which filters
              often mistrust. The banner at the top of the dashboard resends it,
              with a one-minute wait between attempts. Verification isn't
              required to run backtests; it matters because password resets go
              to that address.
            </p>
          </Question>
        </Section>

        <div className="border-t border-border pt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <Link to="/docs" className="text-accent hover:underline">
            How it works →
          </Link>
          <Link to="/demo" className="text-accent hover:underline">
            See a real run →
          </Link>
          <Link to="/pricing" className="text-accent hover:underline">
            Plans →
          </Link>
        </div>
      </div>
    </div>
  );
}
