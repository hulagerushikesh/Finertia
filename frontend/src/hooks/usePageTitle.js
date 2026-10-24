import { useEffect } from "react";
import { DEFAULT_TITLE, PAGE_META } from "../lib/pageMeta";

/**
 * Sets the tab title to the page's entry in PAGE_META while it is shown, and
 * puts index.html's title back after. Not "whatever was there before": under
 * StrictMode the effect runs twice, and the second run would remember its own
 * title as the one to restore.
 */
export function usePageTitle(name) {
  useEffect(() => {
    document.title = PAGE_META[name].title;
    return () => {
      document.title = DEFAULT_TITLE;
    };
  }, [name]);
}
