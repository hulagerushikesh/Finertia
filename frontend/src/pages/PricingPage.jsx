import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getPlans, startCheckout } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";

export default function PricingPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [plans, setPlans] = useState([]);
  const [billingEnabled, setBillingEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    getPlans()
      .then((d) => {
        setPlans(d.plans);
        setBillingEnabled(d.billing_enabled);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpgrade() {
    setRedirecting(true);
    try {
      const { url } = await startCheckout();
      window.location.href = url;
    } catch (err) {
      showToast(err.message || "Could not start checkout.", "error");
      setRedirecting(false);
    }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="max-w-xl mb-10">
        <p className="eyebrow mb-4">Pricing</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-text-primary mb-4">
          Start free. Pay when you want the checks.
        </h1>
        <p className="text-text-muted leading-relaxed">
          Both plans run the same engine on the same data. Pro adds the two
          tests that tell you whether a result is worth anything — and raises
          the monthly run quota.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-5 py-4 mb-6"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid sm:grid-cols-2 gap-5">
          {[0, 1].map((i) => (
            <div key={i} className="panel h-96 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-5 items-start">
          {plans.map((plan) => {
            const isPro = plan.id === "pro";
            return (
              <div
                key={plan.id}
                // The recommended plan is lifted rather than merely outlined.
                // A tinted border alone was doing all the work of saying "this
                // one", which is a lot to ask of one pixel.
                className={`relative rounded-xl p-7 flex flex-col ${
                  isPro
                    ? "bg-surface border border-accent/45 shadow-panel-lifted"
                    : "panel"
                }`}
              >
                {isPro && (
                  <span className="absolute -top-2.5 left-7 text-2xs font-mono font-semibold uppercase tracking-wider bg-accent-strong text-white px-2.5 py-0.5 rounded-full">
                    Recommended
                  </span>
                )}

                <h2 className="text-sm font-semibold text-text-primary mb-4">
                  {plan.label}
                </h2>

                <p className="mb-1 flex items-baseline gap-1.5">
                  <span className="text-[2.75rem] leading-none font-mono font-medium text-text-primary tracking-tight">
                    ${plan.price_monthly}
                  </span>
                  <span className="text-sm text-text-faint">/ month</span>
                </p>
                <p className="eyebrow mb-7">
                  {isPro ? "Cancel any time" : "No card required"}
                </p>

                <ul className="flex flex-col gap-3 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2.5 text-sm text-text-muted leading-relaxed"
                    >
                      <span
                        aria-hidden="true"
                        className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                          isPro ? "bg-accent" : "bg-border-strong"
                        }`}
                      />
                      {f}
                    </li>
                  ))}
                </ul>

                {isPro ? (
                  !user ? (
                    <Link to="/register" className="btn-primary py-2.5 text-sm">
                      Create an account
                    </Link>
                  ) : billingEnabled ? (
                    <button
                      onClick={handleUpgrade}
                      disabled={redirecting}
                      className="btn-primary py-2.5 text-sm"
                    >
                      {redirecting ? "Redirecting…" : "Upgrade to Pro"}
                    </button>
                  ) : (
                    // Self-hosted or pre-launch: showing a button that would
                    // 503 is worse than saying plainly that it is not wired up.
                    <div className="border border-border rounded-lg py-2.5 text-center">
                      <p className="text-xs text-text-faint">
                        Billing is not enabled on this deployment
                      </p>
                    </div>
                  )
                ) : (
                  <Link
                    to={user ? "/dashboard" : "/register"}
                    className="btn-secondary py-2.5 text-sm"
                  >
                    {user ? "Go to dashboard" : "Start free"}
                  </Link>
                )}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-text-faint mt-10 max-w-xl leading-relaxed">
        Quotas count backtests, validation runs, and portfolios, and reset at the
        start of each calendar month (UTC). Cancelling keeps Pro until the end of
        the period you have already paid for.
      </p>
    </main>
  );
}
