import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageSpinner } from "./Spinner";
import VerifyEmailBanner from "./VerifyEmailBanner";
import { authPath } from "../utils/returnTo";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <PageSpinner />
    );
  }

  // Remember where they were going, so signing in lands there (utils/returnTo.js).
  if (!user) return <Navigate to={authPath("/login", location.pathname + location.search)} replace />;

  // The banner lives here rather than in App so it appears on the pages a
  // signed-in user actually works on, and never on the public marketing pages.
  return (
    <>
      <VerifyEmailBanner />
      {children}
    </>
  );
}
