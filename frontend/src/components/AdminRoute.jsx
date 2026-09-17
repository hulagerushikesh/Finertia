import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageSpinner } from "./Spinner";

export default function AdminRoute({ children }) {
  const { user, userProfile, loading } = useAuth();

  if (loading) {
    return (
      <PageSpinner />
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (userProfile?.role !== "admin") {
    return <Navigate to="/dashboard" replace state={{ toast: "Access denied." }} />;
  }

  return children;
}
