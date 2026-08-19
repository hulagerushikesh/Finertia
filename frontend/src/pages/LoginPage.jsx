import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase";
import { useToast } from "../hooks/useToast";
import AuthShell, { AuthField } from "../components/AuthShell";
import PasswordInput from "../components/PasswordInput";

const ERROR_MAP = {
  "auth/wrong-password": "Incorrect password.",
  "auth/user-not-found": "No account found with this email.",
  "auth/invalid-email": "Invalid email address.",
  "auth/too-many-requests": "Too many attempts. Please try again later.",
  "auth/invalid-credential": "Incorrect email or password.",
};

export default function LoginPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setError("");
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      navigate("/dashboard");
    } catch (err) {
      const message = ERROR_MAP[err.code] || err.message;
      setError(message);
      showToast(message, "error");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter") handleLogin();
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to pick up your saved runs."
      aside={
        <div className="max-w-sm">
          <p className="eyebrow mb-4">While you were away</p>
          <p className="text-sm text-text-muted leading-relaxed">
            Every run you have kept is still in History, with the exact
            parameters it used. Reopen one to compare it against a new set, or
            send someone a link that rebuilds the configuration on their screen.
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
        <AuthField label="Email" htmlFor="login-email">
          <input
            id="login-email"
            className="field-input py-2.5"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={handleKey}
            autoComplete="email"
          />
        </AuthField>

        <AuthField
          label="Password"
          htmlFor="login-password"
          action={
            <Link
              to="/forgot-password"
              className="text-xs text-text-muted hover:text-accent transition-colors rounded"
            >
              Forgot password?
            </Link>
          }
        >
          <PasswordInput
            id="login-password"
            value={password}
            onChange={setPassword}
            onKeyDown={handleKey}
            placeholder="Your password"
            autoComplete="current-password"
          />
        </AuthField>

        <button
          onClick={handleLogin}
          disabled={loading}
          className="btn-primary w-full py-2.5 text-sm mt-1"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Signing in…
            </>
          ) : (
            "Sign in"
          )}
        </button>
      </div>

      <p className="text-xs text-text-muted text-center mt-6">
        No account yet?{" "}
        <Link to="/register" className="text-accent hover:underline rounded">
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}
