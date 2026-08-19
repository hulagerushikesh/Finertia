import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getUsage } from "../api";

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
      <div className="panel p-5">
        <p className="text-sm text-text-muted">Could not load usage — {error}</p>
      </div>
    );
  }

  if (!usage) {
    return <div className="h-32 panel animate-pulse" />;
  }

  const uncapped = usage.limit === null;
  const pctUsed = uncapped ? 0 : Math.min(100, (usage.used / usage.limit) * 100);
  // Amber before the wall, not at it — a bar that only changes colour once the
  // account is already blocked has told the user nothing useful.
  const tone = uncapped
    ? "bg-accent"
    : pctUsed >= 100
      ? "bg-danger"
      : pctUsed >= 80
        ? "bg-warning"
        : "bg-success";

  return (
    <div className="panel p-5">
      <div className="flex items-baseline justify-between gap-3 flex-wrap mb-4">
        <h2 className="text-sm font-semibold text-text-primary">
          Usage · {usage.plan_label}
        </h2>
        <span className="text-xs font-mono text-text-muted">{usage.period}</span>
      </div>

      {uncapped ? (
        <p className="text-sm text-text-muted">
          <span className="font-mono text-text-primary">{usage.used}</span> runs this
          month — no limit on your plan.
        </p>
      ) : (
        <>
          <div className="flex items-baseline justify-between mb-2">
            <span className="text-sm text-text-primary font-mono">
              {usage.used} / {usage.limit} runs
            </span>
            <span className="text-xs text-text-muted">{usage.remaining} left</span>
          </div>
          <div className="h-2 bg-bg rounded-full overflow-hidden">
            <div
              className={`h-full ${tone} transition-all`}
              style={{ width: `${pctUsed}%` }}
            />
          </div>
        </>
      )}

      <div className="flex flex-wrap gap-x-5 gap-y-1 mt-4 text-xs text-text-muted">
        <span>
          Validation:{" "}
          <span className={usage.validation ? "text-success" : "text-text-faint"}>
            {usage.validation ? "included" : "Pro only"}
          </span>
        </span>
        <span>
          Portfolios: up to{" "}
          <span className="font-mono text-text-primary">{usage.max_portfolio_size}</span>{" "}
          holdings
        </span>
      </div>

      {usage.plan === "free" && (
        <Link
          to="/pricing"
          className="inline-block mt-4 text-xs text-accent hover:underline"
        >
          Compare plans →
        </Link>
      )}
    </div>
  );
}
