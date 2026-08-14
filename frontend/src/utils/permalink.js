/**
 * Encode a backtest config into URL query params and back.
 *
 * The config is small and flat, so plain query params beat an opaque blob: the
 * URL stays readable and hand-editable, and a stale link degrades into "some
 * fields recognised" rather than failing to parse entirely.
 *
 * Only the parameters the selected strategy actually uses are written. Dumping
 * all fourteen would make every link mostly noise and would imply that MACD
 * cares about `bb_std`.
 */

import { DEFAULTS } from "../components/ConfigPanel";

const STRATEGY_KEYS = {
  momentum: ["momentum_lookback", "ma_window", "momentum_threshold"],
  macd: ["macd_fast", "macd_slow", "macd_signal"],
  bollinger: ["bb_window", "bb_std"],
};

const BASE_KEYS = ["ticker", "start", "end", "strategy", "transaction_cost"];

// Portfolio mode. `tickers` is a list, so it travels as a comma-joined string
// rather than repeated keys — shorter, and readable in the address bar.
const PORTFOLIO_KEYS = ["mode", "tickers", "weighting", "weight_window", "max_weight"];

// Risk overlays apply to every strategy, so they always travel with the link.
const RISK_KEYS = [
  "stop_loss",
  "take_profit",
  "sizing",
  "target_vol",
  "vol_window",
  "max_leverage",
];

const NUMERIC = new Set([
  "transaction_cost",
  "stop_loss",
  "take_profit",
  "target_vol",
  "vol_window",
  "max_leverage",
  "weight_window",
  "max_weight",
  ...Object.values(STRATEGY_KEYS).flat(),
]);

// Fields whose null means "off" rather than "unset" — they must survive the
// round trip as null, not silently fall back to the default.
const NULLABLE = new Set(["stop_loss", "take_profit"]);

/** Serialise a config to a query string (no leading "?"). */
export function encodeParams(params) {
  const strategy = params.strategy || "momentum";
  const sizing = params.sizing || "fixed";
  const mode = params.mode || "single";
  const portfolio = mode === "portfolio";

  const keys = [
    ...BASE_KEYS,
    ...(STRATEGY_KEYS[strategy] || []),
    ...RISK_KEYS,
    ...(portfolio ? PORTFOLIO_KEYS : []),
  ];
  const query = new URLSearchParams();

  for (const key of keys) {
    // Volatility knobs are meaningless under fixed sizing — writing them would
    // pad every link with settings that have no effect.
    if (sizing === "fixed" && ["target_vol", "vol_window", "max_leverage"].includes(key)) {
      continue;
    }
    // Likewise the weighting window only applies to inverse-vol.
    if (
      params.weighting !== "inverse_vol" &&
      ["weight_window", "max_weight"].includes(key)
    ) {
      continue;
    }
    // In portfolio mode the single `ticker` is a leftover from the other mode.
    if (portfolio && key === "ticker") continue;

    const value = params[key];
    // A disabled stop is simply omitted; decode restores it as null.
    if (value === undefined || value === null || value === "") continue;

    query.set(key, Array.isArray(value) ? value.join(",") : String(value));
  }
  return query.toString();
}

/**
 * Read a config out of a query string, layered over DEFAULTS.
 *
 * Returns null when there is nothing to read, so the caller can tell "no
 * permalink" apart from "a permalink that happened to match the defaults".
 * Unknown keys and unparseable numbers are dropped rather than thrown on — a
 * truncated link should still open the app.
 */
export function decodeParams(search) {
  const query = new URLSearchParams(search);
  if ([...query.keys()].length === 0) return null;

  const out = { ...DEFAULTS };
  let recognised = 0;

  const strategy = query.get("strategy");
  if (strategy && STRATEGY_KEYS[strategy]) {
    out.strategy = strategy;
    recognised++;
  }

  // An absent stop key means "off", not "use the default" — otherwise sharing a
  // config with stops disabled would hand the recipient a 5% stop.
  for (const key of NULLABLE) out[key] = null;

  const mode = query.get("mode");
  if (mode === "portfolio" || mode === "single") {
    out.mode = mode;
    recognised++;
  }

  const allowed = [
    ...BASE_KEYS,
    ...(STRATEGY_KEYS[out.strategy] || []),
    ...RISK_KEYS,
    ...PORTFOLIO_KEYS,
  ];
  for (const [key, raw] of query.entries()) {
    if (key === "strategy" || key === "mode" || !allowed.includes(key)) continue;

    if (key === "tickers") {
      const list = raw
        .split(",")
        .map((t) => t.trim().toUpperCase())
        .filter(Boolean);
      // Below two the server rejects the request outright, so a mangled link
      // falls back to the default basket rather than loading a broken form.
      if (list.length < 2) continue;
      out.tickers = [...new Set(list)].slice(0, 10);
    } else if (NUMERIC.has(key)) {
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      out[key] = n;
    } else {
      out[key] = key === "ticker" ? raw.toUpperCase() : raw;
    }
    recognised++;
  }

  return recognised > 0 ? out : null;
}

/** Full shareable URL for a config, based on the current origin. */
export function permalinkFor(params) {
  return `${window.location.origin}/dashboard?${encodeParams(params)}`;
}
