/**
 * One source of truth for chart colours.
 *
 * Recharts paints SVG through props, so it cannot read Tailwind classes. Every
 * value here is a CSS custom property reference rather than a hex literal:
 * SVG presentation attributes accept `hsl(var(--x))`, so the same chart
 * resolves correctly on the light sheet and the dark one with no JavaScript
 * theme lookup and no re-render on toggle.
 *
 * The pairing matches the rest of the app. Ink is the thing you measured;
 * graphite, dashed, is the reference it has to beat; pencil is whatever
 * checked it — an out-of-sample boundary, a significance line.
 */
export const CHART = {
  strategy: "hsl(var(--foreground))",
  benchmark: "hsl(var(--muted-foreground))",
  pencil: "hsl(var(--pencil))",
  grid: "hsl(var(--border))",
  axisText: "hsl(var(--muted-foreground))",
  loss: "hsl(var(--loss))",
  gain: "hsl(var(--gain))",
  warn: "hsl(var(--warn))",
  textPrimary: "hsl(var(--foreground))",
  surface: "hsl(var(--card))",
  borderStrong: "hsl(var(--border-strong))",
  mono: "IBM Plex Mono, ui-monospace, monospace",
  // Alpha variants for fills.
  lossFill: "hsl(var(--loss) / 0.18)",
  pencilFill: "hsl(var(--pencil) / 0.12)",
  cursor: "hsl(var(--foreground) / 0.04)",
};

/** Shared axis props so the six charts agree on tick weight and size. */
export const AXIS = {
  tick: { fill: CHART.axisText, fontSize: 10, fontFamily: CHART.mono },
  tickLine: false,
  axisLine: { stroke: CHART.grid },
};

/** Thin a daily series to ~300 points; keeps the last one so the line ends
 * where the data does. */
export function thin(data, max = 300) {
  if (!data || data.length <= max) return data || [];
  const step = Math.ceil(data.length / max);
  const kept = data.filter((_, i) => i % step === 0);
  if (kept[kept.length - 1] !== data[data.length - 1]) kept.push(data[data.length - 1]);
  return kept;
}
