import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import { getPlans, startCheckout } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Rise, Stagger, StaggerItem } from "../components/motion";
import { cn } from "@/lib/utils";
import { SUPPORT_EMAIL } from "../lib/contact";
import { usePageTitle } from "../hooks/usePageTitle";

export default function PricingPage() {
  usePageTitle("pricing");
  const { user } = useAuth();
  const { showToast } = useToast();
  const [plans, setPlans] = useState([]);
  const [billingEnabled, setBillingEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [redirecting, setRedirecting] = useState(false);

  const loadPlans = useCallback(() => {
    setLoading(true);
    setError("");
    getPlans()
      .then((d) => {
        setPlans(d.plans);
        setBillingEnabled(d.billing_enabled);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadPlans();
  }, [loadPlans]);

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
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <Rise className="max-w-xl mb-12">
        <p className="eyebrow mb-4">Pricing</p>
        <h1 className="font-display text-display-md font-semibold tracking-tight text-foreground text-balance">
          Start free. Pay when you want the checks.
        </h1>
        <p className="text-graphite leading-relaxed mt-4">
          Both plans run the same engine on the same data. Pro adds the tests that tell you whether
          a result is worth anything — and raises the monthly run quota.
        </p>
      </Rise>

      {/* A pricing page that shows an error and nothing else has failed twice:
          once at fetching, and again at being a pricing page. */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription className="flex flex-col gap-3">
            <span>{error}</span>
            <span className="flex flex-wrap items-center gap-3">
              <Button variant="outline" size="sm" onClick={loadPlans} disabled={loading}>
                {loading ? "Retrying…" : "Try again"}
              </Button>
              <span className="text-xs text-graphite">
                Plans and prices are served by the API, so they are not shown here rather than shown
                wrong.
              </span>
            </span>
          </AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="grid sm:grid-cols-2 gap-5">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-96 rounded-lg" />
          ))}
        </div>
      ) : (
        <Stagger className="grid sm:grid-cols-2 gap-5 items-start">
          {plans.map((plan) => {
            const isPro = plan.id === "pro";
            // Pro with no billing behind it is not for sale yet. Say so,
            // rather than a Pro button that makes a free account.
            const soon = isPro && !billingEnabled;
            return (
              <StaggerItem
                key={plan.id}
                className={cn("relative rounded-lg p-7 flex flex-col", isPro ? "sheet-lifted" : "sheet")}
              >
                {isPro && (
                  <Badge size="sm" variant={soon ? "faint" : undefined} className="absolute top-5 right-5">
                    {soon ? "Coming soon" : "Recommended"}
                  </Badge>
                )}

                <p className="eyebrow mb-5">{plan.label}</p>

                <p className="flex items-baseline gap-1.5">
                  <span className="font-display text-display-md font-semibold text-foreground tracking-tight">
                    ${plan.price_monthly}
                  </span>
                  <span className="text-sm text-faint">/ month</span>
                </p>
                <p className="text-xs font-mono text-graphite mt-2 mb-7">
                  {!isPro
                    ? "No card required"
                    : billingEnabled
                      ? "Cancel any time"
                      : "Not on sale yet"}
                </p>

                <ul className="flex flex-col gap-3 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-graphite leading-relaxed">
                      <Check
                        className={cn("size-4 mt-0.5 shrink-0", isPro ? "text-pencil" : "text-faint")}
                        aria-hidden="true"
                      />
                      {f}
                    </li>
                  ))}
                </ul>

                {soon ? (
                  <div className="flex flex-col gap-3">
                    {!user && (
                      <Button asChild variant="outline">
                        <Link to="/register">Start free</Link>
                      </Button>
                    )}
                    <p className="text-xs text-graphite leading-relaxed">
                      Pro isn&rsquo;t on sale yet. Testing Finertia and need validation? Ask for
                      access at{" "}
                      <a href={`mailto:${SUPPORT_EMAIL}`} className="text-pencil underline underline-offset-2">
                        {SUPPORT_EMAIL}
                      </a>
                      .
                    </p>
                  </div>
                ) : isPro ? (
                  !user ? (
                    <Button asChild>
                      <Link to="/register">Create an account</Link>
                    </Button>
                  ) : (
                    <Button onClick={handleUpgrade} disabled={redirecting}>
                      {redirecting ? "Redirecting…" : "Upgrade to Pro"}
                    </Button>
                  )
                ) : (
                  <Button asChild variant="outline">
                    <Link to={user ? "/dashboard" : "/register"}>
                      {user ? "Go to the workspace" : "Start free"}
                    </Link>
                  </Button>
                )}
              </StaggerItem>
            );
          })}
        </Stagger>
      )}

      <p className="text-xs text-faint mt-10 max-w-xl leading-relaxed">
        Quotas count backtests, validation runs, and portfolios, and reset at the start of each
        calendar month (UTC).
        {billingEnabled && " Cancelling keeps Pro until the end of the period you have already paid for."}
      </p>
    </div>
  );
}
