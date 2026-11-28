import React, { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { runScan } from "../api";
import { DEFAULTS, STRATEGIES } from "../components/ConfigPanel";
import { decodeParams } from "../utils/permalink";
import Spinner from "../components/Spinner";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

/**
 * Index scan: the set-up from the workspace, run on every stock in an index.
 *
 * The page's job is the comparison a single backtest cannot make — on how
 * many of these stocks did it work, and is that more than luck — so the
 * summary leads with the count that beat holding next to the count chance
 * alone would give. The table is there to look inside, not to pick from.
 */

export const UNIVERSES = [
  { id: "nifty50", label: "Nifty 50" },
  { id: "niftynext50", label: "Nifty Next 50" },
  { id: "nasdaq100", label: "Nasdaq-100" },
];

const COLUMNS = [
  ["ticker", "Stock", "text"],
  ["total_return", "Return", "pct"],
  ["hold_total_return", "Holding it", "pct"],
  ["sharpe_ratio", "Sharpe", "num"],
  ["sharpe_vs_hold", "Sharpe vs holding", "num"],
  ["max_drawdown", "Worst fall", "pct"],
  ["num_trades", "Trades", "int"],
  ["p_value", "p", "p"],
];

const fmt = (kind, v) => {
  if (v === null || v === undefined) return "—";
  if (kind === "pct") return `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1)}%`;
  if (kind === "num") return v.toFixed(2);
  if (kind === "p") return v.toFixed(3);
  return String(v);
};
const tone = (kind, v) =>
  kind === "pct" || kind === "num" ? (v > 0 ? "text-gain" : v < 0 ? "text-loss" : "") : "";

/** The headline sentence: the count, and what luck alone would give. */
export function scanSentence(s) {
  const luck = s.expected_by_chance;
  const base = `Beat holding the stock on ${s.beats_holding} of ${s.tested_against_holding}`;
  const chance =
    luck < 1 ? "chance alone would give less than one" : `chance alone would give about ${Number(luck.toFixed(1))}`;
  if (s.survives_correction > 0) {
    return `${base}; ${chance}. ${s.survives_correction} still ${s.survives_correction === 1 ? "stands" : "stand"} after correcting for testing ${s.tested_against_holding} stocks at once.`;
  }
  return `${base}; ${chance}. None stands after correcting for testing ${s.tested_against_holding} stocks at once.`;
}

export default function ScanPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useMemo(
    () => location.state?.params || decodeParams(location.search) || DEFAULTS,
    [location.state, location.search]
  );
  const [universe, setUniverse] = useState("nifty50");
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [sort, setSort] = useState(["sharpe_ratio", -1]);

  const strategyLabel = STRATEGIES.find((s) => s.id === params.strategy)?.label || params.strategy;

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      setResult(await runScan({ ...params, mode: "single" }, universe));
    } catch (err) {
      setError(err.message || "The scan failed.");
    } finally {
      setRunning(false);
    }
  }

  const rows = useMemo(() => {
    if (!result) return [];
    const [key, dir] = sort;
    const ok = result.rows.filter((r) => r.status === "ok");
    return [...ok].sort((a, b) => {
      const x = a[key] ?? -Infinity;
      const y = b[key] ?? -Infinity;
      return (x > y ? 1 : x < y ? -1 : 0) * dir;
    });
  }, [result, sort]);
  const skipped = result ? result.rows.filter((r) => r.status !== "ok") : [];

  function open(ticker) {
    navigate("/dashboard", { state: { params: { ...params, mode: "single", ticker } } });
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <p className="eyebrow mb-2">Index scan</p>
      <h1 className="font-display text-display-sm font-semibold text-foreground">
        One set-up, every stock in an index
      </h1>
      <p className="text-sm text-graphite mt-2 max-w-prose leading-relaxed">
        <span className="text-foreground">{strategyLabel}</span>, {params.start} → {params.end}, with the
        costs and risk settings from your workspace.{" "}
        <Link to="/dashboard" state={{ params }} className="text-pencil hover:underline">
          Change the set-up
        </Link>
      </p>

      <div className="flex flex-wrap items-center gap-3 mt-6" role="group" aria-label="Index">
        {UNIVERSES.map((u) => (
          <button
            key={u.id}
            type="button"
            aria-pressed={universe === u.id}
            onClick={() => setUniverse(u.id)}
            className={cn(
              "tap-safe rounded-md border px-3 py-1.5 text-sm transition-colors",
              universe === u.id ? "border-pencil text-foreground bg-muted" : "border-border text-graphite hover:bg-muted/60"
            )}
          >
            {u.label}
          </button>
        ))}
        <Button onClick={handleRun} disabled={running} className="ml-auto">
          {running ? <Spinner className="size-4" /> : null}
          {running ? "Scanning…" : "Run scan"}
        </Button>
      </div>
      <p className="text-2xs text-faint mt-2">
        Counts as one run from your monthly allowance. Prices are the nightly copy; nothing is saved to
        your history.
      </p>

      {error && (
        <p className="text-sm text-loss mt-6" role="alert">
          {error}
        </p>
      )}

      {result && (
        <section className="mt-8" aria-labelledby="scan-summary">
          <div className="sheet p-6">
            <p className="eyebrow mb-2">
              {result.universe_title} · {result.summary.ran} stocks
              {result.summary.skipped ? ` · ${result.summary.skipped} skipped` : ""}
            </p>
            <h2 id="scan-summary" className="font-display text-xl font-semibold text-foreground text-balance">
              {scanSentence(result.summary)}
            </h2>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-2xs font-mono text-graphite mt-4">
              <span>made money on {result.summary.made_money}</span>
              <span>ahead of holding on {result.summary.ahead_of_holding}</span>
              <span>median Sharpe {fmt("num", result.summary.median_sharpe)}</span>
              <span>median vs holding {fmt("pct", result.summary.median_excess_return)}</span>
            </div>
            <p className="text-xs text-faint mt-4 leading-relaxed max-w-prose">
              &ldquo;Beat holding&rdquo; means the strategy&rsquo;s Sharpe ratio was above holding the same
              stock by more than a 5% test allows for chance. Test enough stocks and some pass by luck, which
              is why the count chance would give sits beside it. Past results on these stocks, not a
              forecast for any of them.
            </p>
          </div>

          <div className="mt-5 overflow-x-auto -mx-4 sm:mx-0">
            <Table className="text-xs font-mono">
              <TableHeader>
                <TableRow>
                  {COLUMNS.map(([key, label, kind]) => (
                    <TableHead key={key} className={cn(kind !== "text" && "text-right")}>
                      <button
                        type="button"
                        className="hover:text-foreground"
                        onClick={() => setSort(([k, d]) => [key, k === key ? -d : -1])}
                        aria-label={`Sort by ${label}`}
                      >
                        {label}
                        {sort[0] === key ? (sort[1] > 0 ? " ↑" : " ↓") : ""}
                      </button>
                    </TableHead>
                  ))}
                  <TableHead>Beats holding</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.ticker} data-testid="scan-row" className="cursor-pointer" onClick={() => open(r.ticker)}>
                    {COLUMNS.map(([key, , kind]) => (
                      <TableCell key={key} className={cn(kind !== "text" ? "text-right" : "text-foreground", tone(kind, r[key]))}>
                        {key === "ticker" ? (
                          <button type="button" className="hover:underline" onClick={(e) => { e.stopPropagation(); open(r.ticker); }}>
                            {r.ticker}
                          </button>
                        ) : (
                          fmt(kind, r[key])
                        )}
                      </TableCell>
                    ))}
                    <TableCell className={cn("font-sans", r.survives_correction ? "text-gain" : r.beats_holding ? "text-warn" : "text-faint")}>
                      {r.survives_correction ? "yes, after correction" : r.beats_holding ? "yes, could be luck" : "no"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {skipped.length > 0 && (
            <p className="text-2xs text-faint mt-3 leading-relaxed">
              Skipped: {skipped.map((r) => `${r.ticker} (${r.reason})`).join("; ")}.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
