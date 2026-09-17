import React from "react";
import { cn } from "@/lib/utils";

/** The one loading indicator. Pencil-coloured arc, 16px unless told otherwise. */
const SIZES = { 3: "size-3", 4: "size-4", 5: "size-5", 8: "size-8" };

export default function Spinner({ className, size = 4 }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-block rounded-full border-2 border-current border-t-transparent animate-spin",
        SIZES[size] || SIZES[4],
        className,
      )}
    />
  );
}

export function PageSpinner() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]" aria-busy="true">
      <Spinner size={8} className="text-pencil" />
    </div>
  );
}
