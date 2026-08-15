import React, { useState, useRef, useEffect } from "react";

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
        <ul className="absolute z-20 left-0 right-0 mt-1 bg-surface border border-border rounded-lg shadow-2xl overflow-hidden max-h-60 overflow-y-auto">
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
    { key: "momentum_lookback", label: "Lookback", hint: "Days for rate-of-change (5–200)", min: 5, max: 200, step: 1 },
    { key: "ma_window", label: "MA Window", hint: "Trend filter period (5–300)", min: 5, max: 300, step: 1 },
    { key: "momentum_threshold", label: "Threshold", hint: "Min momentum to trigger (0.02 = 2%)", min: 0, max: 1, step: 0.005 },
  ],
  macd: [
    { key: "macd_fast", label: "Fast EMA", hint: "Shorter average, must be < slow (2–100)", min: 2, max: 100, step: 1 },
    { key: "macd_slow", label: "Slow EMA", hint: "Longer average (3–200)", min: 3, max: 200, step: 1 },
    { key: "macd_signal", label: "Signal EMA", hint: "Smoothing of the MACD line (2–100)", min: 2, max: 100, step: 1 },
  ],
  bollinger: [
    { key: "bb_window", label: "Window", hint: "Bars for the moving average (5–200)", min: 5, max: 200, step: 1 },
    { key: "bb_std", label: "Std Deviations", hint: "Band width — higher trades less (0.5–4)", min: 0.5, max: 4, step: 0.25 },
  ],
};

function Field({ label, hint, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-text-muted/70">{hint}</p>}
    </div>
  );
}

const inputClass =
  "w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono placeholder-text-muted/50 focus:outline-none focus:border-accent transition-colors";

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
        <p className="text-xs text-text-muted/70">
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
      <label className="flex items-center gap-2 text-xs font-medium text-text-muted uppercase tracking-wider">
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
          {hint && <p className="text-xs text-text-muted/70">{hint}</p>}
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

  function handleChange(key, value) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  function reset() {
    setParams(DEFAULTS);
  }

  return (
    // The risk section makes this panel taller than a laptop viewport, so it
    // scrolls within itself rather than pushing the Run button off-screen.
    // Sticky and height-capped only from lg up. On a phone the panel is stacked
    // above the results, so pinning it would park a scrollable box inside a
    // scrolling page — two nested scroll regions competing for the same drag.
    <div className="w-full lg:w-80 lg:flex-shrink-0 bg-surface border border-border rounded-xl p-5 flex flex-col gap-5 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">Configuration</h2>
        <button
          onClick={reset}
          className="text-xs text-text-muted hover:text-accent transition-colors"
        >
          Reset to defaults
        </button>
      </div>

      {/* Strategy picker */}
      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
          Strategy
        </label>
        <div className="grid grid-cols-3 gap-1 bg-bg border border-border rounded-lg p-1">
          {STRATEGIES.map((s) => (
            <button
              key={s.id}
              onClick={() => handleChange("strategy", s.id)}
              className={`text-xs font-medium py-1.5 rounded-md transition-colors ${
                strategy === s.id
                  ? "bg-accent text-white"
                  : "text-text-muted hover:text-text-primary"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-text-muted/70 leading-relaxed">{active.blurb}</p>
      </div>

      {/* Single ticker vs portfolio */}
      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
          Universe
        </label>
        <div className="grid grid-cols-2 gap-1 bg-bg border border-border rounded-lg p-1">
          {[
            { id: "single", label: "One ticker" },
            { id: "portfolio", label: "Portfolio" },
          ].map((m) => (
            <button
              key={m.id}
              onClick={() => handleChange("mode", m.id)}
              className={`text-xs font-medium py-1.5 rounded-md transition-colors ${
                mode === m.id ? "bg-accent text-white" : "text-text-muted hover:text-text-primary"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {mode === "single" ? (
        <Field label="Ticker" hint="Any symbol yfinance accepts — the list is a shortcut">
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
        <Field label="Start Date">
          <input
            type="date"
            className={inputClass}
            value={params.start}
            onChange={(e) => handleChange("start", e.target.value)}
          />
        </Field>
        <Field label="End Date">
          <input
            type="date"
            className={inputClass}
            value={params.end}
            onChange={(e) => handleChange("end", e.target.value)}
          />
        </Field>
      </div>

      {/* Only the selected strategy's parameters */}
      {FIELDS[strategy].map((f) => (
        <Field key={f.key} label={f.label} hint={f.hint}>
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

      {macdInverted && (
        <p className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-lg px-3 py-2">
          Fast EMA must be shorter than the slow EMA.
        </p>
      )}

      <Field label="Transaction Cost" hint="Per-trade cost as fraction (e.g. 0.001 = 0.1%)">
        <input
          type="number"
          className={inputClass}
          value={params.transaction_cost}
          step={0.0005}
          min={0}
          onChange={(e) => handleChange("transaction_cost", Number(e.target.value))}
        />
      </Field>

      {mode === "portfolio" && (
        <div className="flex flex-col gap-4 border-t border-border pt-4">
          <div>
            <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
              Weighting
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-1 bg-bg border border-border rounded-lg p-1">
            {[
              { id: "equal", label: "Equal" },
              { id: "inverse_vol", label: "Inverse vol" },
            ].map((w) => (
              <button
                key={w.id}
                onClick={() => handleChange("weighting", w.id)}
                className={`text-xs font-medium py-1.5 rounded-md transition-colors ${
                  params.weighting === w.id
                    ? "bg-accent text-white"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                {w.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-text-muted/70 leading-relaxed">
            {params.weighting === "inverse_vol"
              ? "Quieter names get more of the book, so no single volatile holding dominates the portfolio's risk."
              : "1/N in each name, rebalanced every bar back to target."}
          </p>

          {params.weighting === "inverse_vol" && (
            <>
              <Field label="Weight Window" hint="Trailing bars used to measure volatility">
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
                label="Max Weight"
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
        </div>
      )}

      {/* Risk overlays — independent of the strategy above */}
      <div className="flex flex-col gap-4 border-t border-border pt-4">
        <div>
          <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
            Risk
          </h3>
          <p className="text-xs text-text-muted/70 mt-1 leading-relaxed">
            Applied to whichever strategy is selected.
          </p>
        </div>

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
          <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
            Position sizing
          </label>
          <div className="grid grid-cols-2 gap-1 bg-bg border border-border rounded-lg p-1">
            {[
              { id: "fixed", label: "Fixed" },
              { id: "vol_target", label: "Vol target" },
            ].map((s) => (
              <button
                key={s.id}
                onClick={() => handleChange("sizing", s.id)}
                className={`text-xs font-medium py-1.5 rounded-md transition-colors ${
                  params.sizing === s.id
                    ? "bg-accent text-white"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-text-muted/70 leading-relaxed">
            {params.sizing === "vol_target"
              ? "Scales exposure so realised volatility sits near the target — smaller in turbulent markets, larger in calm ones."
              : "Full exposure whenever a signal is on."}
          </p>
        </div>

        {params.sizing === "vol_target" && (
          <>
            <Field label="Target Volatility" hint="Annualised, e.g. 0.15 = 15%">
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
            <Field label="Vol Window" hint="Trailing bars used to measure it (2–250)">
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
            <Field label="Max Leverage" hint="Cap on the size multiplier">
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
      </div>

      <button
        onClick={onRun}
        disabled={loading || blocked}
        className="w-full bg-accent hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Running…
          </>
        ) : (
          mode === "portfolio" ? "Run Portfolio" : "Run Backtest"
        )}
      </button>
    </div>
  );
}

export { DEFAULTS, STRATEGIES };
