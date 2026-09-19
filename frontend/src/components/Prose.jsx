import React from "react";
import { cn } from "@/lib/utils";

/**
 * The document parts shared by the Docs and Support pages: a titled section
 * with an anchor, a term set like a glossary entry, and a margin layout that
 * puts the term's name in the margin the way a printed manual does.
 */
export function DocSection({ id, title, children }) {
  return (
    <section id={id} className="scroll-mt-20 grid lg:grid-cols-[11rem_minmax(0,1fr)] gap-x-10 gap-y-3">
      <h2 className="font-display text-xl font-semibold text-foreground lg:text-right lg:pt-0.5 text-balance">
        {title}
      </h2>
      <div className="flex flex-col gap-3 text-[0.95rem] text-graphite leading-relaxed max-w-prose">
        {children}
      </div>
    </section>
  );
}

export function Term({ name, children, className }) {
  return (
    <div className={cn("border-l-2 border-pencil/40 pl-4 py-0.5", className)}>
      <p className="text-foreground font-medium text-sm mb-1">{name}</p>
      <div className="text-sm text-graphite leading-relaxed flex flex-col gap-2">{children}</div>
    </div>
  );
}

export function DocHeader({ eyebrow, title, children }) {
  return (
    <header className="max-w-2xl mb-12">
      {eyebrow && <p className="eyebrow mb-4">{eyebrow}</p>}
      <h1 className="font-display text-display-md font-semibold tracking-tight text-foreground text-balance">
        {title}
      </h1>
      {children && <p className="text-graphite leading-relaxed mt-4">{children}</p>}
    </header>
  );
}
