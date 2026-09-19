import React from "react";
import { Label } from "@/components/ui/label";
import { Rise } from "./motion";

/**
 * The frame around sign-in, registration, and password reset.
 *
 * A form on the left, and on the right — from `lg` up — a margin note saying
 * what the account is actually for. On a phone the form is the whole job.
 */
export default function AuthShell({ title, subtitle, aside, children }) {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-4xl grid lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] gap-10 lg:gap-16 items-center">
        <Rise className="w-full max-w-sm mx-auto lg:mx-0">
          <h1 className="font-display text-display-sm font-semibold tracking-tight text-foreground mb-2 text-balance">
            {title}
          </h1>
          <p className="text-sm text-graphite mb-7 leading-relaxed">{subtitle}</p>
          {children}
        </Rise>

        {aside && (
          <Rise delay={0.08} className="hidden lg:block border-l border-border pl-12">
            {aside}
          </Rise>
        )}
      </div>
    </div>
  );
}

/** Consistent label + field pairing for the auth forms. */
export function AuthField({ label, htmlFor, action, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <Label htmlFor={htmlFor} className="eyebrow">
          {label}
        </Label>
        {action}
      </div>
      {children}
    </div>
  );
}
