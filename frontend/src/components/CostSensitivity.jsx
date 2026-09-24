import React from "react";
import { Badge } from "@/components/ui/badge";
import Tooltip from "./Tooltip";
import { cn } from "@/lib/utils";

/** Costs are quoted per unit of turnover. Basis points are how anyone
 *  actually says them, and a tenth of a bp is below the precision of any
 *  spread a person could quote — so one decimal, and only where it reads. */
function bps(cost) {
  if (cost === null || cost === undefined) return "—";
  const v = cost * 1e4;
  // A trailing ".0" reads as spurious precision on figures the user typed
  // themselves — "0 bps" and "5 bps", never "0.0 bps".
  const text = v >= 10 ? v.toFixed(0) : v.toFixed(1).replace(/\.0$/, "");
  return `${text} bps`;
}

const sharpe = (v) => (v === null || v === undefined ? "—" : v.toFixed(2));

/**
 * How wrong the cost assumption can be before the edge is gone.
 *
 * This strip exists because of a measurement that cancelled a different
 * feature. The plan was a volatility-scaled cost model — real spreads widen
 * with volatility, so a flat charge should flatter a strategy exactly when it
 * hurts. Measured against a matched total cost, the *shape* of the cost model
 * moves Sharpe by at most 0.015; the *level* moves it 0.16 to 0.32 per extra
 * 10 bps. About thirty to one. So the level is what gets reported, and the
 * shape stayed flat. `backend/costs.py` carries the full measurement.
 *
 * The headline is the breakeven: the charge at which annualised return, and
 * therefore the Sharpe on the card above, reaches exactly zero. Next to the
 * number the user typed, it answers the only cost question that changes a
 * decision — not "is 10 bps right" but "does it matter if it isn't".
 *
 * One thing it deliberately does not do: call a headroom "safe". There is no
 * measured threshold that separates comfortable from tight, and inventing one
 * would be the same unmeasured assertion the backend module was written to
 * avoid. Colour marks one fact only — that the strategy is already underwater
 * at the cost the user assumed — which the numbers state rather than imply.
 */
export default function CostSensitivity({ data }) {
  if (!data) return null;

  const { status, assumed_cost: assumed, breakeven_cost: breakeven, headroom, curve } = data;

  if (status === "no_trades") {
    return (
      <p className="text-2xs text-faint leading-relaxed">
        No cost tolerance on this run — the strategy never trades, so transaction costs never apply.
      </p>
    );
  }

  const underwater = status === "unprofitable" || (headroom !== null && headroom < 1);

  const tip =
    `The breakeven is the cost per unit of turnover at which this strategy's annualised return ` +
    `reaches exactly zero — and so, on this page's definition of Sharpe, where the Sharpe above ` +
    `reaches zero too. It is solved directly on the equity curve rather than read off the table ` +
    `beside it. Each point in that table is a real re-run of the engine at that cost, so it is ` +
    `what you would see by typing the number into the box yourself. ` +
    `Why the level rather than a cleverer cost model: holding the total cost paid fixed and ` +
    `moving the charge onto high-volatility bars changes Sharpe by at most 0.015, while the level ` +
    `moves it 0.16 to 0.32 per extra 10 bps. The number you assume matters about thirty times ` +
    `more than the shape of the model it goes into.`;

  return (
    <div className="sheet px-4 py-3 sm:px-5 flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        <span className="eyebrow">Cost tolerance</span>
        <Tooltip label={tip} align="start" />
      </div>

      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 font-mono text-sm tabular-nums">
        <span className="text-graphite">
          assumed <span className="font-medium text-foreground">{bps(assumed)}</span>
        </span>
        <span className="text-graphite">
          breakeven{" "}
          <span className={cn("font-medium", underwater ? "text-loss" : "text-foreground")}>
            {status === "unprofitable" ? "—" : bps(breakeven)}
          </span>
        </span>
        {headroom !== null && headroom !== undefined && (
          <Badge variant={underwater ? "loss" : "outline"} size="sm" className="font-mono">
            {headroom.toFixed(1)}× headroom
          </Badge>
        )}
      </div>

      {/* Cost in graphite, Sharpe in foreground, with no separator glyph
          between them — a faint "·" measures 4.39:1 on the dark sheet, and a
          delimiter is not worth shipping below the contrast bar when the
          weight difference already separates the pair. */}
      {curve?.length > 0 && (
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 font-mono text-2xs tabular-nums">
          {curve.map((point) => {
            // The user's own assumption is one of these points; marking it is
            // what makes the rest read as "and if I am wrong".
            const mine = point.cost === assumed;
            return (
              <span key={point.cost} className="text-graphite">
                {bps(point.cost)}{" "}
                <span className={cn("font-medium", mine ? "text-foreground" : "text-graphite")}>
                  {sharpe(point.sharpe_ratio)}
                </span>
              </span>
            );
          })}
        </div>
      )}

      <p className="text-2xs text-graphite leading-relaxed max-w-prose">
        {status === "unprofitable"
          ? "This loses money before a single basis point of cost is charged, so there is no cost headroom to report. Costs are not what went wrong here."
          : underwater
            ? `The edge runs out at ${bps(breakeven)}, below the ${bps(assumed)} you assumed — on these settings the strategy is already past breakeven.`
            : `Costs would have to reach ${bps(breakeven)} — ${headroom?.toFixed(1)}× what you assumed — before the return reaches zero.`}
      </p>
    </div>
  );
}
