/**
 * Build-time render of the public pages, for crawlers that never run the app.
 *
 * scripts/prerender.mjs loads this through Vite after `vite build` and writes
 * each page's markup into its HTML shell. It is the app's own Layout, rendered
 * as a signed-out reader with no API: anything that waits on the network
 * (Pricing's plans) is in its loading state, and charts that measure their
 * width draw nothing. main.jsx then replaces the copy with the live page.
 */
import React from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { LazyMotion, domAnimation } from "motion/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthContext } from "./context/AuthContext";
import { ToastContext } from "./context/ToastContext";
import { StillMotion } from "./components/motion";
import { Layout, PRELOAD } from "./App.jsx";
import { PAGE_META } from "./lib/pageMeta.js";

const SIGNED_OUT = {
  user: null,
  userProfile: null,
  loading: false,
  emailVerified: false,
  refreshUser: async () => false,
  logout: async () => {},
};

/** Every page the build renders, keyed as in PRELOAD; the landing page is `/`. */
export const PAGES = { landing: "/", ...Object.fromEntries(Object.entries(PAGE_META).map(([k, m]) => [k, m.path])) };

export async function render(name) {
  await PRELOAD[name]();
  // Radix and motion call useLayoutEffect, which React warns about on every
  // server render. The warning is about hydration mismatches, and this copy is
  // replaced, never hydrated (main.jsx), so it is noise here.
  const error = console.error;
  console.error = (msg, ...rest) => {
    if (typeof msg === "string" && msg.includes("useLayoutEffect does nothing on the server")) return;
    error(msg, ...rest);
  };
  try {
    return renderPage(name);
  } finally {
    console.error = error;
  }
}

function renderPage(name) {
  return renderToString(
    <LazyMotion features={domAnimation} strict>
      <StillMotion.Provider value={true}>
        <StaticRouter location={PAGES[name]}>
          <AuthContext.Provider value={SIGNED_OUT}>
            <ToastContext.Provider value={{ showToast() {} }}>
              <TooltipProvider delayDuration={200}>
                <Layout />
              </TooltipProvider>
            </ToastContext.Provider>
          </AuthContext.Provider>
        </StaticRouter>
      </StillMotion.Provider>
    </LazyMotion>
  );
}
