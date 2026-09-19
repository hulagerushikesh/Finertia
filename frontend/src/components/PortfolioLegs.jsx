import React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

const pct = (v) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)}%`);

/**
 * Per-holding breakdown: how much of the book each name held, what it added
 * to the total, and how it did on its own. The attribution is arithmetic, so
 * the contributions add up to the whole.
 */
export default function PortfolioLegs({ result }) {
  const { legs, diversification_ratio: dr, weighting } = result;
  const dropped = result.dropped_bars || 0;
  const best = Math.max(...legs.map((l) => l.contribution));
  const worst = Math.min(...legs.map((l) => l.contribution));

  return (
    <div className="flex flex-col gap-5">
      {dropped > 0 && (
        <Alert className="border-l-2 border-l-warn">
          <AlertDescription className="text-xs text-graphite leading-relaxed">
            <strong className="text-foreground">
              {dropped} of {result.longest_ticker_bars} bars dropped — measured on {result.start} →{" "}
              {result.end}.
            </strong>{" "}
            A portfolio can only be measured on days every holding traded, and{" "}
            <strong className="text-foreground">{result.limiting_ticker}</strong> has the shortest
            history of the {legs.length}. Forward-filling the missing bars would invent flat returns
            on days the asset did not trade, which understates volatility and flatters every risk
            metric here.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid sm:grid-cols-3 gap-3">
        <div className="sheet p-4">
          <p className="eyebrow mb-1">Holdings</p>
          <p className="font-display text-3xl font-semibold text-foreground">{legs.length}</p>
        </div>
        <div className="sheet p-4">
          <p className="eyebrow mb-1">Weighting</p>
          <p className="font-display text-xl font-semibold text-foreground mt-1.5">
            {weighting === "inverse_vol" ? "Inverse volatility" : "Equal weight"}
          </p>
        </div>
        <div className="sheet p-4">
          <p className="eyebrow mb-1">Diversification</p>
          <p className="font-display text-3xl font-semibold text-foreground">
            {dr === null || dr === undefined ? "—" : dr.toFixed(2)}
          </p>
          <p className="text-xs text-faint mt-1 leading-relaxed">
            {dr === null || dr === undefined
              ? "Undefined — the portfolio had no volatility to measure."
              : dr > 1.05
                ? "Above 1.0: the holdings' moves partly cancel."
                : "Near 1.0: these names move as one, so holding several bought little."}
          </p>
        </div>
      </div>

      <section className="sheet overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-5">Holding</TableHead>
                <TableHead className="text-right">Avg weight</TableHead>
                <TableHead className="text-right">Contribution</TableHead>
                <TableHead className="text-right">Standalone return</TableHead>
                <TableHead className="text-right">Sharpe</TableHead>
                <TableHead className="text-right pr-5">Max DD</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {legs.map((leg) => (
                <TableRow key={leg.ticker} className="font-mono text-xs">
                  <TableCell className="pl-5 font-medium text-foreground">{leg.ticker}</TableCell>
                  <TableCell className="text-right text-graphite">{(leg.avg_weight * 100).toFixed(1)}%</TableCell>
                  <TableCell
                    className={cn(
                      "text-right",
                      leg.contribution === best
                        ? "text-gain font-medium"
                        : leg.contribution === worst
                          ? "text-loss font-medium"
                          : leg.contribution >= 0
                            ? "text-gain"
                            : "text-loss",
                    )}
                  >
                    {leg.contribution >= 0 ? "+" : ""}
                    {(leg.contribution * 100).toFixed(2)}%
                  </TableCell>
                  <TableCell className={cn("text-right", leg.metrics?.total_return >= 0 ? "text-gain" : "text-loss")}>
                    {pct(leg.metrics?.total_return)}
                  </TableCell>
                  <TableCell className="text-right text-foreground">{leg.metrics?.sharpe_ratio?.toFixed(2) ?? "—"}</TableCell>
                  <TableCell className="text-right pr-5 text-loss">{pct(leg.metrics?.max_drawdown)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-faint px-5 py-3 border-t border-border leading-relaxed">
          Contribution is each holding's additive share of the portfolio result, so the column sums
          to the total. Standalone return is what that leg did on its own at full size — the two
          differ because a holding is only ever a fraction of the book.
        </p>
      </section>
    </div>
  );
}
