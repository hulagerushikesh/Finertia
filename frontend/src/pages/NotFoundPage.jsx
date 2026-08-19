import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function NotFoundPage() {
  const { user } = useAuth();
  const home = user ? "/dashboard" : "/";

  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <p className="font-mono text-5xl font-bold text-accent/30 tracking-tight">404</p>
        <h1 className="text-xl font-bold text-text-primary mt-4">Page not found</h1>
        <p className="text-sm text-text-muted mt-2 leading-relaxed">
          That URL doesn't match anything in Finertia. It may have moved, or the link
          may be mistyped.
        </p>
        <Link
          to={home}
          className="btn-primary mt-6 px-5 py-2.5 text-sm"
        >
          {user ? "Back to dashboard" : "Back to home"}
        </Link>
      </div>
    </div>
  );
}
