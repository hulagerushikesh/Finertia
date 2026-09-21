import React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * The one-paragraph answer that sits above the six validation sections.
 *
 * Each section below ends in its own verdict, and a reader who wants the
 * evidence can have all of it. But the first question is always the same —
 * "is this real?" — and six stamps on six sheets do not answer it. This
 * card counts the checks, names the ones that failed in plain words, and
 * says what the combination usually means. Every chip scrolls to its
 * section, so the card is a table of contents, not a replacement.
 *
 * Verdict strings are the backend's; the words here are the reader's.
 */
const TONE_DOT = {
  gain: "bg-gain",
  warn: "bg-warn",
  loss: "bg-loss",
  faint: "bg-faint",
};

const CHECKS = [
  {
    id: "walk-forward",
    name: "Unseen data",
    read: (d) => d.walk_forward?.verdict,
    words: {
      held_up: ["held up", "gain"],
      weakened: ["weakened", "warn"],
      overfit: ["overfit", "loss"],
      failed: ["lost money", "loss"],
      inconclusive: ["no edge to test", "faint"],
    },
  },
  {
    id: "rolling",
    name: "Every split",
    read: (d) =>
      d.rolling_walk_forward && d.rolling_walk_forward.computable !== false
        ? d.rolling_walk_forward.verdict
        : null,
    words: {
      consistent: ["held on every split", "gain"],
      regime_dependent: ["depends on the year", "warn"],
      failed: ["failed", "loss"],
    },
  },
  {
    id: "deflated",
    name: "Search correction",
    read: (d) => (d.walk_forward?.deflated?.computable ? d.walk_forward.deflated.verdict : null),
    words: {
      significant: ["survives", "gain"],
      marginal: ["borderline", "warn"],
      not_significant: ["could be luck", "loss"],
      noise: ["noise", "loss"],
      inconclusive: ["cannot say", "faint"],
    },
  },
  {
    id: "overfitting",
    name: "Overfit odds",
    read: (d) => (d.walk_forward?.overfitting?.computable ? d.walk_forward.overfitting.verdict : null),
    words: {
      robust: ["robust", "gain"],
      acceptable: ["acceptable", "gain"],
      fragile: ["fragile", "warn"],
      overfit: ["overfit", "loss"],
    },
  },
  {
    id: "snooping",
    name: "Whole grid",
    read: (d) => (d.walk_forward?.snooping?.computable ? d.walk_forward.snooping.verdict : null),
    words: {
      grid_beats_benchmark: ["beats holding", "gain"],
      weak_evidence: ["borderline vs holding", "warn"],
      no_evidence: ["nothing beats holding", "loss"],
    },
  },
  {
    id: "timing",
    name: "Timing vs luck",
    read: (d) => (d.permutation ? (d.permutation.significant ? "yes" : "no") : null),
    words: {
      yes: ["beats random timing", "gain"],
      no: ["no better than random", "loss"],
    },
  },
];

/** Resolve every check that ran into { id, name, word, tone }. */
export function readChecks(data) {
  const out = [];
  for (const c of CHECKS) {
    const v = c.read(data);
    if (v === null || v === undefined) continue;
    const [word, tone] = c.words[v] || ["unclear", "faint"];
    out.push({ id: c.id, name: c.name, word, tone });
  }
  return out;
}

/** The sentence after the count — what this particular combination usually means. */
function interpret(byId, held) {
  const wf = byId["walk-forward"]?.tone;
  const timing = byId.timing?.tone;
  const dsr = byId.deflated?.tone;
  const rolling = byId.rolling?.tone;
  const grid = byId.snooping?.tone;
  const all = Object.values(byId).filter((c) => c.tone !== "faint");

  if (all.length && all.every((c) => c.tone === "gain")) {
    return "Every check agrees. On this window the edge is more than luck — though one window is still one window.";
  }
  if (wf === "loss" && timing === "gain") {
    return "The timing carries signal, but these exact parameters were fitted too tightly to the tuning period. Loosen them before trusting the number.";
  }
  if (wf === "loss" && timing === "loss") {
    return "The returns look like market exposure rather than strategy. There is nothing here to build on yet.";
  }
  if (wf === "gain" && (dsr === "loss" || dsr === "warn")) {
    return "It held up on unseen data, but with this many combinations tried a Sharpe this high could still be a lucky pick.";
  }
  if (wf === "gain" && grid === "loss") {
    return `It held up on unseen data, but not one combination in the grid beats simply holding ${held} once the search is inside the test. Beating doing nothing is the harder bar, and it was not cleared.`;
  }
  if (rolling === "warn") {
    return "The result depends on where the split falls. Treat it as an edge in some years, not a general one.";
  }
  if (wf === "warn") {
    return "Some of the edge survived contact with unseen data. Real, but smaller than the tuned number suggests.";
  }
  return null;
}

export default function VerdictCard({ data, className, onJump }) {
  const checks = readChecks(data);
  const counted = checks.filter((c) => c.tone !== "faint");
  const passed = counted.filter((c) => c.tone === "gain");
  const warned = counted.filter((c) => c.tone === "warn");
  const failed = counted.filter((c) => c.tone === "loss");
  const byId = Object.fromEntries(checks.map((c) => [c.id, c]));

  const wfFailed = byId["walk-forward"]?.tone === "loss";
  const overall =
    counted.length === 0
      ? ["Nothing to judge", "faint"]
      : wfFailed || failed.length * 2 >= counted.length
        ? ["Not proven", "loss"]
        : failed.length || warned.length
          ? ["Mixed", "warn"]
          : ["Holds up", "gain"];

  const headline =
    counted.length === 0
      ? "None of the checks could run on this configuration."
      : `${passed.length} of ${counted.length} checks passed.`;
  const meaning = interpret(byId, Array.isArray(data.tickers) ? "the basket" : "the stock");

  // The sections may be collapsed; the parent opens them and scrolls once
  // they exist. Without a parent, scroll directly.
  const jump = (id) => {
    if (onJump) return onJump(id);
    const el = document.getElementById(`validation-${id}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <section className={cn("sheet p-6", className)} aria-labelledby="verdict-heading">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="max-w-prose">
          <p className="eyebrow mb-2">Is this real?</p>
          <h2 id="verdict-heading" className="font-display text-display-sm font-semibold text-foreground text-balance">
            {headline}
          </h2>
          {meaning && <p className="margin-note mt-3">{meaning}</p>}
        </div>
        <Badge variant={overall[1]} size="lg" className="shrink-0">
          {overall[0]}
        </Badge>
      </div>

      {checks.length > 0 && (
        <ul className="flex flex-wrap gap-2 mt-5" aria-label="Checks">
          {checks.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => jump(c.id)}
                className="tap-safe inline-flex items-center gap-2 rounded-md border border-border bg-muted/40 hover:bg-muted px-2.5 py-1.5 text-xs text-graphite transition-colors"
              >
                <span className={cn("h-1.5 w-1.5 rounded-full", TONE_DOT[c.tone])} aria-hidden="true" />
                <span className="text-foreground">{c.name}</span>
                <span>· {c.word}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
