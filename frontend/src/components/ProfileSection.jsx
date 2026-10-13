import React from "react";

/** A titled sheet on the Profile page, with the title set in the margin from lg up. */
export default function ProfileSection({ title, description, children }) {
  return (
    <section className="sheet p-6 grid lg:grid-cols-[11rem_minmax(0,1fr)] gap-x-8 gap-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-foreground leading-tight">{title}</h2>
        {description && <p className="text-xs text-graphite mt-1.5 leading-relaxed">{description}</p>}
      </div>
      <div>{children}</div>
    </section>
  );
}
