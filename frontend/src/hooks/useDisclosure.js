import { useState } from "react";

/**
 * Open/closed state that survives a reload.
 *
 * Used for the folds that hide most of a page — the validation working, the
 * secondary charts — so a reader who always opens them never has to again.
 * localStorage can throw in private mode; the toggle still works for the
 * page, it just forgets.
 */
export default function useDisclosure(storageKey, initial = false) {
  const [open, setOpenState] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      return stored === null ? initial : stored === "open";
    } catch {
      return initial;
    }
  });
  const setOpen = (next) => {
    setOpenState(next);
    try {
      localStorage.setItem(storageKey, next ? "open" : "closed");
    } catch {
      /* private mode */
    }
  };
  return [open, setOpen, () => setOpen(!open)];
}
