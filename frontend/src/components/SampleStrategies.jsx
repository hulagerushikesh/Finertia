import React from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SAMPLES } from "../lib/samples";
import { STRATEGIES } from "./ConfigPanel";
import { encodeParams } from "../utils/permalink";

const label = (id) => STRATEGIES.find((s) => s.id === id)?.label || id;

/**
 * The three example set-ups, for someone who does not know what to try.
 *
 * Choosing one only fills in the config: nothing runs until the user presses
 * Run, so an example never spends a run from the monthly quota by itself.
 * `onPick` loads it in place (the workspace); without it each card is a link
 * to the workspace with the example in the URL (History).
 */
export default function SampleStrategies({ onPick, className = "" }) {
  return (
    <ul className={`grid gap-3 sm:grid-cols-3 w-full ${className}`} aria-label="Example set-ups">
      {SAMPLES.map((s) => (
        <li key={s.id} className="sheet p-4 flex flex-col gap-2 text-left">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="font-mono text-2xs">{label(s.params.strategy)}</Badge>
            <span className="font-mono text-2xs text-graphite">
              {s.params.mode === "portfolio" ? s.params.tickers.join(" · ") : s.params.ticker}
            </span>
          </div>
          <p className="font-display font-semibold text-foreground leading-snug">{s.title}</p>
          <p className="text-xs text-graphite leading-relaxed flex-1">{s.idea}</p>
          {onPick ? (
            <Button variant="outline" size="sm" className="self-start mt-1" onClick={() => onPick(s)}>
              Load this example
            </Button>
          ) : (
            <Button asChild variant="outline" size="sm" className="self-start mt-1">
              <Link to={`/dashboard?${encodeParams(s.params)}`}>Open in the workspace</Link>
            </Button>
          )}
        </li>
      ))}
    </ul>
  );
}
