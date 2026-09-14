/** @type {import('tailwindcss').Config} */
import animate from "tailwindcss-animate";

/**
 * "Blue pencil."
 *
 * The product is peer review for a backtest, so the interface is set like a
 * marked-up manuscript rather than a trading terminal: paper, ink, and an
 * editor's blue pencil on every number that was checked.
 *
 *   ink      — what you wrote: your strategy, your numbers, primary actions
 *   pencil   — what was checked: out-of-sample figures, verdicts, the one
 *              accent this palette spends its boldness on
 *   gain /   — kept strictly semantic. Blue for the accent is what frees red
 *   loss       and green to mean only loss and gain, which the previous
 *              violet/mint scheme could not promise.
 *
 * Every colour is an HSL triple in CSS variables (src/index.css) so the same
 * class resolves correctly in the light and dark sheets; nothing here is a
 * literal hex.
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
        // Newsreader carries the headlines and the big figures — an editorial
        // serif with optical sizes, so it holds at 64px and at 28px.
        display: ["Newsreader", "Georgia", "Times New Roman", "serif"],
        // Plex Sans is the face of technical reports. It sets dense copy
        // without reading as a marketing site.
        sans: ["IBM Plex Sans", "system-ui", "-apple-system", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        tick: ["0.625rem", { lineHeight: "0.875rem" }],
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        "display-sm": ["1.875rem", { lineHeight: "1.05" }],
        "display-md": ["2.75rem", { lineHeight: "1" }],
        "display-lg": ["3.5rem", { lineHeight: "0.98" }],
        "display-xl": ["4.25rem", { lineHeight: "0.96" }],
      },
      boxShadow: {
        // A sheet of paper lifted a millimetre off the desk. One soft shadow,
        // no inset highlight — highlights are a dark-UI device.
        sheet: "0 1px 2px hsl(var(--shadow) / 0.06), 0 0 0 1px hsl(var(--border))",
        lifted:
          "0 1px 2px hsl(var(--shadow) / 0.06), 0 12px 32px -12px hsl(var(--shadow) / 0.22), 0 0 0 1px hsl(var(--border))",
        pop: "0 16px 40px -12px hsl(var(--shadow) / 0.35), 0 0 0 1px hsl(var(--border-strong))",
      },
      backgroundImage: {
        // Graph paper. Sits behind charts so the grid is part of the sheet,
        // not a chart-library default.
        graph:
          "linear-gradient(hsl(var(--border) / 0.7) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.7) 1px, transparent 1px)",
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
