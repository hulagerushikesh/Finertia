import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getUsage } from "../api";
import { feature } from "../lib/features";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export default function UsageMeter() {
  const [usage, setUsage] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="sheet p-5">
        <p className="text-sm text-graphite">Could not load usage — {error}</p>
      </div>
    );
  }

  if (!usage) return <Skeleton className="h-32 rounded-lg" />;

  const uncapped = usage.limit === null;
  const pctUsed = uncapped ? 0 : Math.min(100, (usage.used / usage.limit) * 100);
  // Amber before the wall, not at it — a bar that only changes colour once
  // the account is already blocked has told the user nothing useful.
  // The free plan's monthly validations, once switched on (see features.js).
  const freeValidations = feature("free-validation") && !usage.validation && usage.validations_limit > 0;
  const tone = uncapped ? "bg-pencil" : pctUsed >= 100 ? "bg-loss" : pctUsed >= 80 ? "bg-warn" : "bg-foreground";

  return (
    <div className="sheet p-5">
      <div className="flex items-baseline justify-between gap-3 flex-wrap mb-4">
        <h2 className="font-display text-lg font-semibold text-foreground">Usage · {usage.plan_label}</h2>
        <span className="text-2xs font-mono text-graphite">{usage.period}</span>
      </div>

      {uncapped ? (
        <p className="text-sm text-graphite">
          <span className="font-mono text-foreground">{usage.used}</span> runs this month — no limit
          on your plan.
        </p>
      ) : (
        <>
          <div className="flex items-baseline justify-between mb-2">
            <span className="font-display text-2xl font-semibold text-foreground">
              {usage.used} <span className="text-graphite text-base">/ {usage.limit} runs</span>
            </span>
            <span className="text-xs font-mono text-graphite">{usage.remaining} left</span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div className={cn("h-full transition-all", tone)} style={{ width: `${pctUsed}%` }} />
          </div>
        </>
      )}

      <div className="flex flex-wrap gap-x-5 gap-y-1 mt-4 text-xs text-graphite">
        <span>
          Validation:{" "}
          {freeValidations ? (
            <span className="text-foreground">
              <span className="font-mono">{usage.validations_remaining}</span> of{" "}
              <span className="font-mono">{usage.validations_limit}</span> free left
            </span>
          ) : (
            <span className={usage.validation ? "text-gain" : "text-faint"}>
              {usage.validation ? "included" : "Pro only"}
            </span>
          )}
        </span>
        <span>
          Portfolios: up to <span className="font-mono text-foreground">{usage.max_portfolio_size}</span> holdings
        </span>
      </div>

      {usage.plan === "free" && (
        <Link to="/pricing" className="inline-block mt-4 text-xs text-pencil hover:underline rounded-sm">
          Compare plans →
        </Link>
      )}
    </div>
  );
}
