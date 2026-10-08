import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button } from "@/components/ui/button";
import MetricsGrid from "../components/MetricsGrid";
import EquityCurveChart from "../components/EquityCurveChart";
import DrawdownChart from "../components/DrawdownChart";
import AnnualReturnsChart from "../components/AnnualReturnsChart";
import RollingSharpeChart from "../components/RollingSharpeChart";
import MonthlyHeatmap from "../components/MonthlyHeatmap";
import RegimeTable from "../components/RegimeTable";
import BenchmarkTest from "../components/BenchmarkTest";
import CostSensitivity from "../components/CostSensitivity";
import ValidationPanel from "../components/ValidationPanel";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Rise, Stagger, StaggerItem } from "../components/motion";
import demo from "../demoData.json";
import validation from "../demoValidation.json";

const TAB =
  "rounded-none border-b-2 border-transparent data-[state=active]:border-pencil data-[state=active]:shadow-none data-[state=active]:bg-transparent px-4 py-2 -mb-px text-sm";

/**
 * A real result, no login required.
 *
 * The numbers are a genuine run of the shipped engine on AAPL 2019–2024,
 * frozen into JSON — not invented figures chosen to look good. It shows
 * momentum badly losing to buy-and-hold, which is the honest thing to lead
 * with for a product whose whole argument is that backtests flatter
 * themselves.
 *
 * The Validation tab is the same config's /api/validate response, frozen the
 * same way (backend/scripts/freeze_demo_validation.py). Without it the checks
 * the product is built around were invisible until after sign-up. The tab
 * lives in the URL hash so /demo#validation can be linked to directly.
 */
export default function DemoPage() {
  const { user } = useAuth();
  const { hash } = useLocation();
  const navigate = useNavigate();
  const tab = hash === "#validation" ? "validation" : "results";
  const setTab = (next) => navigate({ hash: next === "validation" ? "validation" : "" }, { replace: true });
  const start = user ? "/dashboard" : "/register";
  const strategyEnd = demo.equity_curve[demo.equity_curve.length - 1].strategy;
  const benchmarkEnd = demo.equity_curve[demo.equity_curve.length - 1].benchmark;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise className="flex items-start justify-between gap-6 flex-wrap mb-8">
        <div className="max-w-2xl">
          <p className="eyebrow mb-4">A real result · no account needed</p>
          <h1 className="font-display text-display-md font-semibold tracking-tight text-foreground text-balance">
            Momentum on {demo.ticker}, {demo.start.slice(0, 4)}–{demo.end.slice(0, 4)}.
          </h1>
          <p className="text-sm font-mono text-graphite mt-3">
            {demo.bars} trading days · {demo.signals_summary.long_days}d long ·{" "}
            {demo.signals_summary.short_days}d short · {demo.signals_summary.flat_days}d flat
          </p>
        </div>
        <Button asChild>
          <Link to={start}>Run your own</Link>
        </Button>
      </Rise>

      <Rise delay={0.06} className="sheet px-6 py-5 mb-8 grid sm:grid-cols-[auto_1fr] gap-x-6 gap-y-3 items-start">
        <Badge variant="loss" size="lg" className="mt-1">
          Lost to holding
        </Badge>
        <div>
          <p className="font-display text-xl font-semibold text-foreground">
            This strategy lost badly to doing nothing.
          </p>
          <p className="text-sm text-graphite leading-relaxed mt-2">
            It turned $1 into ${strategyEnd.toFixed(2)}. Buying and holding {demo.ticker} over the
            same period turned it into ${benchmarkEnd.toFixed(2)} — roughly{" "}
            {(benchmarkEnd / strategyEnd).toFixed(1)}× better, with no trading and no fees. We lead
            with this because it is the result the engine actually produced, and because a
            backtesting tool that only ever shows you winners is not measuring anything.
          </p>
        </div>
      </Rise>

      <Tabs value={tab} onValueChange={setTab} className="mb-5">
        <TabsList className="bg-transparent p-0 h-auto gap-1 rounded-none border-b border-border w-full justify-start">
          <TabsTrigger value="results" className={TAB}>Results</TabsTrigger>
          <TabsTrigger value="validation" className={TAB}>
            Validation
            <span className="ml-2 font-mono text-2xs text-loss">{validation.walk_forward.verdict.replace("_", " ")}</span>
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {tab === "validation" ? (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-graphite leading-relaxed max-w-3xl">
            Was it skill or luck? The same rule, re-tuned on the first 70% of {demo.start.slice(0, 4)}–
            {demo.end.slice(0, 4)} and scored on the last 30% it never saw, then checked against
            hundreds of shuffled versions of itself. This is a real run of the checks, saved. On
            the Pro plan they run on any stock and rule you choose.
          </p>
          <ValidationPanel data={validation} />
        </div>
      ) : (
      <Stagger className="flex flex-col gap-5">
        <StaggerItem><MetricsGrid metrics={demo.metrics} confidenceIntervals={demo.confidence_intervals} /></StaggerItem>
        {demo.benchmark_test && (
          <StaggerItem><BenchmarkTest test={demo.benchmark_test} /></StaggerItem>
        )}
        {demo.cost_sensitivity && (
          <StaggerItem><CostSensitivity data={demo.cost_sensitivity} /></StaggerItem>
        )}
        <StaggerItem><EquityCurveChart data={demo.equity_curve} /></StaggerItem>
        <StaggerItem><DrawdownChart data={demo.drawdown} /></StaggerItem>
        <StaggerItem><AnnualReturnsChart data={demo.annual_returns} /></StaggerItem>
        <StaggerItem><MonthlyHeatmap data={demo.monthly_returns} /></StaggerItem>
        <StaggerItem><RollingSharpeChart data={demo.rolling_sharpe} /></StaggerItem>
        <StaggerItem><RegimeTable regimes={demo.regimes} /></StaggerItem>
      </Stagger>
      )}

      <div className="mt-10 grid lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-8 border-t border-border pt-8">
        <p className="margin-note">
          One strategy, one ticker, one period, on its default parameters.
        </p>
        <div>
          <p className="text-sm text-graphite leading-relaxed">
            The question that decides whether any of it means anything is whether the result
            survives on data the parameters were never fitted to. The{" "}
            <button type="button" onClick={() => { setTab("validation"); window.scrollTo({ top: 0 }); }} className="text-pencil underline underline-offset-2">
              Validation tab
            </button>{" "}
            answers that for this run. A free account runs the backtest on any stock; the checks
            are part of <Link to="/pricing" className="text-pencil underline underline-offset-2">Pro</Link>.
          </p>
          <div className="flex items-center gap-3 flex-wrap mt-5">
            <Button asChild>
              <Link to={start}>{user ? "Run it in your workspace" : "Create a free account"}</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/docs">How it works</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
