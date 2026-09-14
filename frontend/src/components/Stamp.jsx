import React from "react";
import { m, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * The verdict stamp — the one bold element in the interface.
 *
 * Every check the product runs ends in a word: held up, failed, overfit,
 * significant. Those words used to be pills, which is how every dashboard
 * marks a status. A stamp is how a reviewer marks a manuscript, and it lands
 * with a motion the reader feels: scale 1.6 → 1 with a small overshoot, a
 * few degrees off square, 500ms. Under reduced motion it is simply there.
 *
 *   tone: "pencil" (checked / neutral verdict) · "gain" · "loss" · "warn"
 */
const TONES = {
  pencil: "text-pencil border-pencil",
  gain: "text-gain border-gain",
  loss: "text-loss border-loss",
  warn: "text-warn border-warn",
  faint: "text-graphite border-rule-strong",
};

export default function Stamp({ children, tone = "pencil", size = "md", className, delay = 0.15 }) {
  const off = useReducedMotion();
  const rotate = -5;
  return (
    <m.span
      role="status"
      initial={off ? false : { scale: 1.6, opacity: 0, rotate }}
      animate={{ scale: 1, opacity: 0.94, rotate }}
      transition={
        off ? { duration: 0 } : { type: "spring", stiffness: 520, damping: 22, mass: 0.7, delay }
      }
      className={cn(
        "inline-flex items-center justify-center font-mono font-medium uppercase tracking-[0.18em] border-2 rounded-[4px] whitespace-nowrap select-none mix-blend-multiply dark:mix-blend-screen",
        size === "sm" ? "text-tick px-1.5 py-0.5 border-[1.5px]" : "text-xs px-2.5 py-1",
        size === "lg" && "text-sm px-3.5 py-1.5",
        TONES[tone] || TONES.pencil,
        className,
      )}
    >
      {children}
    </m.span>
  );
}
