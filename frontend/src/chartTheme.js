/**
 * One source of truth for chart colours.
 *
 * Recharts paints SVG through props, so it cannot read Tailwind classes — every
 * chart was carrying its own copy of the palette as hex literals, which is
 * exactly why all six of them were still drawing the old colours after the
 * tokens moved. Importing from here means the next palette change is one edit.
 *
 * The strategy/benchmark pairing is deliberate and matches the rest of the app:
 * violet is always the thing you measured, mint is always what it is being
 * measured against.
 *
 * These mirror `tailwind.config.js`. Changing a colour means changing both.
 */
export const CHART = {
  strategy: "#7C6BF7",
  benchmark: "#2DD4BF",
  grid: "#232D42",
  axisText: "#94A3BE",
  danger: "#F87171",
  success: "#34D399",
  warning: "#F5A524",
  info: "#38BDF8",
  textPrimary: "#E9EEF9",
  surface: "#192133",
  borderStrong: "#33405C",
  mono: "IBM Plex Mono, ui-monospace, monospace",
};
