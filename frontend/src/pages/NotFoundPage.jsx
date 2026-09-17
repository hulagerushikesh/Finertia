import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button } from "@/components/ui/button";
import Stamp from "../components/Stamp";

export default function NotFoundPage() {
  const { user } = useAuth();
  const home = user ? "/dashboard" : "/";

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4">
      <div className="max-w-sm">
        <Stamp tone="faint" size="lg" delay={0.05}>404</Stamp>
        <h1 className="font-display text-display-md font-medium text-foreground mt-6 text-balance">
          Nothing at this address.
        </h1>
        <p className="text-sm text-graphite mt-3 leading-relaxed">
          That URL doesn't match anything in Finertia. It may have moved, or the link may be mistyped.
        </p>
        <Button asChild className="mt-6">
          <Link to={home}>{user ? "Back to the workspace" : "Back to home"}</Link>
        </Button>
      </div>
    </div>
  );
}
