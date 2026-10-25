import React from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { DocSection as Section, DocHeader } from "../components/Prose";
import { DEFAULTS } from "../components/ConfigPanel";
import { Rise } from "../components/motion";
import { useAuth } from "../hooks/useAuth";
import { usePageTitle } from "../hooks/usePageTitle";
import results from "../lib/stockResults.json";
import { STOCKS, STOCK_PERIOD, ofThree, percent, signed } from "../lib/stockMeta";
import { STRATEGY_PAGES, strategyPage } from "../lib/strategyPages";
import { encodeParams } from "../utils/permalink";
import { authPath } from "../utils/returnTo";
import NotFoundPage from "./NotFoundPage";

const LINK = "text-pencil underline underline-offset-2";
const TH = "text-left font-mono text-2xs uppercase tracking-wider text-faint font-medium px-4 py-2.5 border-b border-border align-bottom";
const TD = "px-4 py-2.5 align-top text-graphite";
const NUM = `${TD} font-mono tabular-nums whitespace-nowrap`;

// backend/validation.py `_verdict` and backend/rolling.py `_overall_verdict`.
const VERDICT = {
  held_up: "held up",
  weakened: "weakened",
  overfit: "overfit",
  failed: "failed",
  inconclusive: "inconclusive",
};
const ROLLING = {
  consistent: "positive in every window",
  regime_dependent: "depends on the window",
  failed: "negative in every window",
};

/**
 * /stocks and /stocks/:slug: the three strategies on one well-known stock,
 * against holding it and on the years they were never tuned on.
 *
 * Every figure is from stockResults.json, which
 * backend/scripts/build_stock_pages.py writes from the real route handlers
 * and can re-check. The prose around the figures is derived from them, never
 * written per stock, so a re-run cannot leave a page saying the opposite of
 * its own table.
 */
export default function StockPage() {
  const { slug } = useParams();
  if (slug === undefined) return <StocksIndex />;
  const meta = STOCKS.find((s) => s.slug === slug);
  if (!meta) return <NotFoundPage />;
  return <Stock key={slug} meta={meta} r={results.stocks[slug]} />;
}

function StocksIndex() {
  usePageTitle("stocks");
  const { user } = useAuth();
  const workspace = user ? "/dashboard" : authPath("/register", "/dashboard");
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow="Stocks" title="Three strategies on well-known stocks.">
          Momentum, MACD and Bollinger bands on {STOCKS.length} US and Indian stocks and indices,{" "}
          {STOCK_PERIOD.years}. Each page compares them with simply holding the stock, then
          asks whether they held up on years they were never tuned on. Most did not.
        </DocHeader>
      </Rise>
      <div className="flex flex-col gap-10">
        {["US", "India"].map((market) => (
          <section key={market} aria-labelledby={`market-${market}`}>
            <h2 id={`market-${market}`} className="font-display text-xl font-semibold text-foreground mb-3">
              {market}
            </h2>
            <Table head={["Stock", "Holding it returned", "Its Sharpe", "Held up out of sample"]}>
              {STOCKS.filter((s) => s.market === market).map((s) => (
                <tr key={s.slug} className="border-b border-border last:border-0">
                  <td className={TD}>
                    <Link to={s.path} className={LINK}>{s.label}</Link>
                  </td>
                  <td className={NUM}>{percent(s.buy_and_hold_return)}</td>
                  <td className={NUM}>{signed(s.buy_and_hold_sharpe)}</td>
                  <td className={NUM}>{s.held_up} of 3</td>
                </tr>
              ))}
            </Table>
          </section>
        ))}
      </div>
      <p className="text-sm text-graphite leading-relaxed mt-10 max-w-prose">
        These {STOCKS.length} are a sample, not a limit. The{" "}
        <Link to={workspace} className={LINK}>workspace</Link> runs the same tests on any symbol
        Yahoo Finance carries: US tickers as they are (MSFT), NSE stocks with .NS (INFY.NS), BSE
        with .BO, indices with ^ (^NSEI).
      </p>
      <p className="text-xs text-faint mt-6 max-w-prose">
        Hypothetical results on past data, from a script in the repository that re-runs every
        figure. Not a recommendation to buy, sell or trade anything.
      </p>
    </div>
  );
}

function Stock({ meta, r }) {
  usePageTitle(`stock-${meta.slug}`);
  const { user } = useAuth();
  const bh = r.buy_and_hold;
  const rows = STRATEGY_PAGES.map((p) => ({ p, x: r.strategies[p.id] }));
  const beatHold = rows.filter(({ x }) => x.defaults.sharpe_ratio > bh.sharpe_ratio).length;
  const split = rows[0].x.walk_forward.split_date;
  const others = STOCKS.filter((s) => s.market === meta.market && s.slug !== meta.slug);
  const workspace = (id) =>
    `/dashboard?${encodeParams({ ...DEFAULTS, ticker: meta.symbol, start: STOCK_PERIOD.start, end: STOCK_PERIOD.end, strategy: id })}`;

  return (
    <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <nav aria-label="Breadcrumb" className="text-xs text-faint mb-4">
          <Link to="/stocks" className="hover:text-pencil transition-colors">Stocks</Link>
          <span aria-hidden="true"> / </span>
          <span>{meta.market}</span>
        </nav>
        <DocHeader title={`${meta.label}: three strategies, ${STOCK_PERIOD.years}.`}>
          Holding {meta.name} over these years returned {percent(bh.total_return)}, a Sharpe ratio
          of {signed(bh.sharpe_ratio)}. At their default settings {ofThree(beatHold)} rules beat
          that Sharpe. Tuned on the first 70% of the period and scored on the rest,{" "}
          {ofThree(meta.held_up)} held up.
        </DocHeader>
      </Rise>

      <div className="flex flex-col gap-14">
        <Section id="against-holding" title="Against holding it">
          <p>
            Each rule at the workspace's default parameters, with 10 basis points of cost on every
            change of position, over {r.bars.toLocaleString("en-US")} trading days.
          </p>
          <Table head={["", "Total return", "Sharpe", "Worst fall"]}>
            <tr className="border-b border-border">
              <td className={`${TD} text-foreground`}>Buy and hold</td>
              <td className={NUM}>{percent(bh.total_return)}</td>
              <td className={NUM}>{signed(bh.sharpe_ratio)}</td>
              <td className={NUM}>{percent(bh.max_drawdown)}</td>
            </tr>
            {rows.map(({ p, x }) => (
              <tr key={p.id} className="border-b border-border last:border-0">
                <td className={TD}>
                  <Link to={p.path} className={LINK}>{p.label}</Link>
                </td>
                <td className={NUM}>{percent(x.defaults.total_return)}</td>
                <td className={NUM}>{signed(x.defaults.sharpe_ratio)}</td>
                <td className={NUM}>{percent(x.defaults.max_drawdown)}</td>
              </tr>
            ))}
          </Table>
        </Section>

        <Section id="out-of-sample" title="On years it never saw">
          <p>
            For each rule, every combination in its grid was run on the period up to {split}, the
            best was picked, and only that one was scored on what came after.{" "}
            <Link to="/learn/walk-forward-validation" className={LINK}>How walk-forward works</Link>.
          </p>
          <Table head={["", "Picked", "Sharpe, tuned", "Sharpe, after", "Verdict"]}>
            {rows.map(({ p, x }) => (
              <tr key={p.id} className="border-b border-border last:border-0">
                <td className={TD}>{p.label}</td>
                <td className={`${TD} font-mono text-xs whitespace-nowrap`}>{strategyPage(p.id).cell(x.walk_forward.best_params)}</td>
                <td className={NUM}>{signed(x.walk_forward.in_sample_sharpe)}</td>
                <td className={NUM}>{signed(x.walk_forward.out_of_sample_sharpe)}</td>
                <td className={`${TD} text-foreground`}>{VERDICT[x.walk_forward.verdict]}</td>
              </tr>
            ))}
          </Table>
        </Section>

        <Section id="skill-or-luck" title="Skill or luck">
          <p>
            Three more readings of the same runs. A permutation p-value under 0.05 means the
            timing beat random timing; a probability of overfitting near 0.5 or above means picking
            by backtest did no better than picking at random; the rolling column slides the split
            through the period.{" "}
            <Link to="/learn/backtest-overfitting" className={LINK}>What each one asks</Link>.
          </p>
          <Table head={["", "Permutation p", "Probability of overfitting", "Across rolling windows"]}>
            {rows.map(({ p, x }) => (
              <tr key={p.id} className="border-b border-border last:border-0">
                <td className={TD}>{p.label}</td>
                <td className={NUM}>{x.permutation_p.toFixed(3)}</td>
                <td className={NUM}>{x.pbo === null ? "—" : x.pbo.toFixed(2)}</td>
                <td className={TD}>{ROLLING[x.rolling_verdict]}</td>
              </tr>
            ))}
          </Table>
          <p className="text-xs text-faint">
            Hypothetical results on past data ({r.first_date} to {r.last_date}), from a script in the
            repository that re-runs every figure. Not a recommendation to buy, sell or trade{" "}
            {meta.name} or any other security.
          </p>
        </Section>

        <Section id="try" title="Run it yourself">
          <p>
            Each opens in the workspace on {meta.name} over the same dates
            {user ? "" : ", straight after sign-up if you are new"}. Change the ticker or the
            dates and the numbers change with them, which is the point.
          </p>
          <div className="flex flex-wrap gap-3">
            {rows.map(({ p }, i) => {
              const to = user ? workspace(p.id) : authPath("/register", workspace(p.id));
              return (
                <Button key={p.id} asChild variant={i === 0 ? "default" : "outline"}>
                  <Link to={to}>{p.label} on {meta.name}</Link>
                </Button>
              );
            })}
          </div>
          {others.length > 0 && (
            <p className="text-sm">
              Other {meta.market} stocks:{" "}
              {others.map((o, i) => (
                <React.Fragment key={o.slug}>
                  {i > 0 && " · "}
                  <Link to={o.path} className={LINK}>{o.name}</Link>
                </React.Fragment>
              ))}
              . <Link to="/stocks" className={LINK}>All of them</Link>.
            </p>
          )}
        </Section>
      </div>
    </article>
  );
}

function Table({ head, children }) {
  return (
    <div className="overflow-x-auto border border-border rounded-lg bg-card">
      <table className="w-full text-sm border-collapse min-w-[30rem]">
        <thead>
          <tr>{head.map((h, i) => <th key={i} className={TH}>{h}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
