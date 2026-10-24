import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageSpinner } from "./Spinner";
import { nextPath } from "../utils/returnTo";

/**
 * The inverse of ProtectedRoute: sign-in and register have nothing to offer
 * someone who is already signed in, so they go straight to the workspace.
 * Waits for the auth check like ProtectedRoute does, so a signed-in user
 * never sees the form flash before the redirect. Registration signs in
 * before it has written the profile, so it holds the redirect until it has
 * (AuthContext's `registering`) and then navigates itself. Either way the
 * destination is the `?next=` the form was opened with, if any.
 */
export default function PublicOnlyRoute({ children }) {
  const { user, loading, registering } = useAuth();
  const location = useLocation();
  if (loading) return <PageSpinner />;
  if (user && !registering) return <Navigate to={nextPath(location.search)} replace />;
  return children;
}
