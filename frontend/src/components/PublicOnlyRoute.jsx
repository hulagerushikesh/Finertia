import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageSpinner } from "./Spinner";

/**
 * The inverse of ProtectedRoute: sign-in and register have nothing to offer
 * someone who is already signed in, so they go straight to the workspace.
 * Waits for the auth check like ProtectedRoute does, so a signed-in user
 * never sees the form flash before the redirect.
 */
export default function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <PageSpinner />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}
