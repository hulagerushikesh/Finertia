import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, m, useReducedMotion } from "motion/react";
import { Link2, Check, Download } from "lucide-react";
import ConfigPanel, { DEFAULTS, STRATEGIES } from "../components/ConfigPanel";
import MetricsGrid from "../components/MetricsGrid";
import EquityCurveChart from "../components/EquityCurveChart";
import DrawdownChart from "../components/DrawdownChart";
import TradesTable from "../components/TradesTable";
import ValidationPanel from "../components/ValidationPanel";
import MonthlyHeatmap from "../components/MonthlyHeatmap";
import RollingSharpeChart from "../components/RollingSharpeChart";
import RegimeTable from "../components/RegimeTable";
import AnnualReturnsChart from "../components/AnnualReturnsChart";
import PortfolioLegs from "../components/PortfolioLegs";
import Spinner from "../components/Spinner";
import { Badge } from "@/components/ui/badge";
import { Rise, Stagger, StaggerItem, EASE_OUT } from "../components/motion";
import { runBacktest, validateStrategy, runPortfolio } from "../api";
import { exportEquityCurve, exportTrades, exportMetrics } from "../utils/csv";
import { encodeParams, decodeParams, permalinkFor } from "../utils/permalink";
import { useToast } from "../hooks/useToast";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";

const WF_TOAST = {
  held_up: ["Validation passed — the edge held up out-of-sample", "success"],
  weakened: ["Validation: edge weakened out-of-sample", "info"],
  overfit: ["Validation: these parameters are overfit", "error"],
  failed: ["Validation failed — no edge on unseen data", "error"],
  inconclusive: ["Validation inconclusive — no in-sample edge to test", "info"],
};

/** The one-word verdict for the results header, once validation has run. */
const WF_STAMP = {
  held_up: ["Held up", "gain"],
  weakened: ["Weakened", "warn"],
  overfit: ["Overfit", "loss"],
  failed: ["Failed", "loss"],
  inconclusive: ["Inconclusive", "faint"],
};

export default function DashboardPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const off = useReducedMotion();
  // Precedence: a re-run from History carries explicit state, which beats the
  // URL; then a shared permalink; then the defaults.
  const [params, setParams] = useState(
    () => location.state?.params || decodeParams(location.search) || DEFAULTS,
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [tab, setTab] = useState("results");
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [copied, setCopied] = useState(false);

  // Keep the address bar in step with the config so a reload or a bookmark
  // preserves it. `replace` rather than `push` — every keystroke would
  // otherwise become a history entry and Back would crawl.
  useEffect(() => {
    navigate({ search: encodeParams(params) }, { replace: true });
  }, [params, navigate]);

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(permalinkFor(params));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access is denied outside a secure context. Showing the URL
      // is the useful fallback.
      showToast(permalinkFor(params), "info");
    }
  }

  const isPortfolio = params.mode === "portfolio";

  async function handleRun() {
    setError("");
    setLoading(true);
    try {
      const data = isPortfolio ? await runPortfolio(params) : await runBacktest(params);
      setResult(data);
      // Previous validation belongs to the previous config.
      setValidation(null);
      setTab("results");
      const pct = (data.metrics.total_return * 100).toFixed(2);
      const subject = isPortfolio ? `${params.tickers.length}-name portfolio` : params.ticker;
      showToast(`${subject} complete — ${pct}% total return`, "success");
    } catch (err) {
      const message = err.message || "Backtest failed.";
      setError(message);
      showToast(message, "error");
    } finally {
      setLoading(false);
    }
  }

  async function handleValidate() {
    setError("");
    setValidating(true);
    setTab("validation");
    try {
      const data = await validateStrategy(params);
      setValidation(data);
      const [msg, tone] = WF_TOAST[data.walk_forward.verdict] || WF_TOAST.inconclusive;
      showToast(msg, tone);
    } catch (err) {
      const message = err.message || "Validation failed.";
      setError(message);
      showToast(message, "error");
    } finally {
      setValidating(false);
    }
  }

  function handleTab(next) {
    if (next === "validation" && !validation && !validating) {
      handleValidate();
      return;
    }
    setTab(next);
  }

  const strategyLabel =
    STRATEGIES.find((s) => s.id === (result?.strategy || params.strategy))?.label || params.strategy;
  const stamp = validation ? WF_STAMP[validation.walk_forward.verdict] || WF_STAMP.inconclusive : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* The workspace shows no page title — you arrive to configure a run,
          not to read a header. But the document still needs one. */}
      <h1 className="sr-only">Backtest workspace</h1>
      <div className="flex flex-col lg:flex-row gap-6 items-stretch lg:items-start">
        <ConfigPanel params={params} setParams={setParams} onRun={handleRun} loading={loading} />

        <div className="flex-1 min-w-0">
          {/* An error with no way forward is just an accusation. The button
              repeats the action that failed. */}
          {error && (
            <Alert variant="destructive" className="mb-5">
              <AlertDescription className="flex flex-wrap items-center gap-x-4 gap-y-2">
                <span className="flex-1 min-w-[14rem]">{error}</span>
                <Button variant="outline" size="sm" onClick={handleRun} disabled={loading}>
                  Try again
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <AnimatePresence mode="wait" initial={false}>
            {!result && !loading && (
              <m.div
                key="empty"
                initial={off ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, transition: { duration: 0.1 } }}
                transition={{ duration: 0.22, ease: EASE_OUT }}
                className="sheet border-2 border-dashed border-border shadow-none p-8 sm:p-10 flex flex-col items-start gap-4"
              >
                <p className="eyebrow">Nothing run yet</p>
                <h2 className="font-display text-display-sm font-semibold text-foreground max-w-md text-balance">
                  {isPortfolio
                    ? `Run the ${params.tickers.length}-name portfolio and see what comes back.`
                    : `Run ${params.ticker || "a ticker"} and see what comes back.`}
                </h2>
                <p className="text-sm text-graphite max-w-md leading-relaxed">
                  The set-up beside this is ready to go. You will get twelve metrics with confidence
                  intervals, an equity curve against buy-and-hold, and a plain statement of what the
                  result cannot tell you.
                </p>
                <div className="flex flex-wrap items-center gap-3 mt-1">
                  <Button onClick={handleRun}>{isPortfolio ? "Run portfolio" : "Run backtest"}</Button>
                  <Button asChild variant="outline">
                    <Link to="/demo">Look at a finished one</Link>
                  </Button>
                </div>
              </m.div>
            )}

            {/* Shaped like the result it is replacing, so the page does not
                jump when it is swapped out. */}
            {loading && (
              <m.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, transition: { duration: 0.1 } }}
                className="flex flex-col gap-3"
                aria-live="polite"
                aria-busy="true"
              >
                <div className="flex items-center gap-3 mb-1 text-graphite">
                  <Spinner className="text-pencil" />
                  <p className="text-sm">Fetching prices and computing signals…</p>
                </div>
                <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-[6.5rem] rounded-lg" />
                  ))}
                </div>
                <Skeleton className="h-14 rounded-lg" />
                <Skeleton className="h-64 rounded-lg" />
              </m.div>
            )}

            {result && !loading && (
              <m.div
                key="result"
                initial={off ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.22, ease: EASE_OUT }}
                className="flex flex-col gap-5"
              >
                {/* Header row: the run, named the way a report names its subject. */}
                <div className="flex items-end justify-between gap-4 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h2 className="font-display text-display-sm font-semibold text-foreground tracking-tight">
                        {isPortfolio ? result.tickers.join(" · ") : params.ticker}
                      </h2>
                     <Badge variant="outline" className="font-mono text-2xs uppercase tracking-wider text-graphite">
                        {strategyLabel}
                      </Badge>
                      {stamp && (
                        <Badge size="sm" variant={stamp[1]}>
                          {stamp[0]}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs font-mono text-graphite mt-1.5">
                      {result.start || params.start} → {result.end || params.end}
                      <span className="text-faint"> · </span>
                      {isPortfolio
                        ? `${result.aligned_bars} bars shared by all ${result.tickers.length} holdings`
                        : `${result.signals_summary.long_days}d long · ${result.signals_summary.short_days}d short · ${result.signals_summary.flat_days}d flat`}
                      <span className="text-faint"> · </span>
                      {(result.duration_ms / 1000).toFixed(2)}s
                    </p>
                    {/* The price source only matters when it is the fallback:
                        the last good copy served because Yahoo was down. */}
                    {result.data_source === "cache-stale" && (
                      <p className="text-2xs text-warn mt-1.5 leading-relaxed max-w-prose">
                        Prices came from the last good cached copy — the market data provider was
                        unreachable, so the most recent sessions may be missing from this run.
                      </p>
                    )}
                  </div>
                  <Button variant="ghost" size="sm" onClick={handleCopyLink} className="text-graphite">
                    {copied ? <Check className="size-3.5 text-gain" /> : <Link2 className="size-3.5" />}
                    {copied ? "Link copied" : "Copy link to this set-up"}
                  </Button>
                </div>

                {/* Results / Validation switcher. Walk-forward and the
                    permutation test are defined on a single position series,
                    so they have no portfolio meaning yet. */}
                <Tabs value={tab} onValueChange={handleTab}>
                  <div className="flex items-center justify-between gap-3 border-b border-border">
                    <TabsList className="bg-transparent p-0 h-auto gap-1 rounded-none">
                      <TabsTrigger
                        value="results"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-pencil data-[state=active]:shadow-none data-[state=active]:bg-transparent px-4 py-2 -mb-px text-sm"
                      >
                        Results
                      </TabsTrigger>
                      {!isPortfolio && (
                        <TabsTrigger
                          value="validation"
                          disabled={validating}
                          className="rounded-none border-b-2 border-transparent data-[state=active]:border-pencil data-[state=active]:shadow-none data-[state=active]:bg-transparent px-4 py-2 -mb-px text-sm"
                        >
                          Validation
                          {!validation && !validating && (
                            <span className="ml-2 font-mono text-2xs text-pencil">run</span>
                          )}
                        </TabsTrigger>
                      )}
                    </TabsList>
                    {tab === "validation" && validation && (
                      <Button variant="ghost" size="sm" onClick={handleValidate} disabled={validating} className="text-graphite">
                        Re-run checks
                      </Button>
                    )}
                  </div>
                </Tabs>

                {tab === "results" && (
                  <Stagger className="flex flex-col gap-5">
                    <StaggerItem>
                      <MetricsGrid metrics={result.metrics} confidenceIntervals={result.confidence_intervals} />
                    </StaggerItem>
                    {isPortfolio && (
                      <StaggerItem>
                        <PortfolioLegs result={result} />
                      </StaggerItem>
                    )}
                    <StaggerItem><EquityCurveChart data={result.equity_curve} /></StaggerItem>
                    <StaggerItem><DrawdownChart data={result.drawdown} /></StaggerItem>
                    {result.annual_returns?.length > 0 && (
                      <StaggerItem><AnnualReturnsChart data={result.annual_returns} /></StaggerItem>
                    )}
                    {result.monthly_returns?.length > 0 && (
                      <StaggerItem><MonthlyHeatmap data={result.monthly_returns} /></StaggerItem>
                    )}
                    <StaggerItem><RollingSharpeChart data={result.rolling_sharpe} /></StaggerItem>
                    {result.regimes && (
                      <StaggerItem><RegimeTable regimes={result.regimes} /></StaggerItem>
                    )}
                    {result.trades?.length > 0 && (
                      <StaggerItem><TradesTable trades={result.trades} /></StaggerItem>
                    )}

                    {/* The limits of the result, stated where the result is. */}
                    <StaggerItem className="grid lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] gap-x-8 gap-y-3 border-t border-border pt-6">
                      <p className="margin-note">What this backtest cannot tell you.</p>
                      <ul className="text-sm text-graphite leading-relaxed flex flex-col gap-2.5 max-w-prose">
                        <li>
                          <strong className="text-foreground font-medium">Survivorship bias.</strong>{" "}
                          Price history only exists for companies that still trade. Testing on{" "}
                          {isPortfolio ? result.tickers.join(", ") : params.ticker} is testing on
                          survivors — the delisted and bankrupt names that would have dragged the same
                          strategy down are simply not in the data.
                          {isPortfolio &&
                            " A hand-picked basket of names you already know did well is the sharpest form of this."}
                        </li>
                        <li>
                          <strong className="text-foreground font-medium">
                            {isPortfolio ? "One basket, one period." : "One ticker, one period."}
                          </strong>{" "}
                          A single result is one draw from a distribution.{" "}
                          {isPortfolio
                            ? "Validation runs on a single position series, so it is not available for portfolios yet — check the strategy on individual names first."
                            : "Run the Validation tab to see whether these parameters hold on data they were never fitted to."}
                        </li>
                        <li>
                          <strong className="text-foreground font-medium">Idealised fills.</strong>{" "}
                          Every trade executes at the close at a flat{" "}
                          {(params.transaction_cost * 100).toFixed(2)}% cost. Real slippage widens when
                          you are trading size or trading a fast market.
                        </li>
                      </ul>
                    </StaggerItem>

                    <StaggerItem className="flex items-center gap-2 flex-wrap border-t border-border pt-4">
                      <span className="eyebrow mr-2">Export</span>
                      <Button variant="outline" size="sm" onClick={() => exportEquityCurve(result, params)}>
                        <Download className="size-3.5" /> Equity curve CSV
                      </Button>
                      <Button
                        variant="outline" size="sm"
                        onClick={() => exportTrades(result, params)}
                        disabled={!result.trades?.length}
                      >
                        <Download className="size-3.5" /> Trades CSV
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => exportMetrics(result, params)}>
                        <Download className="size-3.5" /> Metrics CSV
                      </Button>
                    </StaggerItem>
                  </Stagger>
                )}

                {tab === "validation" &&
                  (validating ? (
                    <div className="flex flex-col items-center justify-center h-72 sheet" aria-busy="true">
                      <Spinner size={8} className="text-pencil mb-4" />
                      <p className="text-sm text-graphite">Sweeping parameters and shuffling signals…</p>
                      <p className="text-xs text-faint mt-1">
                        This runs hundreds of backtests — a few seconds
                      </p>
                    </div>
                  ) : validation ? (
                    <ValidationPanel data={validation} />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-72 border-2 border-dashed border-border rounded-lg text-graphite px-6 text-center">
                      <p className="font-display text-xl font-semibold text-foreground">Check for overfitting</p>
                      <p className="text-sm mt-1 max-w-sm leading-relaxed">
                        Tests whether these parameters survive on data they were not tuned on, and
                        whether the signal timing beats random entries.
                      </p>
                      <Button onClick={handleValidate} className="mt-4">
                        Run validation
                      </Button>
                    </div>
                  ))}
              </m.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
