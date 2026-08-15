import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ConfigPanel, { DEFAULTS, STRATEGIES } from "../components/ConfigPanel";
import MetricsGrid from "../components/MetricsGrid";
import EquityCurveChart from "../components/EquityCurveChart";
import DrawdownChart from "../components/DrawdownChart";
import TradesTable from "../components/TradesTable";
import ValidationPanel from "../components/ValidationPanel";
import MonthlyHeatmap from "../components/MonthlyHeatmap";
import RollingSharpeChart from "../components/RollingSharpeChart";
import AnnualReturnsChart from "../components/AnnualReturnsChart";
import PortfolioLegs from "../components/PortfolioLegs";
import { runBacktest, validateStrategy, runPortfolio } from "../api";
import { exportEquityCurve, exportTrades, exportMetrics } from "../utils/csv";
import { encodeParams, decodeParams, permalinkFor } from "../utils/permalink";
import { useToast } from "../hooks/useToast";

const WF_TOAST = {
  held_up: ["Validation passed — the edge held up out-of-sample", "success"],
  weakened: ["Validation: edge weakened out-of-sample", "info"],
  overfit: ["Validation: these parameters are overfit", "error"],
  failed: ["Validation failed — no edge on unseen data", "error"],
  inconclusive: ["Validation inconclusive — no in-sample edge to test", "info"],
};

export default function DashboardPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();
  // Precedence: a re-run from History carries explicit state, which beats the
  // URL; then a shared permalink; then the defaults.
  const [params, setParams] = useState(
    () => location.state?.params || decodeParams(location.search) || DEFAULTS
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [tab, setTab] = useState("results");
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [copied, setCopied] = useState(false);

  // Keep the address bar in step with the config so a reload or a bookmark
  // preserves it. `replace` rather than `push` — every keystroke in the panel
  // would otherwise become a separate history entry and Back would crawl.
  useEffect(() => {
    navigate({ search: encodeParams(params) }, { replace: true });
  }, [params, navigate]);

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(permalinkFor(params));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access is denied outside a secure context, which includes
      // plain http on a LAN address. Showing the URL is the useful fallback.
      showToast(permalinkFor(params), "info");
    }
  }

  const isPortfolio = params.mode === "portfolio";

  async function handleRun() {
    setError("");
    setLoading(true);
    try {
      const data = isPortfolio
        ? await runPortfolio(params)
        : await runBacktest(params);
      setResult(data);
      // Previous validation belongs to the previous config.
      setValidation(null);
      setTab("results");
      const pct = (data.metrics.total_return * 100).toFixed(2);
      const subject = isPortfolio
        ? `${params.tickers.length}-name portfolio`
        : params.ticker;
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col lg:flex-row gap-6 items-stretch lg:items-start">
        {/* Sidebar */}
        <ConfigPanel
          params={params}
          setParams={setParams}
          onRun={handleRun}
          loading={loading}
        />

        {/* Results */}
        <div className="flex-1 min-w-0">
          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-5 py-4 mb-5">
              {error}
            </div>
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-80 border border-dashed border-border rounded-2xl text-text-muted">
              <p className="text-4xl mb-3">⚡</p>
              <p className="font-medium text-text-primary">Configure and run a backtest</p>
              <p className="text-sm mt-1">Results will appear here</p>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center h-80 border border-border rounded-2xl">
              <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-sm text-text-muted">Fetching data and computing signals…</p>
            </div>
          )}

          {result && !loading && (
            <div className="flex flex-col gap-5">
              {/* Header row */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2 flex-wrap">
                    {isPortfolio ? result.tickers.join(" · ") : params.ticker}
                    <span className="text-text-muted font-normal">
                      {result.start || params.start} → {result.end || params.end}
                    </span>
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider bg-accent/10 text-accent border border-accent/30 px-2 py-0.5 rounded-full">
                      {STRATEGIES.find((s) => s.id === (result.strategy || params.strategy))?.label ||
                        params.strategy}
                    </span>
                  </h2>
                  {/* A portfolio has no single position series, so it reports
                      how many shared bars its holdings actually had instead. */}
                  <p className="text-xs text-text-muted mt-0.5">
                    {isPortfolio
                      ? `${result.aligned_bars} bars shared by all ${result.tickers.length} holdings`
                      : `${result.signals_summary.long_days}d long · ${result.signals_summary.short_days}d short · ${result.signals_summary.flat_days}d flat`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopyLink}
                    className="text-xs font-mono text-text-muted hover:text-accent border border-border hover:border-accent px-3 py-1 rounded-full transition-colors"
                    title="Copy a link that reopens this exact configuration"
                  >
                    {copied ? "Link copied" : "Share config"}
                  </button>
                  <span className="text-xs font-mono bg-success/10 text-success border border-success/20 px-3 py-1 rounded-full">
                    Completed in {(result.duration_ms / 1000).toFixed(2)}s
                  </span>
                </div>
              </div>

              {/* Results / Validation switcher */}
              <div className="flex items-center gap-1 border-b border-border">
                <button
                  onClick={() => setTab("results")}
                  className={`text-sm font-medium px-4 py-2 border-b-2 -mb-px transition-colors ${
                    tab === "results"
                      ? "border-accent text-text-primary"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                >
                  Results
                </button>
                {/* Walk-forward and the permutation test are defined on a
                    single position series, so they have no portfolio meaning
                    yet. Hiding the tab beats offering one that always errors. */}
                {!isPortfolio && (
                <button
                  onClick={() => (validation ? setTab("validation") : handleValidate())}
                  disabled={validating}
                  className={`text-sm font-medium px-4 py-2 border-b-2 -mb-px transition-colors disabled:opacity-50 ${
                    tab === "validation"
                      ? "border-accent text-text-primary"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                >
                  Validation
                  {!validation && !validating && (
                    <span className="ml-2 text-[10px] font-mono text-accent">run</span>
                  )}
                </button>
                )}
                {tab === "validation" && validation && (
                  <button
                    onClick={handleValidate}
                    disabled={validating}
                    className="ml-auto text-xs text-text-muted hover:text-accent transition-colors disabled:opacity-50"
                  >
                    Re-run checks
                  </button>
                )}
              </div>

              {tab === "results" && (
                <>
                  <MetricsGrid metrics={result.metrics} />
                  {isPortfolio && <PortfolioLegs result={result} />}
                  <EquityCurveChart data={result.equity_curve} />
                  <DrawdownChart data={result.drawdown} />
                  {result.annual_returns?.length > 0 && (
                    <AnnualReturnsChart data={result.annual_returns} />
                  )}
                  {result.monthly_returns?.length > 0 && (
                    <MonthlyHeatmap data={result.monthly_returns} />
                  )}
                  <RollingSharpeChart data={result.rolling_sharpe} />
                  {result.trades?.length > 0 && <TradesTable trades={result.trades} />}

                  {/* The limits of the result, stated where the result is —
                      not buried in a docs page nobody opens. */}
                  <div className="bg-warning/5 border border-warning/20 rounded-xl px-5 py-4">
                    <p className="text-xs font-semibold text-warning uppercase tracking-wider mb-2">
                      What this backtest cannot tell you
                    </p>
                    <ul className="text-xs text-text-muted leading-relaxed flex flex-col gap-1.5">
                      <li>
                        <strong className="text-text-primary">Survivorship bias.</strong>{" "}
                        Price history only exists for companies that still trade. Testing
                        on {isPortfolio ? result.tickers.join(", ") : params.ticker} is
                        testing on survivors — the delisted and bankrupt names that would
                        have dragged the same strategy down are simply not in the data.
                        {isPortfolio &&
                          " A hand-picked basket of names you already know did well is the sharpest form of this."}
                      </li>
                      <li>
                        <strong className="text-text-primary">
                          {isPortfolio ? "One basket, one period." : "One ticker, one period."}
                        </strong>{" "}
                        A single result is one draw from a distribution.{" "}
                        {isPortfolio
                          ? "Validation runs on a single position series, so it is not available for portfolios yet — check the strategy on individual names first."
                          : "Run the Validation tab to see whether these parameters hold on data they were never fitted to."}
                      </li>
                      <li>
                        <strong className="text-text-primary">Idealised fills.</strong>{" "}
                        Every trade executes at the close at a flat{" "}
                        {(params.transaction_cost * 100).toFixed(2)}% cost. Real slippage
                        widens when you are trading size or trading a fast market.
                      </li>
                    </ul>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap border-t border-border pt-4">
                    <span className="text-xs text-text-muted">Export</span>
                    <button
                      onClick={() => exportEquityCurve(result, params)}
                      className="text-xs text-text-muted hover:text-accent border border-border hover:border-accent rounded-lg px-3 py-1.5 transition-colors"
                    >
                      Equity curve CSV
                    </button>
                    <button
                      onClick={() => exportTrades(result, params)}
                      disabled={!result.trades?.length}
                      className="text-xs text-text-muted hover:text-accent border border-border hover:border-accent rounded-lg px-3 py-1.5 transition-colors disabled:opacity-40 disabled:hover:text-text-muted disabled:hover:border-border"
                    >
                      Trades CSV
                    </button>
                    <button
                      onClick={() => exportMetrics(result, params)}
                      className="text-xs text-text-muted hover:text-accent border border-border hover:border-accent rounded-lg px-3 py-1.5 transition-colors"
                    >
                      Metrics CSV
                    </button>
                  </div>
                </>
              )}

              {tab === "validation" && (
                validating ? (
                  <div className="flex flex-col items-center justify-center h-72 border border-border rounded-2xl">
                    <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin mb-4" />
                    <p className="text-sm text-text-muted">
                      Sweeping parameters and shuffling signals…
                    </p>
                    <p className="text-xs text-text-muted/60 mt-1">
                      This runs hundreds of backtests — a few seconds
                    </p>
                  </div>
                ) : validation ? (
                  <ValidationPanel data={validation} />
                ) : (
                  <div className="flex flex-col items-center justify-center h-72 border border-dashed border-border rounded-2xl text-text-muted px-6 text-center">
                    <p className="font-medium text-text-primary">Check for overfitting</p>
                    <p className="text-sm mt-1 max-w-sm leading-relaxed">
                      Tests whether these parameters survive on data they were not tuned on, and
                      whether the signal timing beats random entries.
                    </p>
                    <button
                      onClick={handleValidate}
                      className="mt-4 bg-accent hover:bg-indigo-500 text-white font-semibold px-5 py-2 rounded-lg text-sm transition-colors"
                    >
                      Run validation
                    </button>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
