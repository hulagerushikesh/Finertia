import React from "react";
import { m, useReducedMotion } from "motion/react";

/**
 * The three motions this interface uses, named once.
 *
 *   Rise    — content arriving: 8px up and in, 220ms. Used for page bodies
 *             and for a result replacing an empty state.
 *   Stagger — a list of rises, 40ms apart, so a grid of cards reads as one
 *             thing settling rather than eleven things popping.
 *
 * Every variant collapses to an instant cut under prefers-reduced-motion —
 * these carry no information that is lost by skipping them.
 */
export const EASE_OUT = [0.16, 1, 0.3, 1];

export function useMotionOff() {
  return useReducedMotion();
}

export function Rise({ children, delay = 0, className, as = "div", ...rest }) {
  const off = useReducedMotion();
  const Tag = m[as] || m.div;
  return (
    <Tag
      initial={off ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay, ease: EASE_OUT }}
      className={className}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export const staggerParent = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04, delayChildren: 0.02 } },
};

export const staggerChild = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.22, ease: EASE_OUT } },
};

export function Stagger({ children, className, ...rest }) {
  const off = useReducedMotion();
  return (
    <m.div
      variants={staggerParent}
      initial={off ? "show" : "hidden"}
      animate="show"
      className={className}
      {...rest}
    >
      {children}
    </m.div>
  );
}

export function StaggerItem({ children, className, as = "div", ...rest }) {
  const Tag = m[as] || m.div;
  return (
    <Tag variants={staggerChild} className={className} {...rest}>
      {children}
    </Tag>
  );
}
