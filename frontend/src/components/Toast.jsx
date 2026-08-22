import React from "react";

const VARIANTS = {
  success: {
    ring: "border-success/40 bg-success/10",
    dot: "bg-success",
    icon: "✓",
    iconColor: "text-success",
  },
  error: {
    ring: "border-danger/40 bg-danger/10",
    dot: "bg-danger",
    icon: "!",
    iconColor: "text-danger",
  },
  info: {
    ring: "border-accent/40 bg-accent/10",
    dot: "bg-accent",
    icon: "i",
    iconColor: "text-accent",
  },
};

export default function Toast({ message, type = "info", onDismiss }) {
  const v = VARIANTS[type] || VARIANTS.info;

  return (
    <div
      role="status"
      className={`pointer-events-auto animate-toast-in flex items-start gap-3 min-w-[260px] max-w-sm border ${v.ring} backdrop-blur-sm rounded-lg pl-3 pr-2 py-2.5 shadow-lg shadow-black/30`}
    >
      <span
        className={`shrink-0 mt-0.5 w-4 h-4 rounded-full border ${v.ring} ${v.iconColor} flex items-center justify-center text-2xs font-bold leading-none`}
      >
        {v.icon}
      </span>
      <p className="flex-1 text-xs text-text-primary leading-relaxed">{message}</p>
      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="shrink-0 text-text-muted hover:text-text-primary transition-colors text-sm leading-none px-1 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent rounded"
      >
        ×
      </button>
    </div>
  );
}
