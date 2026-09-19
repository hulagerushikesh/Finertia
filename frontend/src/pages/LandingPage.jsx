import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { m, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  BookOpen,
  Compass,
  LineChart,
  MousePointerClick,
  Play,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import RealityTape from "../components/RealityTape";
import { Rise, Stagger, StaggerItem, EASE_OUT } from "../components/motion";

/**
 * The page is written for someone who has never heard the word "backtest".
 * Every section answers one question a stranger would ask, in order: what
 * is this, how does it work, is it for me, can I see one, why trust it.
 * The method names (walk-forward, deflated Sharpe, permutation) stay in
 * /docs; here they are "checks".
 */
const STEPS = [
  {
    n: "01",
    icon: MousePointerClick,
    title: "Pick",
    desc: "A stock, a simple rule, and a stretch of years.",
    example: "AAPL · momentum · 2019–2024",
  },
  {
    n: "02",
    icon: Play,
    title: "Run",
    desc: "Finertia replays the rule on real prices, with real trading costs, and shows what it would have made.",
    example: "+68% · just holding made +411%",
  },
  {
    n: "03",
    icon: ShieldCheck,
    title: "Check",
    desc: "Then it re-tests the same rule on years it was never tuned on, and tells you if the result was skill or luck.",
    example: "2 of 5 checks passed",
  },
];

const AUDIENCES = [
  {
    icon: Compass,
    title: "New to this?",
    desc: "Start from the example run. Every number has a ? beside it that says what it means and whether it matters.",
    to: "/demo",
    cta: "Open the example",
  },
  {
    icon: LineChart,
    title: "Already trade?",
    desc: "Stop trusting a curve you fitted yourself. See whether your rule holds on data it never saw before you put money on it.",
    to: "/register",
    cta: "Test a rule",
  },
  {
    icon: BookOpen,
    title: "Learning quant?",
    desc: "No black box. The engine is plain pandas and numpy, every check has its formula written out, and 603 tests keep it honest.",
    to: "/docs",
    cta: "Read how it works",
  },
];

/**
 * The split, drawn. In-sample on the left in ink, a purged gap, then the
 * out-of-sample stretch in the accent — the only bars that count.
 */
function SplitDiagram() {
  const off = useReducedMotion();
  return (
    <svg viewBox="0 0 600 64" className="w-full h-16" aria-hidden="true">
      <line x1="0" y1="40" x2="600" y2="40" stroke="hsl(var(--border-strong))" strokeWidth="1" />
      <m.rect
        x="0" y="34" width="400" height="12" fill="hsl(var(--foreground))"
        initial={off ? false : { scaleX: 0 }} animate={{ scaleX: 1 }}
        transition={{ duration: 0.8, ease: EASE_OUT }} style={{ transformOrigin: "0 40px" }}
      />
      <rect x="400" y="34" width="24" height="12" fill="hsl(var(--border))" />
      <m.rect
        x="424" y="34" width="176" height="12" fill="hsl(var(--pencil))"
        initial={off ? false : { scaleX: 0 }} animate={{ scaleX: 1 }}
        transition={{ duration: 0.6, delay: 0.6, ease: EASE_OUT }} style={{ transformOrigin: "424px 40px" }}
      />
      <text x="0" y="20" fontFamily="IBM Plex Mono" fontSize="10" fill="hsl(var(--muted-foreground))" letterSpacing="1.4">
        TUNED HERE · 70%
      </text>
      <text x="412" y="60" fontFamily="IBM Plex Mono" fontSize="9" fill="hsl(var(--muted-foreground))" textAnchor="middle">
        gap
      </text>
      <text x="600" y="20" fontFamily="IBM Plex Mono" fontSize="10" fill="hsl(var(--pencil))" letterSpacing="1.4" textAnchor="end">
        SCORED HERE · 30%
      </text>
    </svg>
  );
}

function SectionHead({ eyebrow, title, lede }) {
  return (
    <div className="max-w-2xl">
      <p className="eyebrow mb-3">{eyebrow}</p>
      <h2 className="font-display text-display-sm font-semibold text-foreground text-balance">{title}</h2>
      {lede && <p className="text-base text-graphite leading-relaxed mt-3">{lede}</p>}
    </div>
  );
}

export default function LandingPage() {
  // A signed-in reader who lands here wants the workspace, not a form.
  const { user } = useAuth();
  const start = user ? "/dashboard" : "/register";

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-20">
      {/* ── 1. What is this ─────────────────────────────────────────── */}
      <Rise className="max-w-3xl">
        <Badge variant="pencil" className="mb-6">Free to start · no card</Badge>
        <h1 className="font-display font-semibold text-display-md sm:text-display-lg lg:text-display-xl tracking-[-0.02em] text-foreground text-balance">
          Test a trading idea before you risk money on it.
        </h1>
        <p className="text-base sm:text-lg text-graphite leading-relaxed mt-7 max-w-2xl">
          Pick a stock, a simple rule and a stretch of years. Finertia shows what would have
          happened — and then checks whether that result was skill or luck.
        </p>
        <div className="flex flex-wrap items-center gap-3 mt-9">
          <Button asChild size="lg">
            <Link to={start}>{user ? "Open your workspace" : "Try it free"}</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/demo">See an example</Link>
          </Button>
        </div>
      </Rise>

      {/* ── 2. How it works ─────────────────────────────────────────── */}
      <section className="mt-24" aria-labelledby="how-heading">
        <SectionHead
          eyebrow="How it works"
          title={<span id="how-heading">Three steps. About a minute.</span>}
        />
        <Stagger className="mt-8 grid sm:grid-cols-3 gap-4">
          {STEPS.map((s) => (
            <StaggerItem key={s.n} className="sheet p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex size-9 items-center justify-center rounded-lg bg-pencil/10 text-pencil">
                  <s.icon className="size-4" aria-hidden="true" />
                </span>
                <span className="font-mono text-xs text-faint">{s.n}</span>
              </div>
              <div>
                <h3 className="font-display text-xl font-semibold text-foreground">{s.title}</h3>
                <p className="text-sm text-graphite leading-relaxed mt-1.5">{s.desc}</p>
              </div>
              <p className="mt-auto font-mono text-2xs text-pencil bg-pencil/5 rounded-md px-2.5 py-1.5 w-fit">
                {s.example}
              </p>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      {/* ── 3. A real run ───────────────────────────────────────────── */}
      <section className="mt-24" aria-labelledby="example-heading">
        <SectionHead
          eyebrow="A real run"
          title={<span id="example-heading">This is what a result looks like.</span>}
          lede="A momentum rule on Apple, year by year, against simply holding the stock. It beat holding in one year out of five — which is exactly the kind of thing you want to know before trading it."
        />
        <Rise delay={0.08} className="mt-8">
          <RealityTape />
        </Rise>
        <p className="mt-4 text-sm">
          <Link to="/demo" className="inline-flex items-center gap-1.5 text-pencil hover:underline underline-offset-4">
            Open the full example, with every chart <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </p>
      </section>

      {/* ── 4. Who it's for ─────────────────────────────────────────── */}
      <section className="mt-24" aria-labelledby="who-heading">
        <SectionHead eyebrow="Who it's for" title={<span id="who-heading">Start where you are.</span>} />
        <Stagger className="mt-8 grid sm:grid-cols-3 gap-4">
          {AUDIENCES.map((a) => (
            <StaggerItem key={a.title} className="sheet p-6 flex flex-col gap-3">
              <a.icon className="size-5 text-pencil" aria-hidden="true" />
              <h3 className="font-display text-lg font-semibold text-foreground">{a.title}</h3>
              <p className="text-sm text-graphite leading-relaxed">{a.desc}</p>
              <Link
                to={a.to === "/register" ? start : a.to}
                className="mt-auto pt-2 inline-flex items-center gap-1.5 text-sm font-medium text-pencil hover:underline underline-offset-4"
              >
                {a.cta} <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      {/* ── 5. Why trust it ─────────────────────────────────────────── */}
      <section className="mt-24" aria-labelledby="trust-heading">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-10 items-center">
          <div>
            <p className="eyebrow mb-3">Why the checks matter</p>
            <h2 id="trust-heading" className="font-display text-display-sm font-semibold text-foreground text-balance">
              Any rule looks good on the years it was tuned on.
            </h2>
            <p className="text-sm text-graphite leading-relaxed mt-4 max-w-md">
              So Finertia tunes on the first 70% of the period and scores on the last 30%,
              untouched. Every figure from that stretch is{" "}
              <span className="pencil-mark">in green, like this</span>, so you always know
              which numbers were actually checked.
            </p>
            <p className="mt-4 text-sm">
              <Link to="/docs" className="inline-flex items-center gap-1.5 text-pencil hover:underline underline-offset-4">
                Every check, with its formula <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </p>
          </div>
          <div className="sheet px-6 py-6">
            <SplitDiagram />
          </div>
        </div>
        <ul className="mt-10 grid sm:grid-cols-3 gap-px bg-border border-y border-border">
          {[
            ["Real prices", "Daily closes from Yahoo Finance, with a trading cost on every position change."],
            ["Open maths", "No backtesting library. Plain pandas and numpy you can read, with 603 tests on the engine."],
            ["Honest numbers", "Every metric carries a confidence interval, and results that beat holding are the exception, not the sales pitch."],
          ].map(([t, d]) => (
            <li key={t} className="bg-background py-5 sm:px-6 first:sm:pl-0 last:sm:pr-0">
              <p className="text-sm font-semibold text-foreground">{t}</p>
              <p className="text-sm text-graphite leading-relaxed mt-1">{d}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── 6. Go ───────────────────────────────────────────────────── */}
      <section className="mt-24 sheet px-6 py-10 sm:px-10 text-center" aria-labelledby="go-heading">
        <h2 id="go-heading" className="font-display text-display-sm font-semibold text-foreground text-balance">
          Try one idea today.
        </h2>
        <p className="text-base text-graphite mt-3 max-w-xl mx-auto">
          Free plan runs the full engine on any stock. No card, nothing to install.
        </p>
        <div className="flex flex-wrap justify-center items-center gap-3 mt-7">
          <Button asChild size="lg">
            <Link to={start}>{user ? "Open your workspace" : "Create a free account"}</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/pricing">See plans</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
