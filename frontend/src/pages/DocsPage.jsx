import React from "react";
import { Link } from "react-router-dom";

function Section({ id, title, children }) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="text-lg font-semibold text-text-primary mb-3">{title}</h2>
      <div className="flex flex-col gap-3 text-sm text-text-muted leading-relaxed">
        {children}
      </div>
    </section>
  );
}

function Term({ name, children }) {
  return (
    <div className="border-l-2 border-border pl-4 py-1">
      <p className="text-text-primary font-medium text-sm mb-0.5">{name}</p>
      <p className="text-sm text-text-muted leading-relaxed">{children}</p>
    </div>
  );
}

const CONTENTS = [
  ["how-it-works", "How a backtest runs"],
  ["lookahead", "Why results here are lower than elsewhere"],
  ["strategies", "The three strategies"],
  ["risk", "Stops and position sizing"],
  ["portfolios", "Portfolios"],
  ["validation", "Validation — the part that matters"],
  ["metrics", "Reading the metrics"],
  ["limits", "What a backtest cannot tell you"],
];

export default function DocsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-2">How it works</h1>
      <p className="text-sm text-text-muted mb-8">
        Every number in this app is computed by hand-written pandas and numpy —
        no backtesting library, no TA library. This page explains what those
        computations do and, more usefully, where they can mislead you.
      </p>

      <nav className="panel p-5 mb-10">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          Contents
        </p>
        <ol className="flex flex-col gap-1.5">
          {CONTENTS.map(([id, label], i) => (
            <li key={id} className="text-sm">
              <a href={`#${id}`} className="text-text-muted hover:text-accent transition-colors">
                <span className="font-mono text-xs text-text-faint mr-2">
                  {String(i + 1).padStart(2, "0")}
                </span>
                {label}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <div className="flex flex-col gap-10">
        <Section id="how-it-works" title="How a backtest runs">
          <p>
            Daily closing prices are fetched for your ticker and date range. The
            strategy turns those prices into a <em>position</em> for each day:
            +1 long, −1 short, 0 flat. That position is multiplied by the next
            day's return, transaction costs are deducted in proportion to how
            much the position changed, and the results are compounded into an
            equity curve starting at 1.0.
          </p>
          <p>
            Everything else — drawdown, Sharpe, the monthly heatmap — is derived
            from that one series of daily net returns.
          </p>
        </Section>

        <Section id="lookahead" title="Why results here are lower than elsewhere">
          <p>
            A signal computed from Monday's close cannot be traded at Monday's
            close — you only know it once the day is over. Every strategy here
            shifts its signal forward one bar, so a signal derived from Monday
            is acted on at Tuesday's price.
          </p>
          <p>
            Skipping that shift is the single most common way a backtest
            manufactures returns that do not exist. It is also invisible: the
            equity curve simply looks better. If a result here is worse than one
            you got elsewhere from the same idea, this is the first thing to
            check.
          </p>
          <p>
            The same principle governs stop-losses (evaluated at the close, so a
            bar that gaps through your stop costs you the whole gap) and
            volatility sizing (measured on a trailing window ending yesterday).
          </p>
        </Section>

        <Section id="strategies" title="The three strategies">
          <Term name="Momentum">
            Goes long when the rate of change over your lookback exceeds a
            threshold <em>and</em> price is above its moving average; short on
            the mirror condition. The moving average is a trend filter — it
            stops the strategy buying a bounce inside a downtrend.
          </Term>
          <Term name="MACD">
            Long while the MACD line is above its signal line, short while below.
            It holds the crossover <em>state</em> rather than trading only on the
            crossing bar, so the position series stays continuous.
          </Term>
          <Term name="Bollinger">
            The opposite stance: buys when price falls below the lower band and
            sells when it rises above the upper one. It fades extremes instead of
            following them, and is flat most of the time. Running it alongside
            momentum on the same data is the fastest way to see how much the
            answer depends on the question.
          </Term>
        </Section>

        <Section id="risk" title="Stops and position sizing">
          <Term name="Stop-loss / take-profit">
            Flattens a position once it is down (or up) a set percentage from
            entry. Two things worth knowing: the exit happens at the close, so a
            −10% day against a 5% stop costs the full −10%; and once stopped out
            the position stays flat until the signal actually changes, rather
            than re-entering the next bar and paying costs for nothing.
          </Term>
          <Term name="Volatility targeting">
            Scales exposure to <code className="font-mono text-xs">target ÷ trailing volatility</code>,
            capped by max leverage. Smaller in turbulent markets, larger in calm
            ones. It usually lowers return and lowers drawdown more — whether
            that is an improvement depends on what you are optimising.
          </Term>
        </Section>

        <Section id="portfolios" title="Portfolios">
          <p>
            Portfolio mode runs the same strategy on 2–10 tickers and combines
            the legs. Each leg is a complete backtest with its own signals,
            stops, sizing and costs.
          </p>
          <p>
            Only days on which <em>every</em> holding traded are used. That
            matters: if one name listed recently, the whole portfolio is
            measured over its shorter history, and the app tells you how many
            bars that cost. Filling in the missing days instead would invent
            flat returns and quietly understate the portfolio's risk.
          </p>
          <p>
            The <strong>diversification ratio</strong> is the weighted average
            volatility of the legs divided by the volatility of the portfolio.
            1.0 means your holdings move as one and you gained nothing by
            splitting between them.
          </p>
        </Section>

        <Section id="validation" title="Validation — the part that matters">
          <p>
            Any strategy can be tuned until its backtest looks good. Two checks
            here are designed to find out whether that has happened.
          </p>
          <Term name="Walk-forward">
            Parameters are optimised on the first 70% of the period, then scored
            — untouched — on the remaining 30%. Only that second number is
            evidence. A strategy that posts a strong in-sample Sharpe and a
            negative out-of-sample one has been fitted to noise.
          </Term>
          <Term name="Permutation test">
            Your position series is reshuffled hundreds of times, holding total
            market exposure identical, so only the <em>timing</em> changes. If
            your real result sits comfortably inside the distribution of shuffled
            ones, the edge came from being in the market, not from choosing when.
          </Term>
        </Section>

        <Section id="metrics" title="Reading the metrics">
          <Term name="Sharpe ratio">
            Return per unit of volatility, annualised. Useful for comparing two
            strategies on the same data; close to meaningless in isolation, and
            badly distorted by short periods.
          </Term>
          <Term name="Max drawdown">
            The worst peak-to-trough fall in the equity curve. Usually the number
            that decides whether a strategy is actually holdable — most people
            abandon a system during its drawdown, which converts a paper loss
            into a real one.
          </Term>
          <Term name="Calmar ratio">
            Annualised return divided by max drawdown. A return-per-unit-of-pain
            measure that punishes the deep-hole strategies Sharpe can flatter.
          </Term>
          <Term name="Profit factor">
            Gross profit divided by gross loss. Above 1 means the winners
            outweigh the losers; below 1 means they do not, whatever the win rate
            says.
          </Term>
          <Term name="Win rate">
            The share of non-flat days that were positive. Deliberately not the
            headline number — a strategy can win 70% of days and still lose
            money if the losses are bigger.
          </Term>
        </Section>

        <Section id="limits" title="What a backtest cannot tell you">
          <p>
            <strong className="text-text-primary">Survivorship bias.</strong>{" "}
            Price history only exists for companies that still trade. Every
            ticker you can type here is one that survived; the ones that went to
            zero are absent from the data and from your results.
          </p>
          <p>
            <strong className="text-text-primary">Idealised execution.</strong>{" "}
            Every trade fills at the closing price at a flat cost. Real slippage
            widens exactly when you least want it to — in fast markets, and when
            you are trading size.
          </p>
          <p>
            <strong className="text-text-primary">One sample.</strong> A single
            backtest is one draw from a distribution of possible histories. It is
            not a forecast, and this app is not financial advice.
          </p>
          <p className="pt-2">
            <Link to="/demo" className="text-accent hover:underline">
              See a worked example →
            </Link>
          </p>
        </Section>
      </div>
    </div>
  );
}
