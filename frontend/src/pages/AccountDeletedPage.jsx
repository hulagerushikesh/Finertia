import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SUPPORT_EMAIL } from "../lib/contact";

/** Where a user lands after deleting their account from Profile. */
export default function AccountDeletedPage() {
  const { user, logout } = useAuth();
  const deleted = useLocation().state?.deleted;

  // The Auth user is already gone on the server; this clears the browser's
  // copy of the session (and the kept workspace). Only when arriving from a
  // deletion, so a signed-in visit to this URL signs nobody out.
  // Arrives from the bottom of the long Profile page; start at the top.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    if (deleted && user) logout();
  }, [deleted, user, logout]);

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4">
      <div className="max-w-sm">
        <Badge variant="faint" size="lg">Account deleted</Badge>
        <h1 className="font-display text-display-md font-semibold text-foreground mt-6 text-balance">
          Your account is deleted.
        </h1>
        <p className="text-sm text-graphite mt-3 leading-relaxed">
          Your profile, your saved runs and your sign-in are gone, and you are signed out. You can
          register again with the same email address at any time; it starts a new, empty account.
          Copies inside our database backups expire on their own within 14 weeks.
        </p>
        <p className="text-sm text-graphite mt-3 leading-relaxed">
          Questions: <a className="underline underline-offset-2" href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
        </p>
        <Button asChild className="mt-6">
          <Link to="/">Back to home</Link>
        </Button>
      </div>
    </div>
  );
}
