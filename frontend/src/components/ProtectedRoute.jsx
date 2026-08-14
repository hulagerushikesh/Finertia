import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import VerifyEmailBanner from "./VerifyEmailBanner";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
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
