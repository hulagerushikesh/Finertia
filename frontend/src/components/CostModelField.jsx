import React from "react";
import table from "../lib/costModels.json";
import { Input } from "@/components/ui/input";

/**
 * The market cost models (backend/fees.py) as the workspace shows them.
 *
 * `costModels.json` is a copy of fees.describe(), kept equal by a backend
 * test, so the figure shown here is the figure the server will charge.
 */

const bps = (fraction) => (fraction * 10000).toFixed(2);

/** Per-side cost and its parts for a market model at a given slippage. */
export function marketCost(model, slippageBps) {
  const m = table.models[model];
  if (!m) return null;
  const fixed = m.charges.filter((c) => c.id !== "slippage");
  const slip = slippageBps / 10000;
  const buy = fixed.reduce((s, c) => s + c.buy, 0) + slip;
  const sell = fixed.reduce((s, c) => s + c.sell, 0) + slip;
  const parts = fixed
    .map((c) => ({ label: c.label, perSide: (c.buy + c.sell) / 2 }))
    .filter((p) => p.perSide > 0);
  return { label: m.label, buy, sell, perSide: (buy + sell) / 2, parts, asOf: table.as_of };
}

export default function CostModelField({ model, slippageBps, onSlippage, inputClass }) {
  const cost = marketCost(model, slippageBps);
  if (!cost) return null;
  return (
    <div className="flex flex-col gap-2" data-testid="market-cost">
      <label className="flex items-center justify-between gap-3 text-sm text-graphite" htmlFor="slippage-bps">
        Slippage (bps a side)
        <Input
          id="slippage-bps"
          type="number"
          className={`${inputClass || ""} w-24`}
          value={slippageBps}
          step={1}
          min={0}
          max={100}
          onChange={(e) => onSlippage(Number(e.target.value))}
        />
      </label>
      <p className="text-xs text-graphite leading-relaxed">
        <span className="text-foreground font-mono">{bps(cost.perSide)} bps</span> a side on average
        (buys {bps(cost.buy)}, sales {bps(cost.sell)}):{" "}
        {cost.parts.map((p) => `${p.label.toLowerCase()} ${bps(p.perSide)}`).join(", ")}, plus your slippage.
      </p>
      <p className="text-2xs text-faint leading-relaxed">
        {model === "india"
          ? "Equity delivery with a zero-brokerage broker. Depository charges (a flat fee per sale) are left out; an Indian account cannot hold a short position overnight."
          : "A commission-free broker. FINRA's per-share fee is under 0.1 bp on stocks above $20 and is left out."}{" "}
        Today&rsquo;s rates (as of {cost.asOf}), applied to the whole history.
      </p>
    </div>
  );
}
