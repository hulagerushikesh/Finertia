import React, { Suspense, lazy, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AnimatePresence, LazyMotion, domAnimation, m } from "motion/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import ProtectedRoute from "./components/ProtectedRoute";
import PublicOnlyRoute from "./components/PublicOnlyRoute";
import AdminRoute from "./components/AdminRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import { EASE_OUT, StillMotion, useMotionOff } from "./components/motion";
import { lazyPage } from "./lib/lazyPage";
import { feature } from "./lib/features";
import { STOCKS } from "./lib/stockMeta";

// Eager: the pages a first-time visitor actually lands on.
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import NotFoundPage from "./pages/NotFoundPage";
import PricingPage from "./pages/PricingPage";

// Public marketing pages, lazy because none is on the critical path to the
// landing page and each pulls in charts or long copy.
const DemoPage = lazyPage(() => import("./pages/DemoPage"));
const DocsPage = lazyPage(() => import("./pages/DocsPage"));
const SupportPage = lazyPage(() => import("./pages/SupportPage"));
const AccountDeletedPage = lazy(() => import("./pages/AccountDeletedPage"));
const WriteupPage = lazyPage(() => import("./pages/WriteupPage"));
const StrategyPage = lazyPage(() => import("./pages/StrategyPage"));
const LearnPage = lazyPage(() => import("./pages/LearnPage"));
const StockPage = lazyPage(() => import("./pages/StockPage"));

/**
 * What to load before the first render of each page the build pre-renders
 * (scripts/prerender.mjs), keyed as in src/lib/pageMeta.js. The landing and
 * pricing pages are in the entry bundle already.
 */
export const PRELOAD = {
  landing: () => Promise.resolve(),
  pricing: () => Promise.resolve(),
  demo: DemoPage.preload,
  docs: DocsPage.preload,
  support: SupportPage.preload,
  writeup: WriteupPage.preload,
  strategies: StrategyPage.preload,
  "strategy-momentum": StrategyPage.preload,
  "strategy-macd": StrategyPage.preload,
  "strategy-bollinger": StrategyPage.preload,
  learn: LearnPage.preload,
  "learn-walk-forward-validation": LearnPage.preload,
  "learn-backtest-overfitting": LearnPage.preload,
  "learn-lookahead-bias": LearnPage.preload,
  "learn-sharpe-ratio": LearnPage.preload,
  "learn-permutation-test": LearnPage.preload,
  stocks: StockPage.preload,
  ...Object.fromEntries(STOCKS.map((s) => [`stock-${s.slug}`, StockPage.preload])),
};

// Lazy: everything behind a login. The charting library alone is ~536 kB, and
// nobody reading the landing page needs it.
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const UserProfilePage = lazy(() => import("./pages/UserProfilePage"));
const AdminLayout = lazy(() => import("./pages/admin/AdminLayout"));
const AdminOverviewPage = lazy(() => import("./pages/admin/AdminOverviewPage"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage"));
const AdminRunsPage = lazy(() => import("./pages/admin/AdminRunsPage"));

function RouteFallback() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-16">
      <div className="h-8 w-48 bg-muted rounded animate-pulse mb-6" />
      <div className="h-64 bg-muted rounded-lg animate-pulse" />
    </div>
  );
}

/**
 * Route transition: a page rises 8px into place over 200ms. Keyed on the
 * pathname only, so a search-string change (the dashboard mirrors its config
 * into the URL on every keystroke) never re-runs it.
 */
function Page({ render }) {
  const location = useLocation();
  const off = useMotionOff();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <m.div
        key={location.pathname}
        initial={off ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={off ? undefined : { opacity: 0, transition: { duration: 0.1 } }}
        transition={{ duration: 0.2, ease: EASE_OUT }}
      >
        {/* The exiting copy must keep rendering the route it was showing —
            without the explicit location, both copies would read the new
            one from context and the transition would show the new page
            twice. */}
        {render(location)}
      </m.div>
    </AnimatePresence>
  );
}

/** Everything inside the providers: the page, its bar and its footer. */
export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      {/* One landmark for every route. */}
      <main id="main" className="flex-1">
        <ErrorBoundary>
          <Suspense fallback={<RouteFallback />}>
            <Page
              render={(location) => (
              <Routes location={location}>
                <Route path="/" element={<LandingPage />} />
                <Route path="/pricing" element={<PricingPage />} />
                <Route path="/demo" element={<DemoPage />} />
                <Route path="/docs" element={<DocsPage />} />
                <Route path="/writeup" element={<WriteupPage />} />
                <Route path="/support" element={<SupportPage />} />
                <Route path="/strategies" element={<StrategyPage />} />
                <Route path="/strategies/:id" element={<StrategyPage />} />
                <Route path="/learn" element={<LearnPage />} />
                <Route path="/learn/:id" element={<LearnPage />} />
                <Route path="/stocks" element={<StockPage />} />
                <Route path="/stocks/:slug" element={<StockPage />} />
                {feature("account-data") && (
                  <Route path="/account-deleted" element={<AccountDeletedPage />} />
                )}
                <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
                <Route path="/register" element={<PublicOnlyRoute><RegisterPage /></PublicOnlyRoute>} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />

                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <DashboardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/history"
                  element={
                    <ProtectedRoute>
                      <HistoryPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <UserProfilePage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin"
                  element={
                    <AdminRoute>
                      <AdminLayout />
                    </AdminRoute>
                  }
                >
                  <Route index element={<Navigate to="/admin/overview" replace />} />
                  <Route path="overview" element={<AdminOverviewPage />} />
                  <Route path="users" element={<AdminUsersPage />} />
                  <Route path="runs" element={<AdminRunsPage />} />
                </Route>

                <Route path="*" element={<NotFoundPage />} />
              </Routes>
              )}
            />
          </Suspense>
        </ErrorBoundary>
      </main>
      <Footer />
    </div>
  );
}

/**
 * `still` is set when the HTML already holds this page, rendered at build
 * time: the first render then replaces it without the entrance motion, so
 * nothing fades out and back in. Later pages animate as usual.
 */
export default function App({ still: initiallyStill = false }) {
  const [still, setStill] = useState(initiallyStill);
  useEffect(() => setStill(false), []);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem storageKey="finertia-theme">
      {/* `m` + domAnimation instead of `motion`: this interface only ever
          animates opacity/transform, and the full `motion` component pulls
          ~40 kB gz of layout/drag/gesture code onto the landing page. `strict`
          throws if a `motion.*` element sneaks back in. */}
      <LazyMotion features={domAnimation} strict>
      <StillMotion.Provider value={still}>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <TooltipProvider delayDuration={200}>
              <Layout />
            </TooltipProvider>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
      </StillMotion.Provider>
      </LazyMotion>
    </ThemeProvider>
  );
}
