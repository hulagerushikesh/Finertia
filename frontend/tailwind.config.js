/** @type {import('tailwindcss').Config} */

/**
 * Finertia reads as a measuring instrument, not a dashboard.
 *
 * The colour system encodes the product's actual thesis. Every screen here puts
 * a number you measured next to the thing that tests it — in-sample against
 * out-of-sample, your strategy against buy-and-hold, your signal against a
 * shuffled one. So the palette is deliberately two-toned:
 *
 *   accent (violet)  the value you measured — the one that might be fooling you
 *   check  (mint)    whatever is checking it — the reference, the null, the
 *                    out-of-sample score
 *
 * Used consistently, that pairing teaches the mental model before any copy
 * does. It is the one place this palette spends its boldness; everything else
 * stays quiet.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Cool ink rather than neutral black. A blue cast lets panels sit
        // *above* the page instead of merging with it, which the old
        // #0f1117/#1a1d27 pair was too close to do.
        bg: "#090C13",
        surface: "#111725",
        // Nested panels and hover states. The old palette had no third step, so
        // an input inside a card had to reuse the page colour and read as a
        // hole punched through the card.
        raised: "#192133",
        border: "#232D42",
        "border-strong": "#33405C",

        /*
         * The accent is split because one violet cannot do both jobs.
         *
         * A violet light enough to read as text on the dark ground (4.94:1) is
         * too light to carry white text on top of it — #7C6BF7 with a white
         * label measures 3.96:1, under the 4.5 floor, and the old lighter hover
         * took it down to 2.72. So `accent` is the text/stroke/border colour
         * and `accent-strong` is the fill behind white labels.
         *
         * Hover goes darker rather than lighter, which is the only direction
         * that improves the label's contrast instead of destroying it.
         */
        accent: "#7C6BF7",
        "accent-soft": "#9C8FFA",
        "accent-strong": "#6B58F6",
        "accent-deep": "#5E49F5",
        check: "#2DD4BF",

        success: "#34D399",
        warning: "#F5A524",
        // Softer than #ef4444: pure red vibrates against a dark ground and made
        // every drawdown read as an error rather than a fact.
        danger: "#F87171",

        "text-primary": "#E9EEF9",
        "text-muted": "#94A3BE",
        "text-faint": "#7C89A2",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        // IBM Plex Mono over JetBrains: it is the face of scientific
        // instrumentation, and its figures sit better in dense tables.
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      /*
       * Micro type is where this interface actually lives — eyebrow labels,
       * verdict pills, axis ticks — and it had no scale. The app reached past
       * Tailwind's `xs` with arbitrary bracket values 48 times and rendered
       * eight distinct sizes on a single page, two of them 9px.
       *
       * `2xs` is the floor for anything a user reads as interface text.
       *
       * `tick` is the one step below it and exists for chart internals only:
       * axis labels and heatmap cells sit inside a fixed geometry that cannot
       * grow, and every one of them restates a number shown at full size
       * elsewhere on the page. Chrome does not get to use it — if a label is
       * the only place a fact appears, it is not a tick.
       */
      fontSize: {
        tick: ["0.625rem", { lineHeight: "0.875rem" }],
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        // Display steps, previously one-off bracket values on four pages.
        "display-sm": ["1.75rem", { lineHeight: "1.1" }],
        "display-md": ["2.5rem", { lineHeight: "1.02" }],
        "display-lg": ["2.75rem", { lineHeight: "1" }],
      },
      boxShadow: {
        // Lit from above. A single inset hairline is what separates a panel
        // that looks placed on the page from one that looks cut out of it.
        panel: "inset 0 1px 0 0 rgba(255,255,255,0.045)",
        "panel-lifted":
          "inset 0 1px 0 0 rgba(255,255,255,0.06), 0 12px 32px -12px rgba(0,0,0,0.7)",
        pop: "0 16px 40px -12px rgba(0,0,0,0.75)",
      },
      keyframes: {
        "toast-in": {
          "0%": { opacity: "0", transform: "translateY(8px) scale(0.97)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
        "rise-in": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        // The needle sweep on the landing gauge. Runs once, on load.
        "sweep-in": {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
      },
      animation: {
        "toast-in": "toast-in 180ms ease-out",
        shimmer: "shimmer 1.4s linear infinite",
        "rise-in": "rise-in 420ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "sweep-in": "sweep-in 900ms cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
};
