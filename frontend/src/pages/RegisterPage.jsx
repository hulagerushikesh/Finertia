import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword, sendEmailVerification } from "firebase/auth";
import { doc, setDoc, serverTimestamp } from "firebase/firestore";
import { auth, db } from "../firebase";
import AuthShell, { AuthField } from "../components/AuthShell";
import PasswordInput from "../components/PasswordInput";

const ERROR_MAP = {
  "auth/email-already-in-use": "Email already registered.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/invalid-email": "Invalid email address.",
};

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

  // Firebase rejects anything shorter, but only after a round-trip. Saying so
  // while they type turns a failed submission into a non-event.
  const passwordShort = password.length > 0 && password.length < 6;

  return (
    <AuthShell
      title="Create your account"
      subtitle="Free to start. No card, and the engine is the same one Pro runs on."
      aside={
        <div className="max-w-sm">
          <p className="eyebrow mb-4">What the free plan runs</p>
          <ul className="flex flex-col gap-3 text-sm text-text-muted leading-relaxed">
            <li>
              <span className="text-text-primary">Three strategies</span> on any
              symbol yfinance carries, over any date range.
            </li>
            <li>
              <span className="text-text-primary">Twelve metrics</span>, an
              equity curve against buy-and-hold, and a drawdown chart.
            </li>
            <li>
              <span className="text-text-primary">Saved history</span>, so a run
              you liked is still there tomorrow with its parameters intact.
            </li>
          </ul>
          <p className="text-xs text-text-faint mt-5 leading-relaxed">
            Walk-forward validation and permutation testing are the Pro
            additions — see Pricing for the quotas.
          </p>
        </div>
      }
    >
      {error && (
        <div
          role="alert"
          className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-lg px-4 py-3 mb-5"
        >
          {error}
        </div>
      )}

      <div className="flex flex-col gap-4">
        <AuthField label="Display name" htmlFor="reg-name">
          <input
            id="reg-name"
            className="field-input py-2.5"
            type="text"
            placeholder="Optional — we use your email otherwise"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            onKeyDown={handleKey}
          />
        </AuthField>

        <AuthField label="Email" htmlFor="reg-email">
          <input
            id="reg-email"
            className="field-input py-2.5"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={handleKey}
            autoComplete="email"
          />
        </AuthField>

        <AuthField label="Password" htmlFor="reg-password">
          <PasswordInput
            id="reg-password"
            value={password}
            onChange={setPassword}
            onKeyDown={handleKey}
            placeholder="At least 6 characters"
            autoComplete="new-password"
          />
          {passwordShort && (
            <p className="text-xs text-warning">
              {6 - password.length} more character
              {6 - password.length === 1 ? "" : "s"} needed.
            </p>
          )}
        </AuthField>

        <button
          onClick={handleRegister}
          disabled={loading || password.length < 6 || !email}
          className="btn-primary w-full py-2.5 text-sm mt-1"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Creating account…
            </>
          ) : (
            "Create account"
          )}
        </button>
      </div>

      <p className="text-xs text-text-muted text-center mt-6">
        Already have an account?{" "}
        <Link to="/login" className="text-accent hover:underline rounded">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
