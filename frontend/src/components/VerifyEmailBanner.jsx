import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { sendEmailVerification } from "firebase/auth";
import { auth } from "../firebase";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";

const DISMISS_KEY = "finertia:hide-verify-banner";
const RESEND_COOLDOWN_S = 60;

function readDismissed() {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    // Storage can be unavailable (private browsing, blocked cookies). Showing
    // the banner is the safe failure — hiding it would lose the only prompt.
    return false;
  }
}

/**
 * Nudges a signed-in user with an unverified address to confirm it.
 *
 * Deliberately a soft prompt and not a gate: nothing in the API requires a
 * verified address, so blocking the dashboard would be inventing a restriction
 * the backend does not enforce. It is dismissible for the session.
 */
export default function VerifyEmailBanner() {
  const { user, emailVerified, refreshUser } = useAuth();
  const { showToast } = useToast();

  const [dismissed, setDismissed] = useState(readDismissed);
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);

  // Firebase rate-limits verification emails per account and reports it as a
  // generic `auth/too-many-requests`. Counting down locally means the user is
  // told to wait rather than handed an error for pressing a button we left
  // enabled.
  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  if (!user || emailVerified || dismissed) return null;

  function handleDismiss() {
    setDismissed(true);
    try {
      sessionStorage.setItem(DISMISS_KEY, "1");
    } catch {
      // Dismissal just won't survive navigation. Not worth surfacing.
    }
  }

  async function handleResend() {
    // `auth.currentUser` can be null even while this component has a user —
    // the context holds the last known value, and a revoked or expired session
    // clears the SDK's copy first. Calling through would throw a raw TypeError
    // about `getIdToken`, which tells the user nothing.
    if (!auth.currentUser) {
      showToast("Your session expired. Sign out and back in.", "error");
      return;
    }
    setBusy(true);
    try {
      await sendEmailVerification(auth.currentUser);
      setCooldown(RESEND_COOLDOWN_S);
      showToast("Verification email sent. Check your inbox.", "success");
    } catch (err) {
      showToast(
        err.code === "auth/too-many-requests"
          ? "Too many requests. Wait a few minutes before trying again."
          : "Couldn't send the email. Try again in a moment.",
        "error"
      );
      // The cooldown deliberately does not start here: nothing was sent, so
      // locking the button for a minute would punish the user for our failure.
    } finally {
      setBusy(false);
    }
  }

  async function handleCheck() {
    if (!auth.currentUser) {
      showToast("Your session expired. Sign out and back in.", "error");
      return;
    }
    setBusy(true);
    try {
      const verified = await refreshUser();
      if (verified) {
        showToast("Email verified. Thanks!", "success");
      } else {
        showToast("Not verified yet — open the link in the email first.", "info");
      }
    } catch {
      showToast("Couldn't check right now. Try again in a moment.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-b border-warning/30 bg-warning/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center gap-x-4 gap-y-2 flex-wrap">
        <p className="text-xs text-text-primary flex-1 min-w-[16rem]">
          <span className="font-semibold">Confirm your email address.</span>{" "}
          <span className="text-text-muted">
            We sent a link to{" "}
            <span className="font-mono">{user.email}</span>. Without it, a
            password reset can't reach you.
          </span>
        </p>

        <div className="flex items-center gap-2">
          <button
            onClick={handleResend}
            disabled={busy || cooldown > 0}
            className="text-xs font-semibold bg-accent hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg transition-colors"
          >
            {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend email"}
          </button>
          <button
            onClick={handleCheck}
            disabled={busy}
            className="text-xs text-text-muted hover:text-text-primary disabled:opacity-50 transition-colors"
          >
            I've verified
          </button>
          <Link
            to="/support"
            className="text-xs text-text-muted hover:text-text-primary transition-colors"
          >
            Help
          </Link>
          <button
            onClick={handleDismiss}
            title="Hide until next visit"
            className="text-text-muted hover:text-text-primary transition-colors leading-none px-1"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
