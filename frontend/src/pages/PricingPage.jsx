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
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-bold text-text-primary mb-3">
          Simple pricing
        </h1>
        <p className="text-text-muted max-w-xl mx-auto">
          Start free. Upgrade when you want the checks that tell you whether a
          result is real.
        </p>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-5 py-4 mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid sm:grid-cols-2 gap-5">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-96 bg-surface border border-border rounded-2xl animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-5">
          {plans.map((plan) => {
            const isPro = plan.id === "pro";
            return (
              <div
                key={plan.id}
                className={`bg-surface border rounded-2xl p-7 flex flex-col ${
                  isPro ? "border-accent/50" : "border-border"
                }`}
              >
                <div className="flex items-baseline justify-between mb-1">
                  <h2 className="text-lg font-semibold text-text-primary">
                    {plan.label}
                  </h2>
                  {isPro && (
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider bg-accent/10 text-accent border border-accent/30 px-2 py-0.5 rounded-full">
                      Recommended
                    </span>
                  )}
                </div>

                <p className="mb-6">
                  <span className="text-4xl font-bold font-mono text-text-primary">
                    ${plan.price_monthly}
                  </span>
                  <span className="text-sm text-text-muted"> / month</span>
                </p>

                <ul className="flex flex-col gap-2.5 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-text-muted">
                      <span className="text-success mt-0.5 flex-shrink-0">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>

                {isPro ? (
                  !user ? (
                    <Link
                      to="/register"
                      className="bg-accent hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-lg text-sm text-center transition-colors"
                    >
                      Create an account
                    </Link>
                  ) : billingEnabled ? (
                    <button
                      onClick={handleUpgrade}
                      disabled={redirecting}
                      className="bg-accent hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
                    >
                      {redirecting ? "Redirecting…" : "Upgrade to Pro"}
                    </button>
                  ) : (
                    // Self-hosted or pre-launch: showing a button that would
                    // 503 is worse than saying plainly that it is not wired up.
                    <div className="border border-border rounded-lg py-2.5 text-center">
                      <p className="text-xs text-text-muted">
                        Billing is not enabled on this deployment
                      </p>
                    </div>
                  )
                ) : (
                  <Link
                    to={user ? "/dashboard" : "/register"}
                    className="border border-border hover:border-accent/50 text-text-muted hover:text-text-primary font-semibold py-2.5 rounded-lg text-sm text-center transition-colors"
                  >
                    {user ? "Go to dashboard" : "Start free"}
                  </Link>
                )}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-text-muted/70 text-center mt-10 max-w-lg mx-auto leading-relaxed">
        Quotas count backtests, validation runs, and portfolios, and reset at the
        start of each calendar month (UTC). Cancelling keeps Pro until the end of
        the period you have already paid for.
      </p>
    </main>
  );
}
