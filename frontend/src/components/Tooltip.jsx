import React, { useState, useId, useRef, useEffect, useLayoutEffect } from "react";

/**
 * Replaces the native `title` attribute.
 *
 * `title` was carrying the explanations that are the actual point of this
 * product — what a Sharpe ratio is worth, why win rate is not a headline
 * number. It is a bad place for them:
 *
 *   - it never appears on a touch device, so every phone user lost all of it
 *   - it waits about a second before showing, so nobody discovers it
 *   - it cannot be reached by keyboard
 *   - it cannot be styled, so it renders as an OS box that ignores the app
 *
 * This is a button, so it is tabbable, it opens on focus as well as hover, it
 * toggles on tap, and Escape closes it.
 */
export default function Tooltip({ label, children, align = "center" }) {
  const [open, setOpen] = useState(false);
  // Horizontal nudge that keeps the bubble inside the viewport.
  const [shift, setShift] = useState(0);
  const id = useId();
  const wrapRef = useRef(null);
  const tipRef = useRef(null);

  /*
   * Pull the bubble back on screen if it hangs off an edge.
   *
   * Pure CSS cannot do this: the tip is anchored to a trigger sitting at an
   * arbitrary x, so on a narrow screen a 17rem bubble on a card near the right
   * edge runs past the viewport and the last words become unreachable —
   * measured at 23px over on a 375px phone. One measure-and-nudge after open
   * fixes every position without hard-coding any of them.
   *
   * Runs once per open (deps are [open]), so setting the shift cannot re-fire
   * it into a loop.
   */
  useLayoutEffect(() => {
    if (!open) {
      setShift(0);
      return;
    }
    const el = tipRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const margin = 8;
    const vw = document.documentElement.clientWidth;
    let dx = 0;
    if (r.right > vw - margin) dx = vw - margin - r.right;
    if (r.left + dx < margin) dx = margin - r.left;
    if (dx) setShift(dx);
  }, [open]);

  // Tap-outside closes it. On touch there is no pointerleave to rely on, so
  // without this an opened tip stays up until something else is tapped twice.
  useEffect(() => {
    if (!open) return undefined;
    function onDown(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const alignClass =
    align === "start"
      ? "left-0"
      : align === "end"
        ? "right-0"
        : "left-1/2 -translate-x-1/2";

  return (
    <span className="relative inline-flex" ref={wrapRef}>
      <button
        type="button"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onPointerEnter={(e) => e.pointerType === "mouse" && setOpen(true)}
        onPointerLeave={(e) => e.pointerType === "mouse" && setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="tap-safe inline-flex items-center justify-center text-text-faint hover:text-accent transition-colors rounded-full"
      >
        {children ?? (
          <span
            aria-hidden="true"
            className="w-3.5 h-3.5 rounded-full border border-current text-2xs font-mono leading-none flex items-center justify-center"
          >
            ?
          </span>
        )}
        <span className="sr-only">Explain this</span>
      </button>

      {open && (
        <span
          ref={tipRef}
          role="tooltip"
          id={id}
          // marginLeft rather than a transform: centre alignment already uses
          // -translate-x-1/2, and an inline transform would replace it.
          style={{ marginLeft: shift || undefined }}
          // w-max with a max-width lets a short tip stay short instead of
          // padding itself out to a fixed box.
          className={`absolute bottom-full mb-2 z-50 w-max max-w-[min(17rem,70vw)] ${alignClass}
                      bg-raised border border-border-strong rounded-lg shadow-pop
                      px-3 py-2 text-xs leading-relaxed text-text-primary font-normal normal-case tracking-normal text-left`}
        >
          {label}
        </span>
      )}
    </span>
  );
}
