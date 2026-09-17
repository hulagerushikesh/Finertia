import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase";
import { useToast } from "../hooks/useToast";
import AuthShell, { AuthField } from "../components/AuthShell";
import PasswordInput from "../components/PasswordInput";
import Spinner from "../components/Spinner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

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
      title="Welcome back."
      subtitle="Sign in to pick up your saved runs."
      aside={
        <div className="max-w-sm">
          <p className="eyebrow mb-4">While you were away</p>
          <p className="margin-note">
            Every run you kept is still in History, with the exact parameters it used.
          </p>
          <p className="text-sm text-graphite leading-relaxed mt-4">
            Reopen one to compare it against a new set, or send someone a link that rebuilds
            the configuration on their screen.
          </p>
        </div>
      }
    >
      {error && (
        <Alert variant="destructive" className="mb-5">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* No <form>: controlled inputs and a click handler, Enter wired by hand. */}
      <div className="flex flex-col gap-4">
        <AuthField label="Email" htmlFor="login-email">
          <Input
            id="login-email"
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
            <Link to="/forgot-password" className="text-xs text-graphite hover:text-pencil transition-colors rounded-sm">
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

        <Button onClick={handleLogin} disabled={loading} className="w-full mt-1">
          {loading ? (
            <>
              <Spinner /> Signing in…
            </>
          ) : (
            "Sign in"
          )}
        </Button>
      </div>

      <p className="text-xs text-graphite text-center mt-6">
        No account yet?{" "}
        <Link to="/register" className="text-pencil hover:underline rounded-sm">
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}
