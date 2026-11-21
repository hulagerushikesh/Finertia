/**
 * The /learn articles: one question a person searches for, answered in full,
 * and tied back to what this engine does about it.
 *
 * Every mechanism described here is the backend's own (validation.py,
 * purge.py, pbo.py, deflated.py, bootstrap.py, signals.py), and every AAPL
 * figure comes from strategyPages.js, whose numbers strategyPages.test.js
 * checks against the write-up. Nothing here should claim more than those do.
 * Titles and descriptions for search live in src/lib/pageMeta.js under
 * `learn-<id>`.
 */
import React from "react";
import { Link } from "react-router-dom";
import { DocSection as Section, Term } from "../../components/Prose";
import { strategyPage } from "../../lib/strategyPages";
import { NIFTY } from "../../lib/niftyFigures";

const LINK = "text-pencil underline underline-offset-2";

const momentum = strategyPage("momentum").writeup;
const macd = strategyPage("macd").writeup;
const bollinger = strategyPage("bollinger").writeup;

function WalkForward() {
  return (
    <>
      <Section id="idea" title="The idea">
        <p>
          A backtest that chooses its parameters on the same data it reports results on is
          grading its own homework. Walk-forward validation splits the history in two: the
          earlier part is used to choose, the later part is used only to score, once.
        </p>
        <p>
          The number from the later part is the only one that is evidence. The earlier one
          tells you how well the search fitted the past, which is a different and much
          less useful question.
        </p>
      </Section>

      <Section id="how" title="How Finertia does it">
        <ol className="list-decimal pl-5 flex flex-col gap-1.5">
          <li>Every combination in the strategy's grid is run on the first 70% of the period.</li>
          <li>The one with the best Sharpe ratio there is picked.</li>
          <li>
            A gap is cut out around the split: 1% of the period, at least 5 and at most 25
            trading days, on each side. A trade open across the split would otherwise earn
            in both halves off the same price move and count twice.
          </li>
          <li>The picked combination, unchanged, is run on the last 30% and scored.</li>
        </ol>
        <p>
          The verdict compares the two Sharpe ratios. Keeping at least 70% of the in-sample
          figure is <em>held up</em>, 40–70% is <em>weakened</em>, below that is{" "}
          <em>overfit</em>, and a test-period Sharpe at or below zero is <em>failed</em>.
        </p>
      </Section>

      <Section id="one-split" title="Why one split is not enough">
        <p>
          A single split is still one draw. On Apple, momentum's best in-sample cell scored{" "}
          {momentum.first.is} and then {momentum.first.oos} on 2022–2023: {momentum.first.verdict}.
          Moving the end date one year put 2024's rally in the test half, and the same
          strategy {momentum.moved.verdict} at {momentum.moved.oos}. Bollinger bands went the
          other way, from {bollinger.first.verdict} to {bollinger.moved.verdict}.
        </p>
        <p>
          So the workspace also runs a rolling walk-forward, which slides the split through
          the period and shows the out-of-sample result at each step. A strategy that only
          passes at one cut point has not passed.
        </p>
      </Section>

      <Section id="what-it-misses" title="What it does not catch">
        <p>
          Walk-forward protects the final number from the search that produced it. It does
          not protect you from your own searching: if you rerun it with ten strategies and
          keep the one that passed, the test half has become part of the search. That is
          what the <Link to="/learn/backtest-overfitting" className={LINK}>overfitting checks</Link>{" "}
          are for.
        </p>
      </Section>
    </>
  );
}

function Overfitting() {
  return (
    <>
      <Section id="what" title="What overfitting looks like">
        <p>
          An overfit backtest has learned the noise in its history instead of a pattern
          that repeats. The tell is a strong result on the data the parameters were chosen
          on and a weak or negative one on data they were not. Momentum on Apple is a clean
          example: a Sharpe of {momentum.first.is} on the years it was tuned on, and{" "}
          {momentum.first.oos} on the years after.
        </p>
        <p>
          The more combinations you try, the better the best one looks by luck alone. Trying
          ten parameter sets and reporting the winner is not one test; it is ten, with the
          nine losers hidden.
        </p>
      </Section>

      <Section id="checks" title="Four checks, and what each asks">
        <Term name="Walk-forward">
          <p>
            Does the chosen combination still work on later data it was never tuned on?{" "}
            <Link to="/learn/walk-forward-validation" className={LINK}>How it works</Link>.
          </p>
        </Term>
        <Term name="Deflated Sharpe ratio">
          <p>
            Is the winner's Sharpe higher than the best of that many tries would reach on pure
            noise? It compares against that expected maximum (Bailey and López de Prado, 2014)
            rather than against zero, and accounts for skew and fat tails.
          </p>
        </Term>
        <Term name="Probability of backtest overfitting">
          <p>
            The period is cut into eight blocks, and all 70 ways of choosing four of them as
            the training half are tried. Each time, the in-sample winner is ranked on the
            other half. The probability is how often it lands in the bottom half there. Around
            0.5 means choosing by backtest was no better than choosing at random.
          </p>
        </Term>
        <Term name="Permutation test">
          <p>
            Does the timing of the trades matter, or would the same amount of time in the
            market have done as well?{" "}
            <Link to="/learn/permutation-test" className={LINK}>How it works</Link>.
          </p>
        </Term>
      </Section>

      <Section id="small-grids" title="A small grid is not a safe grid">
        <p>
          MACD's grid here has only four combinations, which sounds too few to overfit. On
          the later Apple window its in-sample pick still came out with a probability of
          overfitting of 0.77, and a test-period Sharpe of {macd.moved.oos}. Few choices
          limit how much luck a search can find; they do not make what it finds real.
        </p>
      </Section>

      <Section id="habits" title="Habits that help">
        <ul className="list-disc pl-5 flex flex-col gap-1.5">
          <li>Decide the grid before looking at results, and count every run you make.</li>
          <li>Prefer a rule that does reasonably across neighbouring parameters over one sharp peak.</li>
          <li>Test on more than one stock and more than one split before believing a result.</li>
          <li>Treat a confidence interval that contains zero as no evidence, not weak evidence.</li>
        </ul>
      </Section>
    </>
  );
}

function Lookahead() {
  return (
    <>
      <Section id="what" title="What it is">
        <p>
          Lookahead bias is a backtest using information that was not available at the
          moment of the trade. The most common form is one line of code: a signal computed
          from today's close, applied to today's return.
        </p>
        <p>
          You only know today's close once the day is over. Any rule that buys at that close
          because of that close has bought at a price it could not have traded at. The
          backtest gets the move for free, and the equity curve looks better than anything
          you could have done.
        </p>
      </Section>

      <Section id="shift" title="The one-day shift">
        <p>
          The fix is to shift every signal forward one bar. A signal from Monday's close sets
          Tuesday's position, which earns Tuesday's return. Every strategy in Finertia ends
          with that shift, and each one's tests check the position on a given day depends
          only on prices up to the day before.
        </p>
        <pre className="font-mono text-xs bg-card border border-border rounded-md p-3 overflow-x-auto">
{`signal   = close > close.rolling(50).mean()
position = signal.shift(1)        # trade tomorrow on today's signal
returns  = position * close.pct_change()`}
        </pre>
        <p>
          Drop the <code className="font-mono text-xs">.shift(1)</code> and the code still
          runs, the chart still draws and nothing warns you. That is why it is so common.
        </p>
      </Section>

      <Section id="quieter" title="Quieter forms">
        <Term name="Stops checked inside the bar">
          <p>
            A stop-loss assumed to fill at exactly the stop price, when the price gapped
            through it overnight. Finertia checks stops at the close, so a gap costs the
            whole gap.
          </p>
        </Term>
        <Term name="Volatility measured over the whole period">
          <p>
            Sizing a position by a volatility that includes the future. Volatility targeting
            here uses a trailing window ending the day before.
          </p>
        </Term>
        <Term name="Parameters chosen on the full history">
          <p>
            Tuning on all the data and then reporting the same data. This is lookahead at
            the level of the whole study, and{" "}
            <Link to="/learn/walk-forward-validation" className={LINK}>walk-forward validation</Link>{" "}
            exists to prevent it.
          </p>
        </Term>
        <Term name="Survivorship">
          <p>
            Only testing companies that still exist today. Price history is only there for
            the survivors, so this one no backtest on today's tickers can fully remove.
          </p>
        </Term>
      </Section>

      <Section id="check" title="How to check your own">
        <p>
          If a strategy's result changes very little when you add a one-day delay, it was
          probably fine. If it collapses, the edge was the lookahead. A result much better
          here than in another tool, on the same idea, is worth that check first.
        </p>
      </Section>
    </>
  );
}

function Sharpe() {
  return (
    <>
      <Section id="what" title="What it measures">
        <p>
          The Sharpe ratio is return per unit of volatility. Two strategies that both made
          20% are not equally good if one swung twice as much to get there. In Finertia it is
          the annualised return divided by the annualised volatility of daily returns, after
          trading costs and with no risk-free rate subtracted.
        </p>
        <p>
          As a rough guide on daily data, around 0.5 is ordinary, 1 is good and 2 or more over
          several years is rare enough to be suspicious.
        </p>
      </Section>

      <Section id="misleads" title="Where it misleads">
        <Term name="Short periods">
          <p>
            A Sharpe from one year of data is very noisy. That is why every metric here
            carries a confidence interval from a block bootstrap, and why a band that still
            contains zero means there is no evidence of an edge at all.
          </p>
        </Term>
        <Term name="The best of many">
          <p>
            The highest Sharpe in a parameter sweep is biased upward by the sweep. The
            deflated Sharpe ratio asks whether it beats what the best of that many random
            tries would have scored.
          </p>
        </Term>
        <Term name="Fat tails and rare crashes">
          <p>
            Volatility treats a large loss and a large gain the same, and a strategy that
            sells insurance can show a smooth, high Sharpe until the day it does not. Check
            the maximum drawdown alongside it.
          </p>
        </Term>
        <Term name="In-sample numbers">
          <p>
            A Sharpe from the data the parameters were chosen on is a description of the fit.
            Momentum on Apple scored {momentum.first.is} there and {momentum.first.oos} on the
            years after.
          </p>
        </Term>
      </Section>

      <Section id="compare" title="Comparing two Sharpe ratios">
        <p>
          A strategy at 0.9 against buy-and-hold at 0.7 is not necessarily better: on a few
          years of data the difference is often inside the noise. The benchmark test in the
          workspace measures the difference with standard errors that allow for
          autocorrelation, and says when it cannot tell them apart.
        </p>
      </Section>
    </>
  );
}

function Permutation() {
  return (
    <>
      <Section id="question" title="The question it answers">
        <p>
          A strategy that is long most of the time in a rising market will make money. That
          is the market's return, not the strategy's. The permutation test asks whether{" "}
          <em>when</em> the strategy was in the market mattered, or whether being in the
          market that much was the whole result.
        </p>
      </Section>

      <Section id="how" title="How it works">
        <ol className="list-decimal pl-5 flex flex-col gap-1.5">
          <li>Take the strategy's daily positions: long, short or flat.</li>
          <li>
            Cut them into stretches of unchanged position, and shuffle the order of the
            stretches 500 times. Each shuffle keeps exactly as many long, short and flat days,
            and about as many trades; only the timing changes.
          </li>
          <li>Run each shuffled series against the same returns and costs, and compute its Sharpe.</li>
          <li>
            The p-value is the share of shuffles that matched or beat the real Sharpe. Below
            0.05, the timing beat random timing.
          </li>
        </ol>
      </Section>

      <Section id="reading" title="Reading the result">
        <p>
          A low p-value says the entries and exits carried information. A high one says the
          result could have come from the same exposure spread at random. Bollinger bands on
          Apple came out at p 0.164: its entries could not be told apart from shuffled ones.
        </p>
        <p>
          It is not a test of whether the strategy makes money. A rule can beat random timing
          and still lose after costs, or fail to beat simply holding the stock.
        </p>
      </Section>

      <Section id="limits" title="Its limits">
        <p>
          Until November 2026 the test shuffled single days. That broke up the strategy's
          holding periods, so shuffled series traded far more often and paid more in costs than
          the real one, and the test got easier to pass as costs rose. Shuffling whole stretches
          fixed that, and fewer strategies pass now. The test still says nothing about
          overfitting: a combination picked from a grid
          can beat random timing on the data it was picked on.{" "}
          <Link to="/learn/backtest-overfitting" className={LINK}>The overfitting checks</Link>{" "}
          cover that.
        </p>
      </Section>
    </>
  );
}

const TH = "text-left font-mono text-2xs uppercase tracking-wider text-faint font-medium px-4 py-2.5 border-b border-border align-bottom";
const TD = "px-4 py-2.5 align-top text-graphite tabular-nums";

function Table({ head, rows }) {
  return (
    <div className="overflow-x-auto border border-border rounded-lg bg-card">
      <table className="w-full text-sm border-collapse min-w-[26rem]">
        <thead>
          <tr>{head.map((h) => <th key={h} className={TH}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={i ? "border-t border-border" : ""}>
              {r.map((c, j) => <td key={j} className={TD}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NiftyVsHolding() {
  const { funnel: f, beatHoldUnseen: b } = NIFTY;
  return (
    <>
      <Section id="answer" title="The short answer">
        <p>
          Mostly no. Momentum, MACD crossover and Bollinger-band strategies were run on{" "}
          {NIFTY.stocks} of the Nifty 50 stocks for fifteen years ({NIFTY.period}), after a{" "}
          {NIFTY.cost} cost on every trade. Each one was tuned on the first 70% of the years
          and then scored on the rest. On those later years, only {b.total} of {f.tested}{" "}
          strategy-and-stock pairs had a better Sharpe ratio than simply buying the stock and
          holding it.
        </p>
        <p>
          The typical pair scored a Sharpe of {NIFTY.medianOutOfSample} on the later years.
          Holding the typical stock over the same years scored {NIFTY.medianHoldOutOfSample}.
        </p>
      </Section>

      <Section id="setup" title="How the test was run">
        <ul className="list-disc pl-5 flex flex-col gap-1.5">
          <li>
            The stocks are the Nifty 50 <em>as it stood on 1 January 2011</em>, not today’s
            list. Today’s list holds the companies that did well enough to stay in, which makes
            holding them look better than it was. {NIFTY.missing} of the 2011 names have no
            price history any more and are named in the study rather than dropped.
          </li>
          <li>
            Each strategy’s settings were picked on the tuning years, then left unchanged on
            the later years. Only the later years count as evidence; see{" "}
            <Link to="/learn/walk-forward-validation" className={LINK}>walk-forward validation</Link>.
          </li>
          <li>The rules for passing were written down before the first run.</li>
        </ul>
      </Section>

      <Section id="by-strategy" title="Strategy by strategy">
        <p>Pairs whose later-years Sharpe beat holding the same stock, out of {NIFTY.stocks} each:</p>
        <Table
          head={["Strategy", "Beat holding, later years"]}
          rows={[
            ["Momentum", `${b.momentum} of ${NIFTY.stocks}`],
            ["MACD crossover", `${b.macd} of ${NIFTY.stocks}`],
            ["Bollinger bands", `${b.bollinger} of ${NIFTY.stocks}`],
          ]}
        />
        <p>
          No strategy type stood out. Each beat holding on only a handful of the{" "}
          {NIFTY.stocks} stocks.
        </p>
      </Section>

      <Section id="funnel" title="Looking good is not the same as being good">
        <p>The study then asked for more than one good number:</p>
        <Table
          head={["Step", "Pairs left"]}
          rows={[
            ["Tested", f.tested],
            ["Beat holding on the tuning years", f.beatInSample],
            ["Still ahead on the later years", f.aheadOutOfSample],
            ["Passed three checks for luck", f.survives],
          ]}
        />
        <p>
          {f.beatInSample} pairs looked better than holding on the years they were tuned on.
          The typical pair had a Sharpe of {NIFTY.medianInSample} there and{" "}
          {NIFTY.medianOutOfSample} afterwards. Tuning finds settings that fit the past; it
          does not find settings that keep working. The{" "}
          <Link to="/learn/backtest-overfitting" className={LINK}>overfitting checks</Link>{" "}
          exist for exactly this gap.
        </p>
        <p>
          Costs do not change the picture: at half the cost {NIFTY.survivesHalfCost} pairs
          survive, at double the cost {NIFTY.survivesDoubleCost}.
        </p>
      </Section>

      <Section id="survivors" title="The four that survived">
        <Table
          head={["Stock", "Strategy", "Later-years Sharpe", "Holding"]}
          rows={NIFTY.survivors.map((s) => [s.stock, s.strategy, s.oos, s.hold])}
        />
        <p>
          All four are on companies of one business group that fell apart over the decade.
          The strategies beat holding by spending much of a long decline in cash, not by
          timing good moments to buy. On a stock that mostly falls, any rule that is
          sometimes out of the market beats one that is always in.
        </p>
        <p>
          Reliance Communications’ price history also has long stretches with no trading at
          all, so its figures are not something a person could have earned.
        </p>
      </Section>

      <Section id="takeaway" title="What to take from it">
        <p>
          For a large Indian stock over these fifteen years, a simple rule tuned on the past
          was far more likely to trail holding than to beat it. A backtest that says
          otherwise should be checked on years it was not tuned on, and against the
          possibility of luck, before it is trusted.
        </p>
        <p>
          This is three strategies on one market over one period. It does not show that no
          strategy beats holding Indian stocks. It shows how rarely these ones did when
          tested fairly. On today’s Nifty 50 list the same test found {NIFTY.today.survives}{" "}
          survivor out of {NIFTY.today.tested}.
        </p>
        <p>
          The full study, with every table and the reasons behind each rule:{" "}
          <Link to="/writeup/nifty-50" className={LINK}>Of 129 Nifty strategies, four survived honest testing</Link>.
        </p>
      </Section>
    </>
  );
}

function Survivorship() {
  const S = NIFTY.survivorship;
  const f = NIFTY.funnel;
  const t = S.todayFunnel;
  const left = NIFTY.stocks - S.stillInIndex;
  return (
    <>
      <Section id="answer" title="The short answer">
        <p>
          <strong>Survivorship bias</strong> is testing only the things that survived. To backtest
          on Indian large caps from 2011, the easy choice is today’s Nifty 50 list. But today’s
          list is made of the companies that did well enough to be in the index now. The ones
          that shrank, merged away or collapsed since 2011 are already gone, so the test
          never sees them.
        </p>
        <p>
          Finertia’s Nifty study ran the same test on both lists over the same years,{" "}
          {NIFTY.period}, so the size of the bias is a measured number. Holding the typical
          stock on today’s list gave a Sharpe ratio of {S.holdTuningToday} over the tuning
          years. On the list as it really stood in 2011, the same figure was{" "}
          {S.holdTuning2011}.
        </p>
      </Section>

      <Section id="how-many-left" title="How much the list changed">
        <p>
          Of the {NIFTY.stocks} stocks from the 2011 Nifty 50 that still have price history,
          only {S.stillInIndex} are in the index today. The other {left} dropped out.{" "}
          {NIFTY.missing} more of the 2011 names have no price history at all any more:
        </p>
        <ul className="list-disc pl-5 flex flex-col gap-1.5">
          {S.missingNames.map((n) => <li key={n}>{n}</li>)}
        </ul>
        <p>
          Most of those seven were absorbed by other members. Two, Jaiprakash Associates and
          Reliance Capital, collapsed. A test that starts from today’s list skips all of this
          without saying so.
        </p>
      </Section>

      <Section id="measured" title="The bias, measured">
        <p>Same three strategies, same years, same 0.1% cost, two lists:</p>
        <Table
          head={["", "2011 list", "Today’s list"]}
          rows={[
            ["Median Sharpe of holding, tuning years", S.holdTuning2011, S.holdTuningToday],
            [
              "Stocks that lost money for a holder over the tuning years",
              `${S.holdNegative2011} of ${NIFTY.stocks}`,
              `${S.holdNegativeToday} of ${S.stocksToday}`,
            ],
            ["Strategy-and-stock pairs tested", f.tested, t.tested],
            ["Beat holding on the tuning years", f.beatInSample, t.beatInSample],
            ["Still ahead on the later years", f.aheadOutOfSample, t.aheadOutOfSample],
            ["Passed three checks for luck", f.survives, t.survives],
          ]}
        />
        <p>
          Today’s list makes buying and holding look much better than it was for someone who
          bought the index in 2011. Its members are, by construction, the ones that rose.
        </p>
      </Section>

      <Section id="which-way" title="It does not always flatter the strategy">
        <p>
          The usual warning is that survivorship bias makes a strategy look better than it
          is. Here it went the other way. Because holding today’s winners looked so good, the
          bar for a strategy was higher, and fewer cleared it: {t.beatInSample} of {t.tested}{" "}
          on today’s list against {f.beatInSample} of {f.tested} on the 2011 list.
        </p>
        <p>
          It also hid where the 2011 winners came from. All {f.survives} strategies that
          survived on the 2011 list were on stocks of one business group that fell apart
          over the decade. The strategies won by sitting in cash through a long decline. None
          of those stocks is in today’s index, so a test on today’s list cannot find them. Its
          single survivor was {S.todaySurvivor.stock}, with {S.todaySurvivor.strategy.toLowerCase()},
          and at double the cost there were {S.todaySurvivesDoubleCost}.
        </p>
        <p>
          So the bias does not push results in one fixed direction. It changes which stocks
          are in the test, and with them the answer. The only way to know its size is to run
          both lists.
        </p>
      </Section>

      <Section id="avoid" title="How to avoid it in your own backtests">
        <ul className="list-disc pl-5 flex flex-col gap-1.5">
          <li>
            Start from the list as it stood on the first day of the test, not today’s. Index
            providers publish their changes; undo them back to the start date.
          </li>
          <li>
            Name the stocks you cannot get prices for, and say what happened to them, rather
            than quietly dropping them. Collapsed companies are exactly the ones that go
            missing.
          </li>
          <li>
            If you must use today’s list, run it beside the historical one and report both, so
            the bias is a number instead of a footnote.
          </li>
          <li>
            Judge results on years the settings were not tuned on; see{" "}
            <Link to="/learn/walk-forward-validation" className={LINK}>walk-forward validation</Link>.
          </li>
        </ul>
      </Section>

      <Section id="takeaway" title="What to take from it">
        <p>
          A backtest on today’s index answers the question “how did today’s winners do?”,
          which is not the question an investor in 2011 faced. On the Nifty 50, the difference
          moved the typical holding Sharpe from {S.holdTuning2011} to {S.holdTuningToday}.
        </p>
        <p>
          This is one index over one fifteen-year period, and even the 2011 list here is
          missing {NIFTY.missing} names, so it still flatters holding a little. The full
          study, with the rebuilt list and every table:{" "}
          <Link to="/writeup/nifty-50" className={LINK}>Of 129 Nifty strategies, four survived honest testing</Link>.
          The headline results on their own:{" "}
          <Link to="/learn/nifty-50-strategies-vs-buy-and-hold" className={LINK}>do trading strategies beat buy-and-hold on the Nifty 50?</Link>
        </p>
      </Section>
    </>
  );
}

export const ARTICLES = [
  {
    id: "walk-forward-validation",
    eyebrow: "Validation",
    title: "Walk-forward validation, and why one split can lie.",
    lede:
      "Choose on the past, score on what came after, and only believe the second number. How it works, how Finertia runs it, and the case where it still misleads.",
    Body: WalkForward,
  },
  {
    id: "backtest-overfitting",
    eyebrow: "Validation",
    title: "How to tell if a backtest is overfit.",
    lede:
      "Every rule looks good on the years it was tuned on. Four checks that ask whether yours learned a pattern or memorised the noise.",
    Body: Overfitting,
  },
  {
    id: "lookahead-bias",
    eyebrow: "Pitfalls",
    title: "Lookahead bias: the one-day shift that invents returns.",
    lede:
      "The most common backtesting bug is one missing line, and nothing warns you. What it is, the quieter forms, and how to check your own results.",
    Body: Lookahead,
  },
  {
    id: "sharpe-ratio",
    eyebrow: "Metrics",
    title: "The Sharpe ratio: what it measures and when it misleads.",
    lede:
      "Return per unit of risk is the most quoted number in a backtest. What a good one looks like, and four ways it flatters a strategy.",
    Body: Sharpe,
  },
  {
    id: "permutation-test",
    eyebrow: "Validation",
    title: "The permutation test: skill, or just time in the market?",
    lede:
      "Shuffle a strategy's trades and see whether the real timing beats random timing. How it works, how to read it, and what it cannot tell you.",
    Body: Permutation,
  },
  {
    id: "nifty-50-strategies-vs-buy-and-hold",
    eyebrow: "Results",
    title: "Do trading strategies beat buy-and-hold on the Nifty 50?",
    lede:
      "Momentum, MACD and Bollinger bands on 43 Nifty 50 stocks, fifteen years, after costs, scored on years they were never tuned on. How often they beat simply holding the stock.",
    Body: NiftyVsHolding,
  },
  {
    id: "survivorship-bias-nifty-50",
    eyebrow: "Pitfalls",
    title: "Survivorship bias: why backtesting today’s Nifty 50 misleads.",
    lede:
      "Today’s index holds the companies that made it. The same test on the 2011 Nifty 50 and on today’s list, side by side, so the bias is a number rather than a warning.",
    Body: Survivorship,
  },
].map((a) => ({ ...a, path: `/learn/${a.id}` }));

export function article(id) {
  return ARTICLES.find((a) => a.id === id) || null;
}
