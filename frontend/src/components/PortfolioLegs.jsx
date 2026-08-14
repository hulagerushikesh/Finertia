import React from "react";

const pct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)}%`;

/**
 * Per-holding breakdown: how much of the book each name held, what it added to
 * the total, and how it did on its own.
 *
 * The attribution is arithmetic, so the contributions add up to the whole and
 * can be compared against each other. It is not a claim that a leg standalone
 * returned that much — the standalone column is there for exactly that.
 */
export default function PortfolioLegs({ result }) {
  const { legs, diversification_ratio: dr, weighting } = result;

  // Only flag real loss of history. Comparing against the requested start date
  // would fire whenever it landed on a weekend or a holiday, and a warning that
  // shows on nearly every run is one nobody reads.
  const dropped = result.dropped_bars || 0;

  const best = Math.max(...legs.map((l) => l.contribution));
  const worst = Math.min(...legs.map((l) => l.contribution));

  return (
    <div className="flex flex-col gap-5">
      {dropped > 0 && (
        <div className="bg-warning/10 border border-warning/30 text-warning text-xs rounded-xl px-4 py-3 leading-relaxed">
          <strong>
            {dropped} of {result.longest_ticker_bars} bars dropped — measured on{" "}
            {result.start} → {result.end}.
          </strong>{" "}
          A portfolio can only be measured on days every holding traded, and{" "}
          <strong>{result.limiting_ticker}</strong> has the shortest history of
          the {legs.length}. Forward-filling the missing bars would invent flat
          returns on days the asset did not trade, which understates volatility
          and flatters every risk metric here.
        </div>
      )}

      <div className="grid sm:grid-cols-3 gap-3">
        <div className="bg-surface border border-border rounded-xl p-4">
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Holdings</p>
          <p className="text-2xl font-mono font-bold text-text-primary">{legs.length}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Weighting</p>
          <p className="text-sm font-mono text-text-primary mt-2">
            {weighting === "inverse_vol" ? "Inverse volatility" : "Equal weight"}
          </p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
            Diversification
          </p>
          <p className="text-2xl font-mono font-bold text-text-primary">
            {dr === null || dr === undefined ? "—" : dr.toFixed(2)}
          </p>
          <p className="text-xs text-text-muted/70 mt-1 leading-relaxed">
            {dr === null || dr === undefined
              ? "Undefined — the portfolio had no volatility to measure."
              : dr > 1.05
                ? "Above 1.0: the holdings' moves partly cancel."
                : "Near 1.0: these names move as one, so holding several bought little."}
          </p>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-muted text-xs uppercase tracking-wider">
                <th className="text-left px-5 py-3">Holding</th>
                <th className="text-right px-5 py-3">Avg Weight</th>
                <th className="text-right px-5 py-3">Contribution</th>
                <th className="text-right px-5 py-3">Standalone Return</th>
                <th className="text-right px-5 py-3">Sharpe</th>
                <th className="text-right px-5 py-3">Max DD</th>
              </tr>
            </thead>
            <tbody>
              {legs.map((leg) => (
                <tr key={leg.ticker} className="border-b border-border/50 last:border-0">
                  <td className="px-5 py-3 font-mono font-semibold text-text-primary">
                    {leg.ticker}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-xs text-text-muted">
                    {(leg.avg_weight * 100).toFixed(1)}%
                  </td>
                  <td
                    className={`px-5 py-3 text-right font-mono text-xs ${
                      leg.contribution === best
                        ? "text-success font-bold"
                        : leg.contribution === worst
                          ? "text-danger font-bold"
                          : leg.contribution >= 0
                            ? "text-success"
                            : "text-danger"
                    }`}
                  >
                    {leg.contribution >= 0 ? "+" : ""}
                    {(leg.contribution * 100).toFixed(2)}%
                  </td>
                  <td
                    className={`px-5 py-3 text-right font-mono text-xs ${
                      leg.metrics?.total_return >= 0 ? "text-success" : "text-danger"
                    }`}
                  >
                    {pct(leg.metrics?.total_return)}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-xs text-text-primary">
                    {leg.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-xs text-danger">
                    {pct(leg.metrics?.max_drawdown)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-text-muted/70 px-5 py-3 border-t border-border leading-relaxed">
          Contribution is each holding's additive share of the portfolio result,
          so the column sums to the total. Standalone return is what that leg did
          on its own at full size — the two differ because a holding is only ever
          a fraction of the book.
        </p>
      </div>
    </div>
  );
}
