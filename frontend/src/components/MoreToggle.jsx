import React from "react";
import { cn } from "@/lib/utils";

/**
 * The one-line "show more" that guards a fold. Text link, not a button
 * block: it should read as a footnote to what is above it, not a call to
 * action.
 */
export default function MoreToggle({ open, onToggle, controls, show, hide, hint, className }) {
  return (
    <div className={cn("flex flex-wrap items-baseline gap-x-3 gap-y-1", className)}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={controls}
        className="tap-safe inline-flex items-center gap-2 text-xs font-medium text-pencil hover:underline underline-offset-4 whitespace-nowrap"
      >
        <span aria-hidden="true" className="font-mono">{open ? "−" : "+"}</span>
        {open ? hide : show}
      </button>
      {hint && <span className="text-2xs text-faint">{hint}</span>}
    </div>
  );
}
