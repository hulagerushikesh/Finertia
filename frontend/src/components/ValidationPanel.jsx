import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import VerdictCard from "./VerdictCard";
import RollingWalkForward from "./RollingWalkForward";
import { Stagger, StaggerItem } from "./motion";
import { cn } from "@/lib/utils";

const WF_VERDICT = {
  held_up: {
    label: "Held up",
    tone: "gain",
    blurb: "The strategy kept most of its edge on data it was never tuned on.",
  },
  weakened: {
    label: "Weakened",
    tone: "warn",
    blurb: "Some edge survived out-of-sample, but a meaningful part of it did not.",
  },
  overfit: {
    label: "Overfit",
    tone: "loss",
    blurb: "Most of the in-sample edge vanished on unseen data. The parameters were fitted to noise.",
  },
  failed: {
    label: "Failed",
    tone: "loss",
    blurb: "The strategy lost money out-of-sample. In-sample performance was not predictive.",
  },
  inconclusive: {
    label: "Inconclusive",
    tone: "faint",
    blurb: "In-sample performance was not positive, so there is no edge to test for decay.",
  },
};

const DSR_VERDICT = {
  significant: {
    label: "Survives selection",
    tone: "gain",
    blurb:
      "The in-sample Sharpe is high enough to be unlikely from cherry-picking alone.",
  },
  marginal: {
    label: "Borderline",
    tone: "warn",
    blurb:
      "It clears the noise bar, but not by enough to rule out a lucky pick with confidence.",
  },
  not_significant: {
    label: "Could be luck",
    tone: "loss",
    blurb:
      "It beats the noise bar, but not by enough to distinguish from a fortunate draw.",
  },
  noise: {
    label: "Indistinguishable from noise",
    tone: "loss",
    blurb:
      "Searching this many combinations would be expected to produce a Sharpe this high even with no edge at all.",
  },
  inconclusive: {
    label: "Cannot say",
    tone: "faint",
    blurb: "The sample is too thin or too lopsided for this correction to mean anything.",
  },
};

const PBO_VERDICT = {
  robust: {
    label: "Robust",
    tone: "gain",
    blurb: "Across every way of dividing this period, the combination chosen on one half kept ranking well on the other.",
  },
  acceptable: {
    label: "Acceptable",
    tone: "gain",
    blurb: "The selection usually holds up across splits, though not always.",
  },
  fragile: {
    label: "Fragile",
    tone: "warn",
    blurb: "The in-sample winner drops below the out-of-sample median on a large minority of splits.",
  },
  overfit: {
    label: "Overfit",
    tone: "loss",
    blurb: "The combination that wins on one half lands below the median on the other at least half the time — no better than choosing at random.",
  },
};

const pct = (v) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)}%`);
const num = (v) => (v === null || v === undefined ? "—" : v.toFixed(3));

const PARAM_LABELS = {
  momentum_lookback: "lookback",
  ma_window: "MA",
  momentum_threshold: "threshold",
  macd_fast: "fast",
  macd_slow: "slow",
  macd_signal: "signal",
  bb_window: "window",
  bb_std: "std",
};

/** Render whatever parameters a strategy happens to use, not a fixed set. */
function describeParams(params) {
  if (!params) return "—";
  return Object.entries(params)
    .map(([k, v]) => `${PARAM_LABELS[k] || k} ${v}`)
    .join(" · ");
}

function Stat({ label, value, tone = "text-foreground", mark = false }) {
  return (
    <div>
      <p className="eyebrow mb-1">{label}</p>
      <p className={cn("font-mono text-sm", tone, mark && "pencil-mark")}>{value}</p>
    </div>
  );
}

/** Section header with the verdict stamped beside it. */
function Head({ title, blurb, stamp, tone }) {
  return (
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div className="max-w-lg">
        <h2 className="font-display text-xl font-semibold text-foreground">{title}</h2>
        <p className="text-xs text-graphite mt-1 leading-relaxed">{blurb}</p>
      </div>
      <Badge variant={tone} className="shrink-0">{stamp}</Badge>
    </div>
  );
}

/** A figure in a box, the way the three PBO and DSR numbers are set. */
function Figure({ label, value, sub, tone = "text-foreground", mark = false }) {
  return (
    <div className="bg-muted/50 rounded-md p-4">
      <p className="eyebrow mb-1.5">{label}</p>
      <p className={cn("font-display text-2xl font-semibold", tone, mark && "pencil-mark")}>{value}</p>
      {sub && <p className="text-2xs text-faint mt-1">{sub}</p>}
    </div>
  );
}

function SegmentCard({ title, caption, metrics, checked = false }) {
  const good = metrics.total_return >= 0;
  return (
    <div className={cn("rounded-md p-4", checked ? "bg-pencil/5 ring-1 ring-pencil/30" : "bg-muted/50")}>
      <div className="flex items-baseline justify-between mb-3 gap-3">
        <h3 className="text-xs font-semibold text-foreground">{title}</h3>
        <span className={cn("text-2xs font-mono", checked ? "text-pencil" : "text-graphite")}>{caption}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Total return" value={pct(metrics.total_return)} tone={good ? "text-gain" : "text-loss"} mark={checked} />
        <Stat label="Sharpe" value={num(metrics.sharpe_ratio)} mark={checked} />
        <Stat label="Max drawdown" value={pct(metrics.max_drawdown)} tone="text-loss" />
        <Stat label="Trades" value={metrics.num_trades} />
      </div>
    </div>
  );
}

/**
 * The two halves of the walk-forward split do not touch — a purge-and-embargo
 * gap sits between them. Worth stating in the UI rather than only in the code,
 * because it explains why the bar counts do not add up to the period and why
 * the split ratio the user chose is not exactly what they got.
 */
function BoundaryNote({ boundary }) {
  if (!boundary.applied) {
    return (
      <p className="text-2xs text-warn leading-relaxed mb-5">
        This period was too short to leave a gap at the split, so the two halves
        touch. A trade held across the boundary earns in both — the out-of-sample
        figure may be flattered by a move the selection was already paid for. A
        longer date range removes the doubt.
      </p>
    );
  }
  return (
    <p
      className={cn("text-2xs leading-relaxed mb-5", boundary.shortened ? "text-warn" : "text-faint")}
    >
      A {boundary.purge_bars}-bar gap sits on each side of the split, so selection
      stops at{" "}
      <span className="font-mono text-foreground">{boundary.in_sample_end_date}</span>{" "}
      and scoring resumes at{" "}
      <span className="font-mono pencil-mark">{boundary.out_of_sample_start_date}</span>.
      Without it, a position held across the boundary would earn once as evidence
      for choosing these parameters and again as proof they worked.
      {boundary.shortened && (
        <>
          {" "}This period could only spare {boundary.purge_bars} of the{" "}
          {boundary.requested_gap} bars that gap wants, so some of that
          double-counting is still in the numbers below.
        </>
      )}
    </p>
  );
}

/**
 * N is not the grid size. A 20-day and a 25-day lookback are nearly the same
 * trial, so the noise bar built from "16 attempts" is punishing the winner
 * for company it never had. This states the raw count and the measured one
 * side by side, and the deflated probability under each. The headline takes
 * the larger of the two estimates — lowering N is the direction that flatters
 * a result, so when they disagree the tool sides with the higher bar.
 */
function EffectiveN({ et }) {
  const raw = et.under_raw;
  const eff = et.under_effective;
  const gap = et.dsr_gap;
  const same = et.n_trials_effective === et.n_trials_raw;
  return (
    <div className="mt-5 pt-4 border-t border-border">
      <p className="eyebrow mb-3">How many of those trials were really distinct</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-muted/50 rounded-md p-4">
          <p className="text-2xs text-graphite mb-1">Counted as</p>
          <p className="font-display text-2xl font-semibold text-foreground">
            {et.n_trials_raw} <span className="text-sm text-graphite font-sans">trials</span>
          </p>
          <p className="text-2xs text-faint mt-1">
            deflated probability {raw?.deflated_sharpe_ratio === null ? "—" : pct(raw?.deflated_sharpe_ratio)}
          </p>
        </div>
        <div className="bg-pencil/5 ring-1 ring-pencil/30 rounded-md p-4">
          <p className="text-2xs text-pencil mb-1">Measured as</p>
          <p className="font-display text-2xl font-semibold text-foreground pencil-mark">
            {et.n_trials_effective} <span className="text-sm text-graphite font-sans">distinct</span>
          </p>
          <p className="text-2xs text-faint mt-1">
            deflated probability{" "}
            <span className="text-foreground">{eff?.deflated_sharpe_ratio === null ? "—" : pct(eff?.deflated_sharpe_ratio)}</span>
            {gap !== null && gap !== undefined && gap !== 0 && (
              <span className={gap > 0 ? "text-gain" : "text-loss"}>
                {" "}({gap > 0 ? "+" : "−"}{(Math.abs(gap) * 100).toFixed(2)} pts)
              </span>
            )}
          </p>
        </div>
      </div>
      <p className="text-2xs text-graphite mt-3 leading-relaxed">
        {same
          ? "Every combination in the grid behaved differently from every other in-sample, so the raw count stands."
          : <>
              Measured two ways from how the candidates' in-sample returns move together — an
              eigenvalue count says {Math.round(et.eigen?.n_effective ?? 0)}, correlation clustering says{" "}
              {et.clusters?.n_effective}
              {et.clusters?.silhouette !== null && et.clusters?.silhouette !== undefined && (
                <> (silhouette {et.clusters.silhouette.toFixed(2)})</>
              )}
              . The headline takes the <strong className="text-foreground font-medium">larger</strong>, because a
              smaller N is the direction that flatters a result; {et.n_trials_lower_bound} is the lower bound.
              {eff?.verdict && raw?.verdict && eff.verdict !== raw.verdict && (
                <> Under the measured count the verdict reads <span className="text-foreground">{(DSR_VERDICT[eff.verdict] || DSR_VERDICT.inconclusive).label.toLowerCase()}</span>.</>
              )}
            </>}
      </p>
    </div>
  );
}

export default function ValidationPanel({ data }) {
  if (!data) return null;

  const { walk_forward: wf, permutation: pm } = data;
  const dsrVerdict =
    DSR_VERDICT[wf.deflated?.verdict] || DSR_VERDICT.inconclusive;
  const ov = wf.overfitting;
  const boundary = wf.boundary;
  const pboVerdict = PBO_VERDICT[ov?.verdict] || PBO_VERDICT.fragile;
  const verdict = WF_VERDICT[wf.verdict] || WF_VERDICT.inconclusive;

  // The working is long — five sheets of figures — and most readers want
  // the answer first. Collapsed by default; the choice is remembered so a
  // researcher who always opens it never has to again.
  const [showWorking, setShowWorking] = useState(() => {
    try {
      return localStorage.getItem("finertia-validation-working") === "open";
    } catch {
      return false;
    }
  });
  const setWorking = (next) => {
    setShowWorking(next);
    try {
      localStorage.setItem("finertia-validation-working", next ? "open" : "closed");
    } catch {
      /* private mode — the toggle still works for this page */
    }
  };
  const toggleWorking = () => setWorking(!showWorking);
  // A chip on the verdict card opens the working, then scrolls to its section
  // on the next frame, once the section has mounted.
  const jumpTo = (id) => {
    setWorking(true);
    requestAnimationFrame(() =>
      requestAnimationFrame(() =>
        document.getElementById(`validation-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" })
      )
    );
  };

  return (
    <Stagger className="flex flex-col gap-5">
      <StaggerItem>
        <VerdictCard data={data} onJump={jumpTo} />
      </StaggerItem>

      <StaggerItem className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <button
          type="button"
          onClick={toggleWorking}
          aria-expanded={showWorking}
          aria-controls="validation-working"
          className="tap-safe inline-flex items-center gap-2 text-xs font-medium text-pencil hover:underline underline-offset-4 whitespace-nowrap"
        >
          <span aria-hidden="true" className="font-mono">{showWorking ? "−" : "+"}</span>
          {showWorking ? "Hide the working" : "Show the working"}
        </button>
        <span className="text-2xs text-faint">every figure behind the verdict, with its interval</span>
      </StaggerItem>

      {showWorking && (
      <div id="validation-working" className="flex flex-col gap-5">
      {/* ── Walk-forward ── */}
      <StaggerItem as="section" id="validation-walk-forward" className="sheet p-6 scroll-mt-20">
        <Head
          title="Walk-forward validation"
          blurb="Parameters were optimised on the earlier part of the period, then scored on the later part. Only the green figures are evidence."
          stamp={verdict.label}
          tone={verdict.tone}
        />

        <p className="margin-note mt-4 mb-5">{verdict.blurb}</p>

        <div className="flex flex-wrap gap-x-6 gap-y-2 text-2xs font-mono text-graphite mb-3">
          <span>split <span className="text-foreground">{wf.split_date}</span></span>
          <span>{wf.in_sample_bars} in-sample bars</span>
          <span>{wf.out_of_sample_bars} out-of-sample bars</span>
          <span>{wf.combinations_tested} combinations tested</span>
        </div>

        {boundary && <BoundaryNote boundary={boundary} />}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <SegmentCard title="In-sample (tuned here)" caption="optimistic" metrics={wf.best_in_sample} />
          <SegmentCard
            title="Out-of-sample (never seen)"
            caption="the checked number"
            metrics={wf.best_out_of_sample}
            checked
          />
        </div>

        <div className="mt-4 flex items-center justify-between bg-muted/50 rounded-md px-4 py-3 flex-wrap gap-2">
          <div>
            <p className="eyebrow">Best parameters found</p>
            <p className="font-mono text-xs text-foreground mt-0.5">{describeParams(wf.best_params)}</p>
          </div>
          <div className="text-right">
            <p className="eyebrow">Sharpe decay</p>
            <p className={cn("font-mono text-xs mt-0.5", wf.sharpe_degradation > 0.5 ? "text-loss" : "text-foreground")}>
              {wf.sharpe_degradation > 0 ? "−" : "+"}
              {Math.abs(wf.sharpe_degradation).toFixed(3)}
            </p>
          </div>
        </div>

        {wf.user_params && (
          <div className="mt-3 bg-muted/50 rounded-md px-4 py-3">
            <p className="eyebrow mb-2">Your parameters ({describeParams(wf.user_params.params)})</p>
            <div className="flex flex-wrap gap-x-8 gap-y-2 font-mono text-xs">
              <span className="text-graphite">
                in-sample Sharpe{" "}
                <span className="text-foreground">{num(wf.user_params.in_sample.sharpe_ratio)}</span>
              </span>
              <span className="text-graphite">
                out-of-sample Sharpe{" "}
                <span
                  className={cn(
                    "pencil-mark",
                    wf.user_params.out_of_sample.sharpe_ratio >= 0 ? "text-gain" : "text-loss",
                  )}
                >
                  {num(wf.user_params.out_of_sample.sharpe_ratio)}
                </span>
              </span>
            </div>
          </div>
        )}
      </StaggerItem>

      {/* The single split, walked forward. Directly after it because it is
          the same experiment repeated, not a different one. */}
      {data.rolling_walk_forward && (
        <StaggerItem id="validation-rolling" className="scroll-mt-20">
          <RollingWalkForward rolling={data.rolling_walk_forward} />
        </StaggerItem>
      )}

      {/* Deflation. Sits between walk-forward and the permutation test because
          it is a correction *to* walk-forward, not a separate experiment. */}
      {wf.deflated?.computable && (
        <StaggerItem as="section" id="validation-deflated" className="sheet p-6 scroll-mt-20">
          <Head
            title="Deflated Sharpe ratio"
            blurb={`Picking the best of ${wf.deflated.n_trials} combinations is itself a search, and the winner of any search looks good. This asks how high a Sharpe that search would have produced on data with no edge at all, then measures the winner against that bar instead of zero.`}
            stamp={dsrVerdict.label}
            tone={dsrVerdict.tone}
          />

          <p className="margin-note mt-4 mb-5">{wf.deflated.unreliable || dsrVerdict.blurb}</p>

          {!wf.deflated.unreliable && (
            <>
              {/* The comparison the whole section exists to make. */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Figure label="Selected Sharpe" value={num(wf.deflated.selected_sharpe)} sub="in-sample, annualised" />
                <Figure
                  label="Noise bar"
                  value={num(wf.deflated.expected_max_sharpe)}
                  sub={`best of ${wf.deflated.n_trials} on no edge`}
                  tone={wf.deflated.clears_noise_bar ? "text-foreground" : "text-loss"}
                />
                <Figure
                  label="Deflated probability"
                  value={wf.deflated.deflated_sharpe_ratio === null ? "—" : pct(wf.deflated.deflated_sharpe_ratio)}
                  sub="0.95 is the usual bar"
                  tone={
                    wf.deflated.deflated_sharpe_ratio >= 0.95
                      ? "text-gain"
                      : wf.deflated.deflated_sharpe_ratio >= 0.9
                        ? "text-warn"
                        : "text-loss"
                  }
                  mark
                />
              </div>

              {/* Stating the uncorrected figure beside it is the point: the gap
                  between the two is exactly what selection was worth. */}
              {wf.deflated.psr_vs_zero !== null && (
                <p className="text-xs text-graphite mt-4 leading-relaxed">
                  Without correcting for the search, the same result reads as{" "}
                  <span className="font-mono text-foreground">{pct(wf.deflated.psr_vs_zero)}</span>{" "}
                  likely to be real. Accounting for {wf.deflated.n_trials} attempts takes it to{" "}
                  <span className="font-mono pencil-mark">
                    {wf.deflated.deflated_sharpe_ratio === null ? "—" : pct(wf.deflated.deflated_sharpe_ratio)}
                  </span>
                  .
                </p>
              )}

              {wf.deflated.effective_trials?.computable && (
                <EffectiveN et={wf.deflated.effective_trials} />
              )}

              <div className="flex flex-wrap gap-x-6 gap-y-2 text-2xs font-mono text-faint mt-4">
                <span>skew {num(wf.deflated.skew)}</span>
                <span>kurtosis {num(wf.deflated.kurtosis)}</span>
                <span>
                  in the market {pct(wf.deflated.active_fraction)} of bars
                </span>
              </div>
            </>
          )}
        </StaggerItem>
      )}

      {/* Probability of Backtest Overfitting. Sits last of the three because
          it judges the whole selection procedure rather than any single run. */}
      {ov?.computable && (
        <StaggerItem as="section" id="validation-overfitting" className="sheet p-6 scroll-mt-20">
          <Head
            title="Probability of backtest overfitting"
            blurb={`The split above is one split. This one cuts the period into ${ov.n_splits} blocks and tries all ${ov.n_combinations} balanced ways of splitting them, each time picking the best combination on one half and checking where it lands on the other.`}
            stamp={pboVerdict.label}
            tone={pboVerdict.tone}
          />

          <p className="margin-note mt-4 mb-5">{pboVerdict.blurb}</p>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Figure
              label="PBO"
              value={pct(ov.pbo)}
              sub="50% is a coin flip"
              tone={ov.pbo >= 0.5 ? "text-loss" : ov.pbo >= 0.35 ? "text-warn" : "text-gain"}
              mark
            />
            <Figure
              label="Loses money"
              value={pct(ov.probability_of_loss)}
              sub="of splits, out-of-sample"
              tone={ov.probability_of_loss >= 0.5 ? "text-loss" : "text-foreground"}
            />
            <Figure
              label="Median Sharpe"
              sub="in-sample → out"
              value={
                <>
                  {num(ov.median_is_sharpe)}
                  <span className="text-faint"> → </span>
                  <span className={ov.median_oos_sharpe < ov.median_is_sharpe ? "text-loss" : "text-gain"}>
                    {num(ov.median_oos_sharpe)}
                  </span>
                </>
              }
            />
            <Figure
              label="Degradation"
              value={num(ov.degradation_slope)}
              sub="slope, OOS on IS"
              tone={ov.degradation_slope < 0 ? "text-loss" : "text-gain"}
            />
          </div>

          {/* The slope is the number most worth explaining, and it is the one
              nobody would interpret unaided. */}
          {ov.degradation_slope < 0 && (
            <p className="text-xs text-warn mt-4 leading-relaxed">
              The slope is negative, which is the damning case: across these
              splits, a <em>better</em> in-sample score predicted a{" "}
              <em>worse</em> out-of-sample one. Tuning harder on this data made
              results worse, not better.
            </p>
          )}

          <p className="text-xs text-faint mt-4 leading-relaxed">
            These splits are drawn from blocks spread across the whole period, so
            both halves cover the same years. That is deliberate — it isolates
            whether selection works at all — but it means this test cannot see a
            regime change. The chronological split above is what catches that.
          </p>
        </StaggerItem>
      )}

      <StaggerItem as="section" id="validation-timing" className="sheet p-6 scroll-mt-20">
        <Head
          title="Signal timing test"
          blurb={`The position series was randomly reordered ${pm.trials} times, keeping the exact same number of long, short, and flat days. If real timing beats the shuffles, the entries are doing work that market exposure alone would not.`}
          stamp={pm.significant ? "Significant" : "Not significant"}
          tone={pm.significant ? "gain" : "loss"}
        />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 mb-5">
          <Stat label="Real Sharpe" value={num(pm.real_sharpe)} mark />
          <Stat label="Percentile" value={`${(pm.percentile * 100).toFixed(1)}%`} />
          <Stat label="p-value" value={pm.p_value.toFixed(3)} tone={pm.significant ? "text-gain" : "text-loss"} mark />
          <Stat label="Random mean" value={num(pm.random_sharpe_mean)} tone="text-graphite" />
        </div>

        {/* Where the real result sits among the shuffled ones */}
        <div>
          <div className="relative h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-pencil/30"
              style={{ width: `${Math.min(pm.percentile * 100, 100)}%` }}
            />
          </div>
          <div className="relative mt-1.5" style={{ height: "1rem" }}>
            {(() => {
              const at = Math.min(Math.max(pm.percentile * 100, 0), 100);
              // Near either end the label would overflow its container, so anchor
              // it inward instead of centring it on the marker.
              const shift = at > 82 ? "-100%" : at < 18 ? "0%" : "-50%";
              return (
                <span
                  className="absolute text-2xs font-mono text-pencil whitespace-nowrap"
                  style={{ left: `${at}%`, transform: `translateX(${shift})` }}
                >
                  ▲ your strategy
                </span>
              );
            })()}
          </div>
          <p className="text-2xs text-graphite mt-2 leading-relaxed">
            {pm.significant
              ? `Real timing beat ${(pm.percentile * 100).toFixed(0)}% of random reorderings — unlikely to be chance (p = ${pm.p_value.toFixed(3)}).`
              : `Random timing matched or beat this result ${(pm.p_value * 100).toFixed(0)}% of the time. The returns look like market exposure rather than signal quality.`}
          </p>
        </div>
      </StaggerItem>

      <p className="text-2xs text-graphite leading-relaxed max-w-prose">
        These checks are diagnostic and are not saved to your run history. A strategy can pass the
        timing test and still fail walk-forward — that combination means the approach has signal but
        the specific parameters were tuned too tightly.
      </p>
      </div>
      )}
    </Stagger>
  );
}
