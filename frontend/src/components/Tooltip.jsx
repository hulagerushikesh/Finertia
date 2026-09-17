import React from "react";
import { HelpCircle } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

/**
 * A margin note on demand.
 *
 * The explanations behind these buttons — what a Sharpe ratio is worth, why
 * win rate is not a headline number — are the product's teaching value, so
 * they cannot live in a native `title` (never appears on touch, cannot be
 * reached by keyboard). A Radix popover opens on click and tap, is tabbable,
 * closes on Escape, and stays inside the viewport without measuring anything.
 *
 * Kept as `Tooltip` so no call site changes.
 */
export default function Tooltip({ label, children, align = "start", className }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "tap-safe inline-flex items-center justify-center text-faint hover:text-pencil data-[state=open]:text-pencil transition-colors rounded-full align-middle",
            className,
          )}
          aria-label="Explain this"
        >
          {children ?? <HelpCircle className="size-3.5" aria-hidden="true" />}
        </button>
      </PopoverTrigger>
      <PopoverContent
        align={align}
        sideOffset={6}
        className="w-auto max-w-[min(20rem,80vw)] p-0 border-0 bg-transparent shadow-none"
      >
        <p className="bg-popover text-popover-foreground shadow-pop rounded-md border-l-2 border-l-pencil px-3 py-2.5 text-sm leading-relaxed">
          {label}
        </p>
      </PopoverContent>
    </Popover>
  );
}
