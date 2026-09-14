import React, { useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

function posLabel(pos) {
  if (pos === 1) return { text: "Long", cls: "text-gain border-gain/40" };
  if (pos === -1) return { text: "Short", cls: "text-loss border-loss/40" };
  return { text: "Flat", cls: "text-graphite border-border" };
}

/** Page controls shared by every paginated table. */
export function Pager({ page, totalPages, onPage, className }) {
  if (totalPages <= 1) return null;
  return (
    <div className={cn("flex items-center justify-between", className)}>
      <Button variant="ghost" size="sm" onClick={() => onPage(Math.max(0, page - 1))} disabled={page === 0}>
        ← Previous
      </Button>
      <span className="text-xs font-mono text-graphite">
        {page + 1} / {totalPages}
      </span>
      <Button
        variant="ghost" size="sm"
        onClick={() => onPage(Math.min(totalPages - 1, page + 1))}
        disabled={page === totalPages - 1}
      >
        Next →
      </Button>
    </div>
  );
}

export default function TradesTable({ trades }) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(trades.length / PAGE_SIZE);
  const slice = trades.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <section className="sheet overflow-hidden">
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <h2 className="font-display text-lg font-medium text-foreground">Trade log</h2>
        <span className="text-2xs font-mono text-graphite">{trades.length} entries</span>
      </div>

      <div className="overflow-x-auto">
        <Table className="text-xs font-mono">
          <TableHeader>
            <TableRow>
              <TableHead className="pl-5">Date</TableHead>
              <TableHead>Position</TableHead>
              <TableHead className="text-right">Daily return</TableHead>
              <TableHead className="text-right pr-5">Equity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {slice.map((row, i) => {
              const { text, cls } = posLabel(row.position);
              const retColor =
                row.daily_return > 0 ? "text-gain" : row.daily_return < 0 ? "text-loss" : "text-graphite";
              return (
                <TableRow key={i}>
                  <TableCell className="pl-5 text-graphite">{row.date}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={cn("font-mono text-tick px-1.5 py-0 rounded-sm", cls)}>
                      {text}
                    </Badge>
                  </TableCell>
                  <TableCell className={cn("text-right", retColor)}>
                    {(row.daily_return * 100).toFixed(3)}%
                  </TableCell>
                  <TableCell className="text-right pr-5 text-foreground">{row.equity.toFixed(4)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Pager page={page} totalPages={totalPages} onPage={setPage} className="px-3 py-2 border-t border-border" />
    </section>
  );
}
