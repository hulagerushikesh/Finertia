import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword, sendEmailVerification } from "firebase/auth";
import { doc, setDoc, serverTimestamp } from "firebase/firestore";
import { auth, db } from "../firebase";

const ERROR_MAP = {
  "auth/email-already-in-use": "Email already registered.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/invalid-email": "Invalid email address.",
};

const inputClass =
  "w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary placeholder-text-muted/50 focus:outline-none focus:border-accent transition-colors";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister() {
    setError("");
    setLoading(true);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      const uid = cred.user.uid;
      await setDoc(doc(db, "users", uid), {
        uid,
        email,
        displayName: displayName || email.split("@")[0],
        role: "user",
        createdAt: serverTimestamp(),
        lastLoginAt: serverTimestamp(),
        totalRuns: 0,
        isActive: true,
      });

      // A failed send must not read as a failed registration — the account and
      // its profile document both exist by this point. The dashboard banner is
      // where this surfaces instead: it appears precisely when the address is
      // unverified, and carries the resend button.
      try {
        await sendEmailVerification(cred.user);
      } catch {
        /* surfaced by VerifyEmailBanner */
      }

      navigate("/dashboard");
    } catch (err) {
      setError(ERROR_MAP[err.code] || err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter") handleRegister();
  }

  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="bg-surface border border-border rounded-2xl p-8">
          <h1 className="text-xl font-bold text-text-primary mb-1">Create your account</h1>
          <p className="text-sm text-text-muted mb-6">Start backtesting momentum strategies.</p>

          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-lg px-4 py-3 mb-4">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-4">
            <div>
              <label className="text-xs text-text-muted font-medium block mb-1">Display Name</label>
              <input
                className={inputClass}
                type="text"
                placeholder="Your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                onKeyDown={handleKey}
              />
            </div>
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
            <div>
              <label className="text-xs text-text-muted font-medium block mb-1">Password</label>
              <input
                className={inputClass}
                type="password"
                placeholder="At least 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={handleKey}
                autoComplete="new-password"
              />
            </div>

            <button
              onClick={handleRegister}
              disabled={loading}
              className="w-full bg-accent hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
            >
              {loading ? "Creating account…" : "Create Account"}
            </button>
          </div>

          <p className="text-xs text-text-muted text-center mt-5">
            Already have an account?{" "}
            <Link to="/login" className="text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
