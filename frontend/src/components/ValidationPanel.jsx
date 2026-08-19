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

export default function ValidationPanel({ data }) {
  if (!data) return null;

  const { walk_forward: wf, permutation: pm } = data;
  const verdict = WF_VERDICT[wf.verdict] || WF_VERDICT.inconclusive;

  return (
    <div className="flex flex-col gap-5">
      {/* ── Walk-forward ── */}
      <section className="panel rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 mb-1 flex-wrap">
          <div>
            <h3 className="text-sm font-bold text-text-primary">Walk-forward validation</h3>
            <p className="text-xs text-text-muted mt-1 max-w-lg leading-relaxed">
              Parameters were optimised on the first {Math.round((wf.in_sample_bars /
                (wf.in_sample_bars + wf.out_of_sample_bars)) * 100)}% of the period, then scored on
              the remainder. Only the out-of-sample column is evidence.
            </p>
          </div>
          <span
            className={`text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full border whitespace-nowrap ${verdict.tone}`}
          >
            {verdict.label}
          </span>
        </div>

        <p className="text-xs text-text-muted mt-3 mb-5 leading-relaxed">{verdict.blurb}</p>

        <div className="flex flex-wrap gap-x-6 gap-y-2 text-[11px] font-mono text-text-muted mb-5">
          <span>split <span className="text-text-primary">{wf.split_date}</span></span>
          <span>{wf.in_sample_bars} in-sample bars</span>
          <span>{wf.out_of_sample_bars} out-of-sample bars</span>
          <span>{wf.combinations_tested} combinations tested</span>
        </div>

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
