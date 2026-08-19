import React from "react";

/**
 * The frame around sign-in, registration, and password reset.
 *
 * These three pages were a card centred in an otherwise empty screen, which is
 * where most products put them and where they say the least. The right column
 * uses the space to say what the account is actually for — visible from `sm`
 * up, because on a phone the form is the whole job and anything beside it is
 * something to scroll past.
 */
export default function AuthShell({ title, subtitle, aside, children }) {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-4xl grid lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] gap-10 lg:gap-16 items-center">
        <div className="w-full max-w-sm mx-auto lg:mx-0 animate-rise-in">
          <h1 className="text-2xl font-bold tracking-tight text-text-primary mb-1.5">
            {title}
          </h1>
          <p className="text-sm text-text-muted mb-7 leading-relaxed">{subtitle}</p>
          {children}
        </div>

        {aside && (
          <div className="hidden lg:block border-l border-border pl-16">{aside}</div>
        )}
      </div>
    </main>
  );
}

/** Consistent label + field pairing for the auth forms. */
export function AuthField({ label, htmlFor, action, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={htmlFor} className="eyebrow">
          {label}
        </label>
        {action}
      </div>
      {children}
    </div>
  );
}
