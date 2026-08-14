import React, { useState } from "react";
import { Link } from "react-router-dom";
import { sendPasswordResetEmail } from "firebase/auth";
import { auth } from "../firebase";

const ERROR_MAP = {
  "auth/invalid-email": "That email address isn't valid.",
  "auth/user-not-found": "No account found with this email.",
  "auth/too-many-requests": "Too many attempts. Please try again in a few minutes.",
  "auth/missing-email": "Enter the email address for your account.",
};

const inputClass =
  "w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary placeholder-text-muted/50 focus:outline-none focus:border-accent transition-colors";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    setError("");
    if (!email.trim()) {
      setError(ERROR_MAP["auth/missing-email"]);
      return;
    }
    setLoading(true);
    try {
      await sendPasswordResetEmail(auth, email.trim());
      setSent(true);
    } catch (err) {
      setError(ERROR_MAP[err.code] || err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter") handleSend();
  }

  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="bg-surface border border-border rounded-2xl p-8">
          {sent ? (
            <>
              <div className="w-10 h-10 rounded-full bg-success/10 border border-success/30 flex items-center justify-center mb-4">
                <span className="text-success text-lg leading-none">✓</span>
              </div>
              <h1 className="text-xl font-bold text-text-primary mb-1">Check your inbox</h1>
              <p className="text-sm text-text-muted mb-6 leading-relaxed">
                If an account exists for{" "}
                <span className="text-text-primary font-mono">{email.trim()}</span>, a password
                reset link is on its way. The link expires in one hour.
              </p>
              <Link
                to="/login"
                className="block w-full text-center bg-accent hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
              >
                Back to sign in
              </Link>
              <button
                onClick={() => {
                  setSent(false);
                  setError("");
                }}
                className="w-full text-xs text-text-muted hover:text-text-primary transition-colors mt-4"
              >
                Use a different email
              </button>
            </>
          ) : (
            <>
              <h1 className="text-xl font-bold text-text-primary mb-1">Reset your password</h1>
              <p className="text-sm text-text-muted mb-6">
                Enter your email and we'll send you a reset link.
              </p>

              {error && (
                <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-lg px-4 py-3 mb-4">
                  {error}
                </div>
              )}

              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-xs text-text-muted font-medium block mb-1">Email</label>
                  <input
                    className={inputClass}
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyDown={handleKey}
                    autoComplete="email"
                  />
                </div>

                <button
                  onClick={handleSend}
                  disabled={loading}
                  className="w-full bg-accent hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
                >
                  {loading ? "Sending…" : "Send reset link"}
                </button>
              </div>

              <p className="text-xs text-text-muted text-center mt-5">
                Remembered it?{" "}
                <Link to="/login" className="text-accent hover:underline">
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
