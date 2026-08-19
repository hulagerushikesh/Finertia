import React from "react";

const shimmer =
  "bg-[linear-gradient(90deg,#192133_0%,#28334A_50%,#192133_100%)] bg-[length:800px_100%] animate-shimmer rounded";

/**
 * Placeholder table row shown while data loads.
 *
 * `widths` sets each cell's fill width so the skeleton echoes the shape of the
 * real row rather than reading as a block of identical bars.
 */
export default function SkeletonRow({ columns = 4, widths }) {
  const fills = widths || Array.from({ length: columns }, () => "70%");

  return (
    <tr className="border-b border-border">
      {fills.map((w, i) => (
        <td key={i} className="px-4 py-3.5">
          <div className={`h-3 ${shimmer}`} style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

/** Convenience wrapper: N skeleton rows with the same column shape. */
export function SkeletonRows({ rows = 5, columns = 4, widths }) {
  return (
    <>
      {Array.from({ length: rows }, (_, i) => (
        <SkeletonRow key={i} columns={columns} widths={widths} />
      ))}
    </>
  );
}
