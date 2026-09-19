/** @type {import('tailwindcss').Config} */
import animate from "tailwindcss-animate";

/**
 * Ocean Breeze.
 *
 * tweakcn's preset, carried as HSL triples in src/index.css. The roles Finertia
 * adds on top of the shadcn set keep their names so no component changes:
 *
 *   ink      — your strategy, your numbers, body text (`foreground`)
 *   pencil   — the accent as text and strokes: links, out-of-sample figures,
 *              verdicts. Green here, so `gain` is a deeper, distinct green
 *              and the brand colour never masquerades as a profit.
 *   gain /   — strictly semantic; never used for chrome.
 *   loss
 *
 * Every colour is an HSL triple in CSS variables so the same class resolves
 * correctly in the light and dark sheets; nothing here is a literal hex.
 */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Finertia's own names, on top of the shadcn set.
        paper: "hsl(var(--background))",
        sheet: "hsl(var(--card))",
        ink: "hsl(var(--foreground))",
        graphite: "hsl(var(--muted-foreground))",
        faint: "hsl(var(--faint))",
        rule: "hsl(var(--border))",
        "rule-strong": "hsl(var(--border-strong))",
        pencil: {
          DEFAULT: "hsl(var(--pencil))",
          fill: "hsl(var(--pencil-fill))",
          foreground: "hsl(var(--pencil-foreground))",
        },
        gain: "hsl(var(--gain))",
        loss: "hsl(var(--loss))",
        warn: "hsl(var(--warn))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        // One face. DM Sans has an optical-size axis, so it holds at 64px
        // headlines and at 13px table copy; `display` stays as a name so the
        // headline classes keep working.
        display: ["DM Sans", "system-ui", "-apple-system", "sans-serif"],
        sans: ["DM Sans", "system-ui", "-apple-system", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        tick: ["0.625rem", { lineHeight: "0.875rem" }],
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        "display-sm": ["1.875rem", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        "display-md": ["2.75rem", { lineHeight: "1.05", letterSpacing: "-0.025em" }],
        "display-lg": ["3.5rem", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
        "display-xl": ["4.25rem", { lineHeight: "1", letterSpacing: "-0.03em" }],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 1.4s linear infinite",
      },
    },
  },
  plugins: [animate],
};
