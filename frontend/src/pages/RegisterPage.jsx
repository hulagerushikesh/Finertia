import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword, sendEmailVerification } from "firebase/auth";
import { doc, setDoc, serverTimestamp } from "firebase/firestore";
import { auth, db } from "../firebase";
import AuthShell, { AuthField } from "../components/AuthShell";
import PasswordInput from "../components/PasswordInput";
import Spinner from "../components/Spinner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

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
      // its profile document both exist by this point. The workspace banner
      // surfaces it, with the resend button.
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

  // Firebase rejects anything shorter, but only after a round-trip.
  const passwordShort = password.length > 0 && password.length < 6;

  return (
    <AuthShell
      title="Create your account."
      subtitle="Free to start. No card, and the engine is the same one Pro runs on."
      aside={
        <div className="max-w-sm">
          <p className="eyebrow mb-4">What the free plan runs</p>
          <ul className="flex flex-col gap-3 text-sm text-graphite leading-relaxed">
            <li>
              <span className="text-foreground font-medium">Three strategies</span> on any symbol
              yfinance carries, over any date range.
            </li>
            <li>
              <span className="text-foreground font-medium">Twelve metrics</span>, each with a
              confidence interval, an equity curve against buy-and-hold, and a drawdown chart.
            </li>
            <li>
              <span className="text-foreground font-medium">Saved history</span>, so a run you
              liked is still there tomorrow with its parameters intact.
            </li>
          </ul>
          <p className="margin-note mt-6">
            Walk-forward validation and the permutation test are the Pro additions.
          </p>
        </div>
      }
    >
      {error && (
        <Alert variant="destructive" className="mb-5">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-4">
        <AuthField label="Display name" htmlFor="reg-name">
          <Input
            id="reg-name"
            type="text"
            placeholder="Optional — we use your email otherwise"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            onKeyDown={handleKey}
          />
        </AuthField>

        <AuthField label="Email" htmlFor="reg-email">
          <Input
            id="reg-email"
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
            <p className="text-xs text-warn">
              {6 - password.length} more character{6 - password.length === 1 ? "" : "s"} needed.
            </p>
          )}
        </AuthField>

        <Button
          onClick={handleRegister}
          disabled={loading || password.length < 6 || !email}
          className="w-full mt-1"
        >
          {loading ? (
            <>
              <Spinner /> Creating account…
            </>
          ) : (
            "Create account"
          )}
        </Button>
      </div>

      <p className="text-xs text-graphite text-center mt-6">
        Already have an account?{" "}
        <Link to="/login" className="text-pencil hover:underline rounded-sm">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
