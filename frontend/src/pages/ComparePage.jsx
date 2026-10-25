import React from "react";
import { Link } from "react-router-dom";
import { DocSection as Section, DocHeader } from "../components/Prose";
import { Rise } from "../components/motion";
import { usePageTitle } from "../hooks/usePageTitle";
import results from "../lib/stockResults.json";
import { PAIRS, STOCKS, STOCK_PERIOD, STRATEGY_LABEL, STRATEGY_TOTALS, signed } from "../lib/stockMeta";
import { strategyPage } from "../lib/strategyPages";

const LINK = "text-pencil underline underline-offset-2";
const TH = "text-left font-mono text-2xs uppercase tracking-wider text-faint font-medium px-4 py-2.5 border-b border-border align-bottom";
const TD = "px-4 py-2.5 align-top text-graphite";
const NUM = `${TD} font-mono tabular-nums whitespace-nowrap`;
const WIN = "text-foreground font-semibold";

function median(xs) {
  const s = [...xs].sort((x, y) => x - y);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * /strategies/<a>-vs-<b>: two of the three strategies across every stock with
 * a /stocks page. Every figure is from stockResults.json, like StockPage.jsx;
 * the counts the title and description quote are stockIndex.json's, which
 * stockMeta.test.js checks against the same results.
 */
export default function ComparePage({ slug }) {
  const pair = PAIRS.find((p) => p.slug === slug);
  usePageTitle(`compare-${slug}`);
  const { a, b, wins, label } = pair;
  const rows = STOCKS.map((s) => ({ s, r: results.stocks[s.slug] }));
  const sharpe = (r, id) => r.strategies[id].defaults.sharpe_ratio;
  const after = (r, id) => r.strategies[id].walk_forward.out_of_sample_sharpe;
  const n = STOCKS.length;
  const side = (id) => ({
    wins: wins[id],
    beatHold: rows.filter(({ r }) => sharpe(r, id) > r.buy_and_hold.sharpe_ratio).length,
    median: median(rows.map(({ r }) => sharpe(r, id))),
    heldUp: STRATEGY_TOTALS[id].held_up,
    medianAfter: median(rows.map(({ r }) => after(r, id))),
    beatRandom: STRATEGY_TOTALS[id].beat_random,
  });
  const [A, B] = [side(a), side(b)];
  const [la, lb] = [STRATEGY_LABEL[a], STRATEGY_LABEL[b]];
  const others = PAIRS.filter((p) => p.slug !== slug);

  const score = [
    ["Higher Sharpe than the other, default settings", "wins", (x) => `${x} of ${n}`],
    ["Higher Sharpe than holding the stock", "beatHold", (x) => `${x} of ${n}`],
    ["Median Sharpe, default settings", "median", signed],
    ["Held up on years it never saw", "heldUp", (x) => `${x} of ${n}`],
    ["Median Sharpe on those years", "medianAfter", signed],
    ["Beat random timing (p < 0.05)", "beatRandom", (x) => `${x} of ${n}`],
  ];

  return (
    <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <nav aria-label="Breadcrumb" className="text-xs text-faint mb-4">
          <Link to="/strategies" className="hover:text-pencil transition-colors">Strategies</Link>
          <span aria-hidden="true"> / </span>
          <span>Compare</span>
        </nav>
        <DocHeader title={`${label}, on ${n} stocks.`}>
          The same {n} US and Indian stocks and indices, {STOCK_PERIOD.years}. At default settings{" "}
          {la} had the higher Sharpe ratio on {A.wins}, {lb} on {B.wins}. Tuned on the first 70% of
          the period and scored on the rest, {la} held up on {A.heldUp} and {lb} on {B.heldUp}.
        </DocHeader>
      </Rise>

      <div className="flex flex-col gap-14">
        <Section id="scoreboard" title="The scoreboard">
          <Table head={["", la, lb]} narrow>
            {score.map(([name, key, fmt]) => (
              <tr key={key} className="border-b border-border last:border-0">
                <td className={TD}>{name}</td>
                <td className={`${NUM} ${A[key] > B[key] ? WIN : ""}`}>{fmt(A[key])}</td>
                <td className={`${NUM} ${B[key] > A[key] ? WIN : ""}`}>{fmt(B[key])}</td>
              </tr>
            ))}
          </Table>
          <p>
            Beating random timing and holding up are different questions. The{" "}
            <Link to="/learn/permutation-test" className={LINK}>permutation test</Link> asks
            whether a rule's timing beat chance over the whole period; the{" "}
            <Link to="/learn/walk-forward-validation" className={LINK}>walk-forward split</Link> asks
            whether the setting picked on the early years kept working after. A rule can pass the
            first and fail the second.
          </p>
        </Section>

        <Section id="rules" title="The two rules">
          <div className="grid sm:grid-cols-2 gap-6">
            {[a, b].map((id) => {
              const p = strategyPage(id);
              return (
                <div key={id} className="flex flex-col gap-2">
                  <p className="eyebrow">{p.kind}</p>
                  <p>{p.summary}</p>
                  <p className="text-sm">
                    <Link to={p.path} className={LINK}>The exact {STRATEGY_LABEL[id]} rule</Link>
                  </p>
                </div>
              );
            })}
          </div>
        </Section>

        <Section id="by-stock" title="Stock by stock">
          <p>
            Sharpe ratio at default settings over the whole period, then the Sharpe on the years
            after the split of the setting tuned on the years before. The higher of each pair is in
            bold.
          </p>
          <Table head={["Stock", `${la}`, `${lb}`, `${la}, unseen years`, `${lb}, unseen years`]}>
            {rows.map(({ s, r }) => (
              <tr key={s.slug} className="border-b border-border last:border-0">
                <td className={TD}>
                  <Link to={s.path} className={LINK}>{s.name}</Link>
                </td>
                <Pair x={sharpe(r, a)} y={sharpe(r, b)} />
                <Pair x={after(r, a)} y={after(r, b)} />
              </tr>
            ))}
          </Table>
          <p className="text-xs text-faint">
            Hypothetical results on past data, from a script in the repository that re-runs every
            figure. Not a recommendation to buy, sell or trade anything.
          </p>
        </Section>

        <nav aria-label="More to read" className="text-sm flex flex-col gap-1.5">
          <p className="eyebrow mb-1">Other comparisons</p>
          {others.map((o) => (
            <Link key={o.slug} to={o.path} className={LINK}>{o.label}</Link>
          ))}
          <Link to="/stocks" className={LINK}>Every stock, all three strategies</Link>
        </nav>
      </div>
    </article>
  );
}

function Pair({ x, y }) {
  return (
    <>
      <td className={`${NUM} ${x > y ? WIN : ""}`}>{signed(x)}</td>
      <td className={`${NUM} ${y > x ? WIN : ""}`}>{signed(y)}</td>
    </>
  );
}

/** `narrow` drops the minimum width, for a table short enough to wrap on a phone. */
function Table({ head, children, narrow = false }) {
  return (
    <div className="overflow-x-auto border border-border rounded-lg bg-card">
      <table className={`w-full text-sm border-collapse ${narrow ? "" : "min-w-[30rem]"}`}>
        <thead>
          <tr>{head.map((h, i) => <th key={i} className={TH}>{h}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
