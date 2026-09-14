import React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { TableCell, TableRow } from "@/components/ui/table";

/**
 * Placeholder table row shown while data loads. `widths` sets each cell's
 * fill width so the skeleton echoes the shape of the real row.
 */
export default function SkeletonRow({ columns = 4, widths }) {
  const fills = widths || Array.from({ length: columns }, () => "70%");
  return (
    <TableRow>
      {fills.map((w, i) => (
        <TableCell key={i}>
          <Skeleton className="h-3" style={{ width: w }} />
        </TableCell>
      ))}
    </TableRow>
  );
}

export function SkeletonRows({ rows = 5, columns = 4, widths }) {
  return (
    <>
      {Array.from({ length: rows }, (_, i) => (
        <SkeletonRow key={i} columns={columns} widths={widths} />
      ))}
    </>
  );
}
