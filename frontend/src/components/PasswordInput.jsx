import React, { useState } from "react";

/**
 * A password field you can read back.
 *
 * Masking protects against someone reading over a shoulder; it does nothing
 * about the far more common failure, which is typing the wrong thing and being
 * told only after a round-trip that the credentials were wrong. The toggle
 * costs nothing and removes a whole class of retry.
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
      <input
        id={id}
        className="field-input pr-16 py-2.5"
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
        // The label states the action, not the state — the same rule the rest
        // of the interface follows for buttons.
        aria-label={shown ? "Hide password" : "Show password"}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-2xs font-mono uppercase tracking-wider text-text-faint hover:text-accent transition-colors px-1.5 py-1 rounded"
      >
        {shown ? "Hide" : "Show"}
      </button>
    </div>
  );
}
