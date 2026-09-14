import React, { useState } from "react";
import { Input } from "@/components/ui/input";

/**
 * A password field you can read back. Masking protects against a shoulder;
 * it does nothing about the far more common failure, which is typing the
 * wrong thing and being told after a round-trip.
 */
export default function PasswordInput({
  value,
  onChange,
  onKeyDown,
  placeholder,
  autoComplete = "current-password",
  id,
}) {
  const [shown, setShown] = useState(false);

  return (
    <div className="relative">
      <Input
        id={id}
        className="pr-16"
        type={shown ? "text" : "password"}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        autoComplete={autoComplete}
      />
      <button
        type="button"
        onClick={() => setShown((s) => !s)}
        aria-label={shown ? "Hide password" : "Show password"}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-2xs font-mono uppercase tracking-wider text-faint hover:text-pencil transition-colors px-1.5 py-1 rounded-sm"
      >
        {shown ? "Hide" : "Show"}
      </button>
    </div>
  );
}
