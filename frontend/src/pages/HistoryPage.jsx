import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, m } from "motion/react";
import { getHistory, compareRuns } from "../api";
import { SkeletonRows } from "../components/SkeletonRow";
import { DEFAULTS, STRATEGIES } from "../components/ConfigPanel";
import ComparisonPanel from "../components/ComparisonPanel";
import Spinner from "../components/Spinner";
import { Pager } from "../components/TradesTable";
import { Rise, EASE_OUT } from "../components/motion";
import { useToast } from "../hooks/useToast";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

// Matches the server-side cap in CompareRequest.
const MAX_COMPARE = 4;
const PAGE_SIZE = 20;
const SKELETON_WIDTHS = ["70%", "45%", "85%", "55%", "40%", "50%", "40%", "45%"];

const strategyLabel = (id) => STRATEGIES.find((s) => s.id === id)?.label || "Momentum";

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

function fmtDate(ts) {
  if (!ts) return "—";
  // The API serialises Firestore timestamps to an ISO string; the client SDK
  // hands back a Timestamp (.toDate) or a {_seconds} shape. Handle all three.
  let d;
  if (typeof ts === "string" || typeof ts === "number") d = new Date(ts);
  else if (ts.toDate) d = ts.toDate();
  else if (ts._seconds != null) d = new Date(ts._seconds * 1000);
  else d = new Date(NaN);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  const [picked, setPicked] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError("");
    getHistory(PAGE_SIZE, page * PAGE_SIZE)
      .then((d) => {
        setRuns(d.runs);
        setTotal(d.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function togglePick(runId) {
    setPicked((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId);
      if (prev.length >= MAX_COMPARE) {
        showToast(`Compare up to ${MAX_COMPARE} runs at once`, "info");
        return prev;
      }
      return [...prev, runId];
    });
  }

  async function handleCompare() {
    setError("");
    setComparing(true);
    try {
      const data = await compareRuns(picked);
      setComparison(data);
      if (data.overlapping_days === 0) {
        showToast("These runs cover periods that never overlap", "info");
      }
    } catch (err) {
      const message = err.message || "Comparison failed.";
      setError(message);
      showToast(message, "error");
    } finally {
      setComparing(false);
    }
  }

  function clearComparison() {
    setComparison(null);
    setPicked([]);
  }

  function handleReRun(run) {
    // Start from DEFAULTS so every strategy's parameters exist, then layer the
    // run's own values on top. Older runs have no `strategy`; those are momentum.
    navigate("/dashboard", {
      state: {
        params: {
          ...DEFAULTS,
          ...run.params,
          strategy: run.strategy || "momentum",
          ticker: run.ticker,
          start: run.start,
          end: run.end,
        },
      },
    });
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <Rise className="flex items-end justify-between gap-4 flex-wrap mb-8">
        <div>
          <p className="eyebrow mb-3">Saved runs</p>
          <h1 className="font-display text-display-sm font-semibold text-foreground">History</h1>
        </div>
        {!comparison && runs.length > 1 && (
          <p className="text-xs text-graphite">Tick two or more runs to overlay their equity curves</p>
        )}
      </Rise>

      {error && (
        <Alert variant="destructive" className="mb-5">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {comparison ? (
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h2 className="font-display text-xl font-semibold text-foreground">Comparison</h2>
            <Button variant="outline" size="sm" onClick={clearComparison}>
              ← Back to history
            </Button>
          </div>
          <ComparisonPanel data={comparison} />
        </div>
      ) : (
        <>
          <section className="sheet overflow-hidden">
            <div className="overflow-x-auto">
              <Table className="min-w-[52rem]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10 pl-4" />
                    <TableHead>Date</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead className="text-right">Total return</TableHead>
                    <TableHead className="text-right">Sharpe</TableHead>
                    <TableHead className="text-right">Max DD</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                    <TableHead className="pr-4" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading && <SkeletonRows rows={8} widths={SKELETON_WIDTHS} />}
                  {!loading &&
                    runs.map((run) => (
                      <TableRow
                        key={run.runId}
                        className="cursor-pointer"
                        onClick={() => setSelected(run)}
                      >
                        <TableCell className="w-10 pl-4" onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={picked.includes(run.runId)}
                            onCheckedChange={() => togglePick(run.runId)}
                            aria-label={`Select ${run.ticker} run for comparison`}
                          />
                        </TableCell>
                        <TableCell className="text-graphite font-mono text-xs whitespace-nowrap">
                          {fmtDate(run.createdAt)}
                        </TableCell>
                        <TableCell className="font-mono text-sm font-medium text-foreground">
                          <span className="flex items-center gap-2">
                            {run.ticker}
                            <Badge variant="outline" className="font-mono text-tick uppercase tracking-wider text-graphite font-normal px-1.5 py-0">
                              {strategyLabel(run.strategy)}
                            </Badge>
                          </span>
                        </TableCell>
                        <TableCell className="text-graphite text-xs font-mono whitespace-nowrap">
                          {run.start} → {run.end}
                        </TableCell>
                        <TableCell
                          className={cn(
                            "text-right font-mono text-xs",
                            run.metrics?.total_return >= 0 ? "text-gain" : "text-loss",
                          )}
                        >
                          {fmtPct(run.metrics?.total_return)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-foreground">
                          {run.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-loss">
                          {fmtPct(run.metrics?.max_drawdown)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-graphite">
                          {run.durationMs ? `${(run.durationMs / 1000).toFixed(1)}s` : "—"}
                        </TableCell>
                        <TableCell className="text-right pr-4">
                          <Button
                            variant="link"
                            size="sm"
                            className="text-pencil h-auto p-0"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleReRun(run);
                            }}
                          >
                            Re-run
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  {!loading && runs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-14">
                        <p className="font-display text-xl font-semibold text-foreground">No runs yet.</p>
                        <p className="text-sm text-graphite mt-1">
                          Run a backtest in the workspace and it will be kept here with its parameters.
                        </p>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </section>

          {!loading && <Pager page={page} totalPages={totalPages} onPage={setPage} className="mt-4" />}
        </>
      )}

      {/* Compare bar — only once a comparison is actually possible */}
      <AnimatePresence>
        {!comparison && picked.length > 0 && (
          <m.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12, transition: { duration: 0.12 } }}
            transition={{ duration: 0.2, ease: EASE_OUT }}
            className="sticky bottom-4 mt-4 flex items-center justify-between gap-3 flex-wrap sheet-lifted border-l-2 border-l-pencil px-5 py-3"
          >
            <span className="text-sm text-foreground">
              {picked.length} run{picked.length === 1 ? "" : "s"} selected
              {picked.length === 1 && <span className="text-graphite"> — pick one more to compare</span>}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setPicked([])}>
                Clear
              </Button>
              <Button onClick={handleCompare} disabled={picked.length < 2 || comparing}>
                {comparing ? (
                  <>
                    <Spinner /> Recomputing…
                  </>
                ) : (
                  "Compare"
                )}
              </Button>
            </div>
          </m.div>
        )}
      </AnimatePresence>

      {/* Detail drawer */}
      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          {selected && (
            <>
              <SheetHeader className="text-left">
                <SheetTitle className="font-display text-2xl font-semibold">{selected.ticker}</SheetTitle>
                <SheetDescription className="font-mono text-xs">
                  {selected.start} → {selected.end}
                  <span className="ml-2 text-pencil">{strategyLabel(selected.strategy)}</span>
                </SheetDescription>
              </SheetHeader>

              <div className="grid grid-cols-2 gap-2 my-6">
                {Object.entries(selected.metrics || {}).map(([k, v]) => (
                  <div key={k} className="bg-muted/50 rounded-md p-3">
                    <p className="eyebrow mb-1 truncate">{k.replace(/_/g, " ")}</p>
                    <p className="text-sm font-mono text-foreground">
                      {typeof v === "number" ? v.toFixed(4) : v}
                    </p>
                  </div>
                ))}
              </div>

              <div className="border-t border-border pt-4">
                <p className="eyebrow mb-2">Parameters</p>
                <pre className="text-xs text-graphite font-mono bg-muted/50 rounded-md p-3 overflow-x-auto">
                  {JSON.stringify(selected.params, null, 2)}
                </pre>
              </div>

              <Button onClick={() => handleReRun(selected)} className="mt-5 w-full">
                Re-run this configuration
              </Button>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
