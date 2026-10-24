import { lazy } from "react";

/**
 * React.lazy that can be loaded ahead of its first render.
 *
 * Once `preload()` has resolved, the page renders without suspending: the
 * factory hands React.lazy a thenable that settles synchronously, and React
 * reads that as already loaded. main.jsx relies on it so a pre-rendered page
 * is replaced by the same page rather than by the loading skeleton, and the
 * build-time render relies on it because renderToString cannot wait.
 */
export function lazyPage(load) {
  let loaded = null;
  const Page = lazy(() => (loaded ? { then: (resolve) => resolve(loaded) } : load()));
  Page.preload = () =>
    load().then((mod) => {
      loaded = mod;
      return mod;
    });
  return Page;
}
