import React from "react";

const WF_VERDICT = {
  held_up: {
    label: "Held up",
    tone: "text-success border-success/30 bg-success/10",
    blurb: "The strategy kept most of its edge on data it was never tuned on.",
  },
  weakened: {
    label: "Weakened",
    tone: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
    blurb: "Some edge survived out-of-sample, but a meaningful part of it did not.",
  },
  overfit: {
    label: "Overfit",
    tone: "text-danger border-danger/30 bg-danger/10",
    blurb: "Most of the in-sample edge vanished on unseen data. The parameters were fitted to noise.",
  },
  failed: {
    label: "Failed",
    tone: "text-danger border-danger/30 bg-danger/10",
    blurb: "The strategy lost money out-of-sample. In-sample performance was not predictive.",
  },
  inconclusive: {
    label: "Inconclusive",
    tone: "text-text-muted border-border bg-bg",
    blurb: "In-sample performance was not positive, so there is no edge to test for decay.",
  },
};

const DSR_VERDICT = {
  significant: {
    label: "Survives selection",
    tone: "text-success border-success/30 bg-success/10",
    blurb:
      "The in-sample Sharpe is high enough to be unlikely from cherry-picking alone.",
  },
  marginal: {
    label: "Borderline",
    tone: "text-warning border-warning/30 bg-warning/10",
    blurb:
      "It clears the noise bar, but not by enough to rule out a lucky pick with confidence.",
  },
  not_significant: {
    label: "Could be luck",
    tone: "text-danger border-danger/30 bg-danger/10",
    blurb:
      "It beats the noise bar, but not by enough to distinguish from a fortunate draw.",
  },
  noise: {
    label: "Indistinguishable from noise",
    tone: "text-danger border-danger/30 bg-danger/10",
    blurb:
      "Searching this many combinations would be expected to produce a Sharpe this high even with no edge at all.",
  },
  inconclusive: {
    label: "Cannot say",
    tone: "text-text-muted border-border bg-bg",
    blurb: "The sample is too thin or too lopsided for this correction to mean anything.",
  },
};

const PBO_VERDICT = {
  robust: {
    label: "Robust",
    tone: "text-success border-success/30 bg-success/10",
    blurb: "Across every way of dividing this period, the combination chosen on one half kept ranking well on the other.",
  },
  acceptable: {
    label: "Acceptable",
    tone: "text-success border-success/30 bg-success/10",
    blurb: "The selection usually holds up across splits, though not always.",
  },
  fragile: {
    label: "Fragile",
    tone: "text-warning border-warning/30 bg-warning/10",
    blurb: "The in-sample winner drops below the out-of-sample median on a large minority of splits.",
  },
  overfit: {
    label: "Overfit",
    tone: "text-danger border-danger/30 bg-danger/10",
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

function Stat({ label, value, tone = "text-text-primary" }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-text-muted mb-1">{label}</p>
      <p className={`font-mono text-sm ${tone}`}>{value}</p>
    </div>
  );
}

function SegmentCard({ title, caption, metrics, accent }) {
  const good = metrics.total_return >= 0;
  return (
    <div className="bg-bg border border-border rounded-xl p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h4 className="text-xs font-semibold text-text-primary">{title}</h4>
        <span className={`text-[10px] font-mono ${accent}`}>{caption}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Stat
          label="Total return"
          value={pct(metrics.total_return)}
          tone={good ? "text-success" : "text-danger"}
        />
        <Stat label="Sharpe" value={num(metrics.sharpe_ratio)} />
        <Stat label="Max drawdown" value={pct(metrics.max_drawdown)} tone="text-danger" />
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
      <p className="text-[11px] text-warning leading-relaxed mb-5">
        This period was too short to leave a gap at the split, so the two halves
        touch. A trade held across the boundary earns in both — the out-of-sample
        figure may be flattered by a move the selection was already paid for. A
        longer date range removes the doubt.
      </p>
    );
  }
  return (
    <p
      className={`text-[11px] leading-relaxed mb-5 ${
        boundary.shortened ? "text-warning" : "text-text-faint"
      }`}
    >
      A {boundary.purge_bars}-bar gap sits on each side of the split, so selection
      stops at{" "}
      <span className="font-mono">{boundary.in_sample_end_date}</span>{" "}
      and scoring resumes at{" "}
      <span className="font-mono">{boundary.out_of_sample_start_date}</span>.
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

export default function ValidationPanel({ data }) {
  if (!data) return null;

  const { walk_forward: wf, permutation: pm } = data;
  const dsrVerdict =
    DSR_VERDICT[wf.deflated?.verdict] || DSR_VERDICT.inconclusive;
  const ov = wf.overfitting;
  const boundary = wf.boundary;
  const pboVerdict = PBO_VERDICT[ov?.verdict] || PBO_VERDICT.fragile;
  const verdict = WF_VERDICT[wf.verdict] || WF_VERDICT.inconclusive;

  return (
    <div className="flex flex-col gap-5">
      {/* ── Walk-forward ── */}
      <section className="panel rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 mb-1 flex-wrap">
          <div>
            <h3 className="text-sm font-bold text-text-primary">Walk-forward validation</h3>
            <p className="text-xs text-text-muted mt-1 max-w-lg leading-relaxed">
              Parameters were optimised on the earlier part of the period, then
              scored on the later part. Only the out-of-sample column is evidence.
            </p>
          </div>
          <span
            className={`text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full border whitespace-nowrap ${verdict.tone}`}
          >
            {verdict.label}
          </span>
        </div>

        <p className="text-xs text-text-muted mt-3 mb-5 leading-relaxed">{verdict.blurb}</p>

        <div className="flex flex-wrap gap-x-6 gap-y-2 text-[11px] font-mono text-text-muted mb-3">
          <span>split <span className="text-text-primary">{wf.split_date}</span></span>
          <span>{wf.in_sample_bars} in-sample bars</span>
          <span>{wf.out_of_sample_bars} out-of-sample bars</span>
          <span>{wf.combinations_tested} combinations tested</span>
        </div>

        {boundary && <BoundaryNote boundary={boundary} />}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <SegmentCard
            title="In-sample (tuned here)"
            caption="optimistic"
            metrics={wf.best_in_sample}
            accent="text-text-muted"
          />
          <SegmentCard
            title="Out-of-sample (never seen)"
            caption="the honest number"
            metrics={wf.best_out_of_sample}
            accent="text-accent"
          />
        </div>

        <div className="mt-4 flex items-center justify-between bg-bg border border-border rounded-lg px-4 py-3 flex-wrap gap-2">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-text-muted">Best parameters found</p>
            <p className="font-mono text-xs text-text-primary mt-0.5">
              {describeParams(wf.best_params)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wider text-text-muted">Sharpe decay</p>
            <p
              className={`font-mono text-xs mt-0.5 ${
                wf.sharpe_degradation > 0.5 ? "text-danger" : "text-text-primary"
              }`}
            >
              {wf.sharpe_degradation > 0 ? "−" : "+"}
              {Math.abs(wf.sharpe_degradation).toFixed(3)}
            </p>
          </div>
        </div>

        {wf.user_params && (
          <div className="mt-3 bg-bg border border-border rounded-lg px-4 py-3">
            <p className="text-[10px] uppercase tracking-wider text-text-muted mb-2">
              Your parameters ({describeParams(wf.user_params.params)})
            </p>
            <div className="flex flex-wrap gap-x-8 gap-y-2 font-mono text-xs">
              <span className="text-text-muted">
                in-sample Sharpe{" "}
                <span className="text-text-primary">{num(wf.user_params.in_sample.sharpe_ratio)}</span>
              </span>
              <span className="text-text-muted">
                out-of-sample Sharpe{" "}
                <span
                  className={
                    wf.user_params.out_of_sample.sharpe_ratio >= 0 ? "text-success" : "text-danger"
                  }
                >
                  {num(wf.user_params.out_of_sample.sharpe_ratio)}
                </span>
              </span>
            </div>
          </div>
        )}
      </section>

      {/* ── Permutation test ── */}
      {/* Deflation. Sits between walk-forward and the permutation test because
          it is a correction *to* walk-forward, not a separate experiment. */}
      {wf.deflated?.computable && (
        <section className="panel rounded-2xl p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h3 className="text-sm font-bold text-text-primary">
                Deflated Sharpe ratio
              </h3>
              <p className="text-xs text-text-muted mt-1 max-w-lg leading-relaxed">
                Picking the best of {wf.deflated.n_trials} combinations is itself a
                search, and the winner of any search looks good. This asks how high
                a Sharpe that search would have produced on data with no edge at
                all, then measures the winner against that bar instead of zero.
              </p>
            </div>
            <span
              className={`text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full border whitespace-nowrap ${dsrVerdict.tone}`}
            >
              {dsrVerdict.label}
            </span>
          </div>

          <p className="text-xs text-text-muted mt-3 mb-5 leading-relaxed">
            {wf.deflated.unreliable || dsrVerdict.blurb}
          </p>

          {!wf.deflated.unreliable && (
            <>
              {/* The comparison the whole section exists to make. */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="bg-bg border border-border rounded-xl p-4">
                  <p className="eyebrow mb-1.5">Selected Sharpe</p>
                  <p className="font-mono text-lg text-text-primary">
                    {num(wf.deflated.selected_sharpe)}
                  </p>
                  <p className="text-[11px] text-text-faint mt-1">in-sample, annualised</p>
                </div>
                <div className="bg-bg border border-border rounded-xl p-4">
                  <p className="eyebrow mb-1.5">Noise bar</p>
                  <p
                    className={`font-mono text-lg ${
                      wf.deflated.clears_noise_bar ? "text-text-primary" : "text-danger"
                    }`}
                  >
                    {num(wf.deflated.expected_max_sharpe)}
                  </p>
                  <p className="text-[11px] text-text-faint mt-1">
                    best of {wf.deflated.n_trials} on no edge
                  </p>
                </div>
                <div className="bg-bg border border-border rounded-xl p-4">
                  <p className="eyebrow mb-1.5">Deflated probability</p>
                  <p
                    className={`font-mono text-lg ${
                      wf.deflated.deflated_sharpe_ratio >= 0.95
                        ? "text-success"
                        : wf.deflated.deflated_sharpe_ratio >= 0.9
                          ? "text-warning"
                          : "text-danger"
                    }`}
                  >
                    {wf.deflated.deflated_sharpe_ratio === null
                      ? "—"
                      : pct(wf.deflated.deflated_sharpe_ratio)}
                  </p>
                  <p className="text-[11px] text-text-faint mt-1">0.95 is the usual bar</p>
                </div>
              </div>

              {/* Stating the uncorrected figure beside it is the point: the gap
                  between the two is exactly what selection was worth. */}
              {wf.deflated.psr_vs_zero !== null && (
                <p className="text-xs text-text-muted mt-4 leading-relaxed">
                  Without correcting for the search, the same result reads as{" "}
                  <span className="font-mono text-text-primary">
                    {pct(wf.deflated.psr_vs_zero)}
                  </span>{" "}
                  likely to be real. Accounting for {wf.deflated.n_trials} attempts
                  takes it to{" "}
                  <span className="font-mono text-text-primary">
                    {wf.deflated.deflated_sharpe_ratio === null
                      ? "—"
                      : pct(wf.deflated.deflated_sharpe_ratio)}
                  </span>
                  .
                </p>
              )}

              <div className="flex flex-wrap gap-x-6 gap-y-2 text-[11px] font-mono text-text-faint mt-4">
                <span>skew {num(wf.deflated.skew)}</span>
                <span>kurtosis {num(wf.deflated.kurtosis)}</span>
                <span>
                  in the market {pct(wf.deflated.active_fraction)} of bars
                </span>
              </div>
            </>
          )}
        </section>
      )}

      {/* Probability of Backtest Overfitting. Sits last of the three because
          it judges the whole selection procedure rather than any single run. */}
      {ov?.computable && (
        <section className="panel rounded-2xl p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h3 className="text-sm font-bold text-text-primary">
                Probability of backtest overfitting
              </h3>
              <p className="text-xs text-text-muted mt-1 max-w-lg leading-relaxed">
                The split above is one split. This one cuts the period into{" "}
                {ov.n_splits} blocks and tries all {ov.n_combinations} balanced
                ways of splitting them, each time picking the best combination on
                one half and checking where it lands on the other.
              </p>
            </div>
            <span
              className={`text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full border whitespace-nowrap ${pboVerdict.tone}`}
            >
              {pboVerdict.label}
            </span>
          </div>

          <p className="text-xs text-text-muted mt-3 mb-5 leading-relaxed">
            {pboVerdict.blurb}
          </p>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-bg border border-border rounded-xl p-4">
              <p className="eyebrow mb-1.5">PBO</p>
              <p
                className={`font-mono text-lg ${
                  ov.pbo >= 0.5
                    ? "text-danger"
                    : ov.pbo >= 0.35
                      ? "text-warning"
                      : "text-success"
                }`}
              >
                {pct(ov.pbo)}
              </p>
              <p className="text-[11px] text-text-faint mt-1">50% is a coin flip</p>
            </div>
            <div className="bg-bg border border-border rounded-xl p-4">
              <p className="eyebrow mb-1.5">Loses money</p>
              <p
                className={`font-mono text-lg ${
                  ov.probability_of_loss >= 0.5 ? "text-danger" : "text-text-primary"
                }`}
              >
                {pct(ov.probability_of_loss)}
              </p>
              <p className="text-[11px] text-text-faint mt-1">of splits, out-of-sample</p>
            </div>
            <div className="bg-bg border border-border rounded-xl p-4">
              <p className="eyebrow mb-1.5">Median Sharpe</p>
              <p className="font-mono text-lg text-text-primary">
                {num(ov.median_is_sharpe)}
                <span className="text-text-faint"> → </span>
                <span
                  className={
                    ov.median_oos_sharpe < ov.median_is_sharpe
                      ? "text-danger"
                      : "text-success"
                  }
                >
                  {num(ov.median_oos_sharpe)}
                </span>
              </p>
              <p className="text-[11px] text-text-faint mt-1">in-sample → out</p>
            </div>
            <div className="bg-bg border border-border rounded-xl p-4">
              <p className="eyebrow mb-1.5">Degradation</p>
              <p
                className={`font-mono text-lg ${
                  ov.degradation_slope < 0 ? "text-danger" : "text-success"
                }`}
              >
                {num(ov.degradation_slope)}
              </p>
              <p className="text-[11px] text-text-faint mt-1">slope, OOS on IS</p>
            </div>
          </div>

          {/* The slope is the number most worth explaining, and it is the one
              nobody would interpret unaided. */}
          {ov.degradation_slope < 0 && (
            <p className="text-xs text-warning mt-4 leading-relaxed">
              The slope is negative, which is the damning case: across these
              splits, a <em>better</em> in-sample score predicted a{" "}
              <em>worse</em> out-of-sample one. Tuning harder on this data made
              results worse, not better.
            </p>
          )}

          <p className="text-xs text-text-faint mt-4 leading-relaxed">
            These splits are drawn from blocks spread across the whole period, so
            both halves cover the same years. That is deliberate — it isolates
            whether selection works at all — but it means this test cannot see a
            regime change. The chronological split above is what catches that.
          </p>
        </section>
      )}

      <section className="panel rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 mb-1 flex-wrap">
          <div>
            <h3 className="text-sm font-bold text-text-primary">Signal timing test</h3>
            <p className="text-xs text-text-muted mt-1 max-w-lg leading-relaxed">
              The position series was randomly reordered {pm.trials} times, keeping the exact same
              number of long, short, and flat days. If real timing beats the shuffles, the entries
              are doing work that market exposure alone would not.
            </p>
          </div>
          <span
            className={`text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full border whitespace-nowrap ${
              pm.significant
                ? "text-success border-success/30 bg-success/10"
                : "text-danger border-danger/30 bg-danger/10"
            }`}
          >
            {pm.significant ? "Significant" : "Not significant"}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 mb-5">
          <Stat label="Real Sharpe" value={num(pm.real_sharpe)} tone="text-accent" />
          <Stat label="Percentile" value={`${(pm.percentile * 100).toFixed(1)}%`} />
          <Stat
            label="p-value"
            value={pm.p_value.toFixed(3)}
            tone={pm.significant ? "text-success" : "text-danger"}
          />
          <Stat label="Random mean" value={num(pm.random_sharpe_mean)} tone="text-text-muted" />
        </div>

        {/* Where the real result sits among the shuffled ones */}
        <div>
          <div className="relative h-2 bg-bg border border-border rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-border"
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
                  className="absolute text-[10px] font-mono text-accent whitespace-nowrap"
                  style={{ left: `${at}%`, transform: `translateX(${shift})` }}
                >
                  ▲ your strategy
                </span>
              );
            })()}
          </div>
          <p className="text-[11px] text-text-muted mt-2 leading-relaxed">
            {pm.significant
              ? `Real timing beat ${(pm.percentile * 100).toFixed(0)}% of random reorderings — unlikely to be chance (p = ${pm.p_value.toFixed(3)}).`
              : `Random timing matched or beat this result ${(pm.p_value * 100).toFixed(0)}% of the time. The returns look like market exposure rather than signal quality.`}
          </p>
        </div>
      </section>

      <p className="text-[11px] text-text-muted leading-relaxed">
        These checks are diagnostic and are not saved to your run history. A strategy can pass the
        timing test and still fail walk-forward — that combination means the approach has signal but
        the specific parameters were tuned too tightly.
      </p>
    </div>
  );
}
