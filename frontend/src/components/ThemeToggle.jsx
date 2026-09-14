import React, { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Light is the designed default — a manuscript lives on paper — and dark is
 * the same document read at night. One button, state carried by the icon of
 * what you would switch *to*, the way every other control here names its
 * action rather than its state.
 */
export default function ThemeToggle({ className }) {
  const { resolvedTheme, setTheme } = useTheme();
  // next-themes resolves on the client; render nothing theme-specific until
  // then so the icon never flips on hydration.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const dark = mounted && resolvedTheme === "dark";
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(dark ? "light" : "dark")}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      className={className}
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
