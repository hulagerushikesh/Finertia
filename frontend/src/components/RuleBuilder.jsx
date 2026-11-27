import React from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Build your own rule: entry and exit conditions, no code.
 *
 * Edits the rule as the JSON the API takes (backend/rules.py), so what is on
 * screen is exactly what runs. The server validates it again and names any
 * fault; the inputs here only keep values inside the server's bounds.
 */

// Mirrors backend/rules.py INDICATORS: the parameters each takes and their defaults.
export const INDICATORS = {
  close: { label: "Price", params: {} },
  sma: { label: "SMA", params: { n: 20 } },
  ema: { label: "EMA", params: { n: 20 } },
  rsi: { label: "RSI", params: { n: 14 } },
  momentum: { label: "Momentum", params: { n: 20 } },
  highest: { label: "Highest close", params: { n: 20 } },
  lowest: { label: "Lowest close", params: { n: 20 } },
  macd: { label: "MACD line", params: { fast: 12, slow: 26 } },
  macd_signal: { label: "MACD signal", params: { fast: 12, slow: 26, signal: 9 } },
  bb_upper: { label: "Bollinger upper", params: { n: 20, k: 2 } },
  bb_lower: { label: "Bollinger lower", params: { n: 20, k: 2 } },
  bb_middle: { label: "Bollinger middle", params: { n: 20 } },
};

const PARAM_LABEL = { n: "days", fast: "fast", slow: "slow", signal: "signal", k: "width" };

export const OPS = [
  { id: "<", label: "is below" },
  { id: ">", label: "is above" },
  { id: "<=", label: "is at or below" },
  { id: ">=", label: "is at or above" },
  { id: "crosses_above", label: "crosses above" },
  { id: "crosses_below", label: "crosses below" },
];

const MAX_CONDITIONS = 8;

/** A moving-average crossover: a sensible place to start editing from. */
export const DEFAULT_RULE = {
  direction: "long",
  entry: { all: [{ left: { ind: "sma", n: 20 }, op: "crosses_above", right: { ind: "sma", n: 50 } }] },
  exit: { all: [{ left: { ind: "sma", n: 20 }, op: "crosses_below", right: { ind: "sma", n: 50 } }] },
};

const selectClass =
  "h-8 rounded-md border border-input bg-transparent px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring";
const numberClass =
  "h-8 w-14 rounded-md border border-input bg-transparent px-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-ring";

function operandFor(kind) {
  if (kind === "value") return { value: 50 };
  return { ind: kind, ...INDICATORS[kind].params };
}

function Operand({ value, onChange, label, allowValue }) {
  const kind = "value" in value ? "value" : value.ind;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <select
        aria-label={`${label}: indicator`}
        className={selectClass}
        value={kind}
        onChange={(e) => onChange(operandFor(e.target.value))}
      >
        {Object.entries(INDICATORS).map(([id, m]) => (
          <option key={id} value={id}>{m.label}</option>
        ))}
        {allowValue && <option value="value">Number</option>}
      </select>
      {kind === "value" ? (
        <input
          type="number"
          aria-label={`${label}: number`}
          className={cn(numberClass, "w-20")}
          value={value.value}
          step="any"
          onChange={(e) => onChange({ value: Number(e.target.value) })}
        />
      ) : (
        Object.keys(INDICATORS[kind].params).map((p) => (
          <label key={p} className="flex items-center gap-1 text-2xs text-faint">
            <input
              type="number"
              aria-label={`${label}: ${PARAM_LABEL[p]}`}
              className={numberClass}
              value={value[p]}
              min={p === "k" ? 0.1 : 2}
              max={p === "k" ? 5 : 400}
              step={p === "k" ? 0.25 : 1}
              onChange={(e) => onChange({ ...value, [p]: Number(e.target.value) })}
            />
            {PARAM_LABEL[p]}
          </label>
        ))
      )}
    </div>
  );
}

function Block({ name, block, onChange }) {
  const mode = "all" in block ? "all" : "any";
  const conds = block[mode];
  const set = (next) => onChange({ [mode]: next });

  return (
    <fieldset className="flex flex-col gap-2 border-l-2 border-pencil/40 pl-3">
      <legend className="eyebrow mb-1">{name}</legend>
      <label className="flex items-center gap-2 text-xs text-graphite">
        When
        <select
          aria-label={`${name}: combine conditions`}
          className={selectClass}
          value={mode}
          onChange={(e) => onChange({ [e.target.value]: conds })}
        >
          <option value="all">all of these hold</option>
          <option value="any">any of these holds</option>
        </select>
      </label>
      {conds.map((c, i) => {
        const label = `${name} condition ${i + 1}`;
        const update = (patch) => set(conds.map((x, j) => (j === i ? { ...x, ...patch } : x)));
        return (
          <div key={i} className="flex flex-col gap-1.5 rounded-md bg-muted/50 p-2" data-testid="rule-condition">
            <div className="flex items-start justify-between gap-2">
              <Operand label={`${label} left`} value={c.left} onChange={(left) => update({ left })} />
              {conds.length > 1 && (
                <button
                  type="button"
                  aria-label={`Remove ${label}`}
                  onClick={() => set(conds.filter((_, j) => j !== i))}
                  className="text-faint hover:text-loss rounded-sm"
                >
                  <X className="size-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
            <select
              aria-label={`${label}: comparison`}
              className={cn(selectClass, "self-start")}
              value={c.op}
              onChange={(e) => update({ op: e.target.value })}
            >
              {OPS.map((o) => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
            <Operand label={`${label} right`} value={c.right} onChange={(right) => update({ right })} allowValue />
          </div>
        );
      })}
      {conds.length < MAX_CONDITIONS && (
        <button
          type="button"
          onClick={() => set([...conds, { left: { ind: "close" }, op: ">", right: { ind: "sma", n: 200 } }])}
          className="self-start inline-flex items-center gap-1 text-xs text-pencil hover:underline rounded-sm"
        >
          <Plus className="size-3" aria-hidden="true" /> Add a condition
        </button>
      )}
    </fieldset>
  );
}

export default function RuleBuilder({ rule, onChange }) {
  const r = rule || DEFAULT_RULE;
  return (
    <div className="flex flex-col gap-4" data-testid="rule-builder">
      <label className="flex items-center gap-2 text-xs text-graphite">
        Take a
        <select
          aria-label="Direction"
          className={selectClass}
          value={r.direction || "long"}
          onChange={(e) => onChange({ ...r, direction: e.target.value })}
        >
          <option value="long">long</option>
          <option value="short">short</option>
        </select>
        position
      </label>
      <Block name="Entry" block={r.entry} onChange={(entry) => onChange({ ...r, entry })} />
      <Block name="Exit" block={r.exit} onChange={(exit) => onChange({ ...r, exit })} />
      <p className="text-xs text-faint leading-relaxed">
        Held from the entry until the exit; if both fire on the same day, the exit wins. A signal
        seen at one day&rsquo;s close counts from the next day, so no rule can see ahead.
        Validation for your own rules is coming later.
      </p>
    </div>
  );
}
