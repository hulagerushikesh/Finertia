import React, { useState, useRef, useEffect } from "react";
import Tooltip from "./Tooltip";

// A curated list rather than a symbol-search API: it needs no key, no network
// call, and no rate limit, and these cover the overwhelming majority of what
// anyone types into a backtester. The field stays free-text, so any ticker
// yfinance accepts still works — this is a shortcut, not a whitelist.
const COMMON_TICKERS = [
  { symbol: "AAPL", name: "Apple" },
  { symbol: "MSFT", name: "Microsoft" },
  { symbol: "GOOGL", name: "Alphabet" },
  { symbol: "AMZN", name: "Amazon" },
  { symbol: "NVDA", name: "NVIDIA" },
  { symbol: "META", name: "Meta Platforms" },
  { symbol: "TSLA", name: "Tesla" },
  { symbol: "JPM", name: "JPMorgan Chase" },
  { symbol: "V", name: "Visa" },
  { symbol: "WMT", name: "Walmart" },
  { symbol: "XOM", name: "Exxon Mobil" },
  { symbol: "JNJ", name: "Johnson & Johnson" },
  { symbol: "KO", name: "Coca-Cola" },
  { symbol: "DIS", name: "Walt Disney" },
  { symbol: "NFLX", name: "Netflix" },
  { symbol: "AMD", name: "AMD" },
  { symbol: "INTC", name: "Intel" },
  { symbol: "BA", name: "Boeing" },
  { symbol: "SPY", name: "S&P 500 ETF" },
  { symbol: "QQQ", name: "Nasdaq 100 ETF" },
  { symbol: "IWM", name: "Russell 2000 ETF" },
  { symbol: "DIA", name: "Dow Jones ETF" },
  { symbol: "GLD", name: "Gold ETF" },
  { symbol: "TLT", name: "20+ Year Treasury ETF" },
  { symbol: "BTC-USD", name: "Bitcoin" },
  { symbol: "ETH-USD", name: "Ethereum" },
  { symbol: "^GSPC", name: "S&P 500 Index" },
  { symbol: "^IXIC", name: "Nasdaq Composite" },
];

/**
 * Rank matches so the most likely intent is highlighted first.
 *
 * A plain substring test is not enough: "ETF" is literally inside "N-ETF-LIX",
 * so Netflix would outrank every actual ETF and Enter would pick the wrong one.
 * Symbol matches beat name matches, and a match at a word start beats one
 * buried mid-word.
 */
function score(t, q) {
  const name = t.name.toUpperCase();
  if (t.symbol === q) return 0;
  if (t.symbol.startsWith(q)) return 1;
  if (t.symbol.includes(q)) return 2;
  // \b would not fire before "&" or a digit, so word starts are checked directly.
  if (name.split(/[\s&-]+/).some((w) => w.startsWith(q))) return 3;
  if (name.includes(q)) return 4;
  return Infinity;
}

function matchTickers(query) {
  const q = query.trim().toUpperCase();
  if (!q) return COMMON_TICKERS.slice(0, 8);
  return COMMON_TICKERS.map((t) => ({ t, s: score(t, q) }))
    .filter((x) => x.s !== Infinity)
    .sort((a, b) => a.s - b.s)
    .slice(0, 8)
    .map((x) => x.t);
}

/**
 * Free-text ticker input with suggestions. Keyboard-navigable, no <form>.
 *
 * `onCommit` is optional: single-ticker mode just writes the chosen symbol back
 * through onChange, while the portfolio chip list needs picking a suggestion to
 * mean "add this holding" rather than "replace the field".
 */
function TickerInput({ value, onChange, onCommit, placeholder = "e.g. AAPL" }) {
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(0);
  const wrapRef = useRef(null);
  const matches = matchTickers(value);

  // Clicking outside should dismiss the list — without this it stays open and
  // covers the fields below it.
  useEffect(() => {
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function pick(symbol) {
    if (onCommit) onCommit(symbol);
    else onChange(symbol);
    setOpen(false);
  }

  function handleKeyDown(e) {
    // With no list open, Enter still has to commit whatever was typed —
    // otherwise a ticker not in the curated list could never be added.
    if (onCommit && e.key === "Enter" && (!open || matches.length === 0)) {
      e.preventDefault();
      onCommit(value);
      return;
    }
    if (!open || matches.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => (c + 1) % matches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => (c - 1 + matches.length) % matches.length);
    } else if (e.key === "Enter") {
      // No <form> here, so Enter has no default submit to suppress — it just
      // accepts the highlighted suggestion.
      e.preventDefault();
      pick(matches[cursor].symbol);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="relative" ref={wrapRef}>
      <input
        className={inputClass}
        value={value}
        onChange={(e) => {
          onChange(e.target.value.toUpperCase());
          setOpen(true);
          setCursor(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
      />
      {open && matches.length > 0 && (
        <ul className="absolute z-20 left-0 right-0 mt-1 bg-raised border border-border-strong rounded-lg shadow-pop overflow-hidden max-h-60 overflow-y-auto">
          {matches.map((t, i) => (
            <li key={t.symbol}>
              <button
                onMouseEnter={() => setCursor(i)}
                onClick={() => pick(t.symbol)}
                className={`w-full text-left px-3 py-2 flex items-baseline justify-between gap-2 transition-colors ${
                  i === cursor ? "bg-accent/15" : ""
                }`}
              >
                <span className="font-mono text-xs text-text-primary">{t.symbol}</span>
                <span className="text-xs text-text-muted truncate">{t.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const DEFAULTS = {
  ticker: "AAPL",
  start: "2020-01-01",
  end: "2024-01-01",
  strategy: "momentum",
  transaction_cost: 0.001,
  // Momentum
  momentum_lookback: 20,
  ma_window: 50,
  momentum_threshold: 0.02,
  // MACD
  macd_fast: 12,
  macd_slow: 26,
  macd_signal: 9,
  // Bollinger
  bb_window: 20,
  bb_std: 2.0,
  // Risk overlays — null means the limit is off, which is the default so the
  // baseline result is the strategy itself rather than the strategy plus a
  // stop nobody chose.
  stop_loss: null,
  take_profit: null,
  sizing: "fixed",
  target_vol: 0.15,
  vol_window: 20,
  max_leverage: 2.0,
  // Portfolio mode. `mode` is client-only — it selects which endpoint to call
  // and is never sent, since the two requests have different shapes.
  mode: "single",
  tickers: ["AAPL", "MSFT"],
  weighting: "equal",
  weight_window: 60,
  max_weight: 1.0,
};

// Server cap in PortfolioRequest. Beyond this the legs table stops being
// readable and each one costs a data fetch plus a full backtest.
const MAX_TICKERS = 10;

const STRATEGIES = [
  {
    id: "momentum",
    label: "Momentum",
    blurb: "Rides trends — buys strength above the moving average.",
  },
  {
    id: "macd",
    label: "MACD",
    blurb: "Trend following on the gap between two exponential averages.",
  },
  {
    id: "bollinger",
    label: "Bollinger",
    blurb: "Mean reversion — fades moves outside the volatility envelope.",
  },
];

/** Which numeric inputs belong to which strategy. */
const FIELDS = {
  momentum: [
    { key: "momentum_lookback", label: "Lookback", range: "5–200", min: 5, max: 200, step: 1,
      tip: "How many days of rate-of-change the signal is measured over. Shorter reacts faster and trades more." },
    { key: "ma_window", label: "MA Window", range: "5–300", min: 5, max: 300, step: 1,
      tip: "The trend filter. A position only opens while price is above this moving average." },
    { key: "momentum_threshold", label: "Threshold", range: "0–1", min: 0, max: 1, step: 0.005,
      tip: "Minimum momentum before a trade triggers. 0.02 means the 2% move must be cleared." },
  ],
  macd: [
    { key: "macd_fast", label: "Fast EMA", range: "2–100", min: 2, max: 100, step: 1,
      tip: "The shorter exponential average. Must be below the slow one or the signal inverts." },
    { key: "macd_slow", label: "Slow EMA", range: "3–200", min: 3, max: 200, step: 1,
      tip: "The longer exponential average. The gap between the two is the MACD line." },
    { key: "macd_signal", label: "Signal EMA", range: "2–100", min: 2, max: 100, step: 1,
      tip: "Smoothing applied to the MACD line itself. Crossings of it are what trade." },
  ],
  bollinger: [
    { key: "bb_window", label: "Window", range: "5–200", min: 5, max: 200, step: 1,
      tip: "Bars used for the moving average at the centre of the envelope." },
    { key: "bb_std", label: "Std Dev", range: "0.5–4", min: 0.5, max: 4, step: 0.25,
      tip: "How wide the bands sit. Higher means fewer, more extreme trades." },
  ],
};

function Field({ label, hint, tip, range, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-center gap-1.5">
        <label className="eyebrow">{label}</label>
        {tip && <Tooltip label={tip} align="start" />}
        {range && (
          <span className="ml-auto text-2xs font-mono text-text-faint whitespace-nowrap">
            {range}
          </span>
        )}
      </span>
      <div className="mt-auto">{children}</div>
      {hint && <p className="text-xs text-text-faint leading-relaxed">{hint}</p>}
    </div>
  );
}

const inputClass = "field-input font-mono";

/** Segmented control. Every either/or choice in this panel is one of these. */
function Segmented({ value, onChange, options, columns }) {
  return (
    <div
      className={`grid gap-1 bg-bg border border-border rounded-lg p-1 ${
        columns === 3 ? "grid-cols-3" : "grid-cols-2"
      }`}
    >
      {options.map((o) => (
        <button
          key={o.id}
          onClick={() => onChange(o.id)}
          aria-pressed={value === o.id}
          className={`text-xs font-medium py-1.5 rounded-md transition-colors ${
            value === o.id
              ? "bg-accent-strong text-white shadow-panel"
              : "text-text-muted hover:text-text-primary hover:bg-raised"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Collapsible group.
 *
 * The panel used to be fifteen fields in one flat column, which made the risk
 * overlays — off by default and irrelevant to a first run — look exactly as
 * required as the ticker. Grouping them and closing them by default puts the
 * decisions in the order they are actually made.
 *
 * `badge` is what makes closing them safe: a collapsed section still says how
 * many of its settings are no longer at their default, so nothing can be
 * silently affecting a result from inside a box you cannot see.
 */
function Section({ title, badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-border pt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center gap-2 py-1 -my-1 text-left group"
      >
        <span className="text-xs font-semibold text-text-primary uppercase tracking-wider flex-1">
          {title}
        </span>
        {badge > 0 && (
          <span className="text-2xs font-mono text-accent-soft bg-accent/12 border border-accent/30 rounded-full px-1.5 leading-[1.15rem]">
            {badge}
          </span>
        )}
        <span
          aria-hidden="true"
          className={`text-text-faint group-hover:text-text-primary transition-transform duration-200 text-2xs ${
            open ? "rotate-90" : ""
          }`}
        >
          &#9654;
        </span>
      </button>
      {open && <div className="flex flex-col gap-4 mt-4">{children}</div>}
    </div>
  );
}

/** Chip list of tickers, added through the same autocomplete as single mode. */
function TickerListInput({ tickers, onChange }) {
  const [draft, setDraft] = useState("");
  const full = tickers.length >= MAX_TICKERS;

  function add(symbol) {
    const clean = symbol.trim().toUpperCase();
    if (!clean) return;
    // Holding a name twice is a bigger position, not a second holding — the
    // server rejects it, so the UI should never let it be built.
    if (tickers.includes(clean)) {
      setDraft("");
      return;
    }
    if (full) return;
    onChange([...tickers, clean]);
    setDraft("");
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-1.5">
        {tickers.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-1.5 bg-bg border border-border rounded-lg pl-2.5 pr-1.5 py-1 text-xs font-mono text-text-primary"
          >
            {t}
            <button
              onClick={() => onChange(tickers.filter((x) => x !== t))}
              // Two is the minimum the server accepts; removing below that
              // would build a request that can only fail.
              disabled={tickers.length <= 2}
              aria-label={`Remove ${t}`}
              className="text-text-muted hover:text-danger disabled:opacity-30 disabled:hover:text-text-muted leading-none"
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {full ? (
        <p className="text-xs text-text-faint">
          Maximum of {MAX_TICKERS} holdings reached.
        </p>
      ) : (
        <TickerInput value={draft} onChange={setDraft} onCommit={add} placeholder="Add a ticker" />
      )}
    </div>
  );
}

/** Percent-facing input over a fraction-valued field, with an on/off toggle. */
function LimitField({ label, hint, value, onChange, defaultPct }) {
  const enabled = value !== null && value !== undefined;
  return (
    <div className="flex flex-col gap-1">
      <label className="flex w-fit items-center gap-2 py-1 text-xs font-medium text-text-muted uppercase tracking-wider cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onChange(e.target.checked ? defaultPct / 100 : null)}
          className="w-3.5 h-3.5 accent-accent cursor-pointer"
        />
        {label}
      </label>
      {enabled && (
        <>
          <div className="relative">
            <input
              type="number"
              className={`${inputClass} pr-7`}
              // Users think in percent; the API takes a fraction.
              value={(value * 100).toFixed(2).replace(/\.?0+$/, "")}
              min={0.1}
              max={90}
              step={0.5}
              onChange={(e) => onChange(Number(e.target.value) / 100)}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-muted font-mono">
              %
            </span>
          </div>
          {hint && <p className="text-xs text-text-faint">{hint}</p>}
        </>
      )}
    </div>
  );
}

export default function ConfigPanel({ params, setParams, onRun, loading }) {
  const strategy = params.strategy || "momentum";
  const active = STRATEGIES.find((s) => s.id === strategy) || STRATEGIES[0];
  const macdInverted = strategy === "macd" && params.macd_fast >= params.macd_slow;

  // Mirrors the server-side rule. A target no further than the stop closes on
  // noise before the trade has a chance to work.
  const targetTooTight =
    params.stop_loss != null &&
    params.take_profit != null &&
    params.take_profit <= params.stop_loss;

  const mode = params.mode || "single";

  // A cap below 1/N cannot fill the book, so the weights would sum to less
  // than 1 and understate every return. The server rejects it too.
  const minWeightCap = (1 / Math.max(params.tickers.length, 1)).toFixed(3);
  const capTooSmall =
    mode === "portfolio" &&
    params.weighting === "inverse_vol" &&
    params.max_weight * params.tickers.length < 1;

  const blocked = macdInverted || targetTooTight || capTooSmall;

  // What a collapsed section reports about itself. Counted against DEFAULTS so
  // the badge means "you changed this", not "this field exists".
  const riskBadge =
    (params.stop_loss != null ? 1 : 0) +
    (params.take_profit != null ? 1 : 0) +
    (params.sizing !== DEFAULTS.sizing ? 1 : 0);
  const tuningBadge =
    FIELDS[strategy].filter((f) => params[f.key] !== DEFAULTS[f.key]).length +
    (params.transaction_cost !== DEFAULTS.transaction_cost ? 1 : 0);

  function handleChange(key, value) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  function reset() {
    setParams(DEFAULTS);
  }

  // The first error that blocks the run, in the order the fields appear.
  // Repeating it beside the button matters because the offending field can be
  // inside a section the user has since collapsed.
  const blocker = macdInverted
    ? "Fast EMA must be shorter than the slow EMA."
    : targetTooTight
      ? "Take profit must be further from entry than the stop loss."
      : capTooSmall
        ? `Max weight must be at least ${minWeightCap} for ${params.tickers.length} holdings.`
        : null;

  return (
    // Split into a scrolling body and a pinned footer. Previously the Run
    // button was the last child of the scroll area, so on a laptop opening the
    // risk section pushed the app's primary action out of sight — you had to
    // scroll a sidebar to find the button that does the thing.
    <div className="w-full lg:w-[21rem] lg:flex-shrink-0 panel flex flex-col lg:sticky lg:top-[4.5rem] lg:max-h-[calc(100vh-6rem)] overflow-hidden">
      <div className="flex flex-col gap-5 p-5 lg:overflow-y-auto lg:flex-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-text-primary">Configuration</h2>
          <button
            onClick={reset}
            className="tap-safe text-xs text-text-faint hover:text-accent transition-colors rounded"
          >
            Reset
          </button>
        </div>

        {/* Strategy picker */}
        <div className="flex flex-col gap-2">
          <span className="eyebrow">Strategy</span>
          <Segmented
            columns={3}
            value={strategy}
            onChange={(v) => handleChange("strategy", v)}
            options={STRATEGIES.map((s) => ({ id: s.id, label: s.label }))}
          />
          <p className="text-xs text-text-faint leading-relaxed">{active.blurb}</p>
        </div>

        {/* Single ticker vs portfolio */}
        <div className="flex flex-col gap-2">
          <span className="eyebrow">Universe</span>
          <Segmented
            value={mode}
            onChange={(v) => handleChange("mode", v)}
            options={[
              { id: "single", label: "One ticker" },
              { id: "portfolio", label: "Portfolio" },
            ]}
          />
        </div>

        {mode === "single" ? (
          <Field label="Ticker" tip="Any symbol yfinance accepts — the suggestion list is only a shortcut, not a limit.">
            <TickerInput
              value={params.ticker}
              onChange={(v) => handleChange("ticker", v)}
            />
          </Field>
        ) : (
          <Field
            label={`Holdings (${params.tickers.length})`}
            hint="The same strategy runs on each, then the legs are combined"
          >
            <TickerListInput
              tickers={params.tickers}
              onChange={(v) => handleChange("tickers", v)}
            />
          </Field>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Field label="Start">
            <input
              type="date"
              className={inputClass}
              value={params.start}
              onChange={(e) => handleChange("start", e.target.value)}
            />
          </Field>
          <Field label="End">
            <input
              type="date"
              className={inputClass}
              value={params.end}
              onChange={(e) => handleChange("end", e.target.value)}
            />
          </Field>
        </div>

        {/* Strategy parameters. Open by default — these are what a run is. */}
        <Section title="Tuning" badge={tuningBadge} defaultOpen>
          {/* Two-up: these hold two or three characters, and a full-width box
              for "20" wastes a row each. Matches the Start/End pair above. */}
          <div className="grid grid-cols-2 gap-x-3 gap-y-4">
            {FIELDS[strategy].map((f) => (
              <Field key={f.key} label={f.label} tip={f.tip} range={f.range}>
                <input
                  type="number"
                  className={inputClass}
                  value={params[f.key]}
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  onChange={(e) => handleChange(f.key, Number(e.target.value))}
                />
              </Field>
            ))}
          </div>

          {macdInverted && (
            <p className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-lg px-3 py-2">
              Fast EMA must be shorter than the slow EMA.
            </p>
          )}

          <Field
            label="Transaction cost"
            tip="Charged on turnover each time the position changes. A fraction, not a percent: 0.001 is 0.1% per trade. Set it to zero and a strategy that trades every day will look far better than it is."
          >
            <input
              type="number"
              className={inputClass}
              value={params.transaction_cost}
              step={0.0005}
              min={0}
              onChange={(e) => handleChange("transaction_cost", Number(e.target.value))}
            />
          </Field>
        </Section>

        {mode === "portfolio" && (
          <Section title="Weighting" defaultOpen>
            <Segmented
              value={params.weighting}
              onChange={(v) => handleChange("weighting", v)}
              options={[
                { id: "equal", label: "Equal" },
                { id: "inverse_vol", label: "Inverse vol" },
              ]}
            />
            <p className="text-xs text-text-faint leading-relaxed">
              {params.weighting === "inverse_vol"
                ? "Quieter names get more of the book, so no single volatile holding dominates the portfolio's risk."
                : "1/N in each name, rebalanced every bar back to target."}
            </p>

            {params.weighting === "inverse_vol" && (
              <>
                <Field label="Weight window" hint="Trailing bars used to measure volatility">
                  <input
                    type="number"
                    className={inputClass}
                    value={params.weight_window}
                    min={2}
                    max={250}
                    step={1}
                    onChange={(e) => handleChange("weight_window", Number(e.target.value))}
                  />
                </Field>
                <Field
                  label="Max weight"
                  hint={`Cap per holding — at least ${minWeightCap} for ${params.tickers.length} names`}
                >
                  <input
                    type="number"
                    className={inputClass}
                    value={params.max_weight}
                    min={0.05}
                    max={1}
                    step={0.05}
                    onChange={(e) => handleChange("max_weight", Number(e.target.value))}
                  />
                </Field>
                {capTooSmall && (
                  <p className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-lg px-3 py-2">
                    A cap of {params.max_weight} cannot fill a book of{" "}
                    {params.tickers.length} holdings — it must be at least {minWeightCap}.
                  </p>
                )}
              </>
            )}
          </Section>
        )}

        {/* Risk overlays — independent of the strategy above, and off by
            default, so this stays closed until someone wants it. */}
        <Section title="Risk & sizing" badge={riskBadge}>
          <p className="text-xs text-text-faint leading-relaxed -mt-1">
            Applied on top of whichever strategy is selected. Leave these off to
            see the strategy on its own.
          </p>

          <LimitField
            label="Stop loss"
            hint="Flatten once the trade is down this much from entry"
            value={params.stop_loss}
            onChange={(v) => handleChange("stop_loss", v)}
            defaultPct={5}
          />

          <LimitField
            label="Take profit"
            hint="Flatten once the trade is up this much from entry"
            value={params.take_profit}
            onChange={(v) => handleChange("take_profit", v)}
            defaultPct={15}
          />

          {targetTooTight && (
            <p className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-lg px-3 py-2">
              Take profit must be further from entry than the stop loss.
            </p>
          )}

          <div className="flex flex-col gap-2">
            <span className="eyebrow">Position sizing</span>
            <Segmented
              value={params.sizing}
              onChange={(v) => handleChange("sizing", v)}
              options={[
                { id: "fixed", label: "Fixed" },
                { id: "vol_target", label: "Vol target" },
              ]}
            />
            <p className="text-xs text-text-faint leading-relaxed">
              {params.sizing === "vol_target"
                ? "Scales exposure so realised volatility sits near the target — smaller in turbulent markets, larger in calm ones."
                : "Full exposure whenever a signal is on."}
            </p>
          </div>

          {params.sizing === "vol_target" && (
            <>
              <Field label="Target volatility" hint="Annualised, e.g. 0.15 = 15%">
                <input
                  type="number"
                  className={inputClass}
                  value={params.target_vol}
                  min={0.01}
                  max={2}
                  step={0.01}
                  onChange={(e) => handleChange("target_vol", Number(e.target.value))}
                />
              </Field>
              <Field label="Vol window" hint="Trailing bars used to measure it (2–250)">
                <input
                  type="number"
                  className={inputClass}
                  value={params.vol_window}
                  min={2}
                  max={250}
                  step={1}
                  onChange={(e) => handleChange("vol_window", Number(e.target.value))}
                />
              </Field>
              <Field label="Max leverage" hint="Cap on the size multiplier">
                <input
                  type="number"
                  className={inputClass}
                  value={params.max_leverage}
                  min={0.1}
                  max={5}
                  step={0.1}
                  onChange={(e) => handleChange("max_leverage", Number(e.target.value))}
                />
              </Field>
            </>
          )}
        </Section>
      </div>

      {/* Pinned. Never scrolls out of reach, whatever is open above it. */}
      <div className="flex-shrink-0 border-t border-border bg-surface p-4">
        {blocker && (
          <p className="text-xs text-danger mb-2.5 leading-relaxed">{blocker}</p>
        )}
        <button
          onClick={onRun}
          disabled={loading || blocked}
          className="btn-primary w-full py-2.5 text-sm"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Running…
            </>
          ) : mode === "portfolio" ? (
            "Run portfolio"
          ) : (
            `Run backtest on ${params.ticker || "…"}`
          )}
        </button>
      </div>
    </div>
  );
}

export { DEFAULTS, STRATEGIES };
