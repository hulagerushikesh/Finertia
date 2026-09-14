import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageSpinner } from "./Spinner";
import VerifyEmailBanner from "./VerifyEmailBanner";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <PageSpinner />
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  // The banner lives here rather than in App so it appears on the pages a
  // signed-in user actually works on, and never on the public marketing pages.
  return (
    <>
      <VerifyEmailBanner />
      {children}
    </>
  );
}
