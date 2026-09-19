import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from "motion/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import ProtectedRoute from "./components/ProtectedRoute";
import PublicOnlyRoute from "./components/PublicOnlyRoute";
import AdminRoute from "./components/AdminRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import { EASE_OUT } from "./components/motion";

// Eager: the pages a first-time visitor actually lands on.
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import NotFoundPage from "./pages/NotFoundPage";
import PricingPage from "./pages/PricingPage";

// Public marketing pages, lazy because neither is on the critical path to the
// landing page but both pull in charts or long copy.
const DemoPage = lazy(() => import("./pages/DemoPage"));
const DocsPage = lazy(() => import("./pages/DocsPage"));
const SupportPage = lazy(() => import("./pages/SupportPage"));

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
  const off = useReducedMotion();
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

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem storageKey="finertia-theme">
      {/* `m` + domAnimation instead of `motion`: this interface only ever
          animates opacity/transform, and the full `motion` component pulls
          ~40 kB gz of layout/drag/gesture code onto the landing page. `strict`
          throws if a `motion.*` element sneaks back in. */}
      <LazyMotion features={domAnimation} strict>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <TooltipProvider delayDuration={200}>
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
                          <Route path="/support" element={<SupportPage />} />
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
            </TooltipProvider>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
      </LazyMotion>
    </ThemeProvider>
  );
}
