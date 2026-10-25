import React from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { DocSection as Section, Term, DocHeader } from "../components/Prose";
import { DEFAULTS } from "../components/ConfigPanel";
import { Rise } from "../components/motion";
import { useAuth } from "../hooks/useAuth";
import { usePageTitle } from "../hooks/usePageTitle";
import { STRATEGY_PAGES, strategyPage } from "../lib/strategyPages";
import { encodeParams } from "../utils/permalink";
import { authPath } from "../utils/returnTo";
import { PAIRS, STOCKS } from "../lib/stockMeta";
import NotFoundPage from "./NotFoundPage";

const LINK = "text-pencil underline underline-offset-2";
const TH = "text-left font-mono text-2xs uppercase tracking-wider text-faint font-medium px-4 py-2.5 border-b border-border align-bottom";
const TD = "px-4 py-2.5 align-top text-graphite";

/**
 * A public page per strategy, plus /strategies listing them.
 *
 * For search: each page is the rule written out exactly, so someone looking up
 * "MACD crossover backtest" finds what this engine actually trades and what
 * validation said about it, rather than a promise. Pre-rendered at build time
 * like the other public pages (src/lib/pageMeta.js, scripts/prerender.mjs).
 */
export default function StrategyPage() {
  const { id } = useParams();
  if (id === undefined) return <StrategyIndex />;
  const s = strategyPage(id);
  if (!s) return <NotFoundPage />;
  return <Strategy key={s.id} s={s} />;
}

function StrategyIndex() {
  usePageTitle("strategies");
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow="Strategies" title="Three ordinary strategies, tested honestly.">
          These are the rules the engine trades. Each page writes the rule out exactly, lists what
          you can change, and shows how it did on data it was never tuned on, including when it did
          badly.
        </DocHeader>
      </Rise>
      <ul className="flex flex-col gap-6">
        {STRATEGY_PAGES.map((s) => (
          <li key={s.id}>
            <Term name={<Link to={s.path} className="hover:text-pencil transition-colors">{s.label}</Link>}>
              <p className="eyebrow">{s.kind}</p>
              <p>{s.summary}</p>
              <p>
                <Link to={s.path} className={LINK}>The rule and its results</Link>
              </p>
            </Term>
          </li>
        ))}
      </ul>
      <section aria-labelledby="compare-heading" className="mt-12 flex flex-col gap-2">
        <h2 id="compare-heading" className="font-display text-xl font-semibold text-foreground">
          Head to head on {STOCKS.length} stocks
        </h2>
        <ul className="flex flex-col gap-1.5 text-sm">
          {PAIRS.map((p) => (
            <li key={p.slug}><Link to={p.path} className={LINK}>{p.label}</Link></li>
          ))}
        </ul>
      </section>
      <p className="text-sm text-graphite leading-relaxed mt-12 max-w-prose">
        How the engine turns any of them into returns, and where that can mislead, is on{" "}
        <Link to="/docs" className={LINK}>How it works</Link>. The questions behind the checks
        are on <Link to="/learn" className={LINK}>Learn</Link>.
      </p>
    </div>
  );
}

function Strategy({ s }) {
  usePageTitle(`strategy-${s.id}`);
  const { user } = useAuth();
  const others = STRATEGY_PAGES.filter((o) => o.id !== s.id);
  const workspace = `/dashboard?${encodeParams({ ...DEFAULTS, ...s.run })}`;
  const { writeup } = s;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow={`Strategy · ${s.kind}`} title={`${s.label}.`}>
          {s.summary}
        </DocHeader>
      </Rise>

      <div className="flex flex-col gap-14">
        <Section id="rule" title="The rule">
          <ol className="list-decimal pl-5 flex flex-col gap-1.5">
            {s.rule.map((r) => <li key={r}>{r}</li>)}
          </ol>
          <p>{s.why}</p>
          <p>
            Every signal is acted on at the next day's close, never the close it was computed from.
            Skipping that one-day shift is the most common way a backtest invents returns (
            <Link to="/docs#lookahead" className={LINK}>why</Link>).
          </p>
        </Section>

        <Section id="parameters" title="Parameters">
          <Table head={["Parameter", "Default", "What it does"]}>
            {s.params.map(([key, name, def, what]) => (
              <tr key={key} className="border-b border-border last:border-0">
                <td className={`${TD} text-foreground`}>{name}</td>
                <td className={`${TD} font-mono tabular-nums whitespace-nowrap`}>{def}</td>
                <td className={TD}>{what}</td>
              </tr>
            ))}
          </Table>
        </Section>

        <Section id="validation-grid" title="What validation tries">
          <p>
            Walk-forward validation picks the best of these {s.grid.length} combinations on the
            first 70% of the period, then scores only that one on the remaining 30%. The fewer
            combinations, the less room to find one that fit by luck.
          </p>
          <ul className="flex flex-wrap gap-2" aria-label={`${s.label} validation grid`}>
            {s.grid.map((c) => (
              <li key={s.cell(c)} className="font-mono text-2xs text-graphite border border-border rounded px-2 py-1">
                {s.cell(c)}
              </li>
            ))}
          </ul>
        </Section>

        <Section id="results" title="How it did on AAPL">
          <p>
            From the <Link to="/writeup" className={LINK}>write-up</Link>: the same three strategies
            on Apple, 10 bp costs, with the 70/30 split. The best in-sample combination on the first
            window was {writeup.best}. Moving the end date one year moves the split, and the
            verdict can flip.
          </p>
          <Table head={["Test period ends", "In-sample Sharpe", "Out-of-sample Sharpe", "Verdict"]}>
            {[
              ["2023 (2018–2024 run)", writeup.first],
              ["2024 (2018–2025 run)", writeup.moved],
            ].map(([label, r]) => (
              <tr key={label} className="border-b border-border last:border-0">
                <td className={TD}>{label}</td>
                <td className={`${TD} font-mono tabular-nums`}>{r.is}</td>
                <td className={`${TD} font-mono tabular-nums`}>{r.oos}</td>
                <td className={`${TD} text-foreground`}>{r.verdict}</td>
              </tr>
            ))}
          </Table>
          <p className="text-xs text-faint">
            Hypothetical results on past data, re-run by a script in the repository. Not a
            recommendation to trade this or any strategy.
          </p>
        </Section>

        <Section id="misleads" title="Where it misleads">
          <p>{s.misleads}</p>
          <p>
            More on reading a result like this:{" "}
            <Link to="/learn/backtest-overfitting" className={LINK}>how to tell if a backtest is overfit</Link>.
          </p>
        </Section>

        <Section id="try" title="Run it yourself">
          <p>
            The same set-up, AAPL from 2018 to 2024, opens in the workspace with this strategy's
            defaults, straight after sign-up if you are new. Change the ticker or the dates and
            the Validate tab runs the same checks.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              {user ? (
                <Link to={workspace}>Open in the workspace</Link>
              ) : (
                <Link to={authPath("/register", workspace)}>Create a free account</Link>
              )}
            </Button>
            <Button asChild variant="outline">
              <Link to="/demo">See a full result first</Link>
            </Button>
          </div>
          <p className="text-sm">
            The same rule on other stocks: <Link to="/stocks" className={LINK}>{STOCKS.length} US and Indian stocks</Link>.
            The other strategies:{" "}
            {others.map((o, i) => (
              <React.Fragment key={o.id}>
                {i > 0 && " · "}
                <Link to={o.path} className={LINK}>{o.label}</Link>
              </React.Fragment>
            ))}
            . Head to head:{" "}
            {PAIRS.filter((p) => p.a === s.id || p.b === s.id).map((p, i) => (
              <React.Fragment key={p.slug}>
                {i > 0 && " · "}
                <Link to={p.path} className={LINK}>{p.label}</Link>
              </React.Fragment>
            ))}
            .
          </p>
        </Section>
      </div>
    </div>
  );
}

function Table({ head, children }) {
  return (
    <div className="overflow-x-auto border border-border rounded-lg bg-card">
      <table className="w-full text-sm border-collapse min-w-[30rem]">
        <thead>
          <tr>{head.map((h) => <th key={h} className={TH}>{h}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
