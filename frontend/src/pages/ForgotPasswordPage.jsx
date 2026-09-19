import React, { useState } from "react";
import { Link } from "react-router-dom";
import { sendPasswordResetEmail } from "firebase/auth";
import { auth } from "../firebase";
import AuthShell, { AuthField } from "../components/AuthShell";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

const ERROR_MAP = {
  "auth/invalid-email": "That email address isn't valid.",
  "auth/user-not-found": "No account found with this email.",
  "auth/too-many-requests": "Too many attempts. Please try again in a few minutes.",
  "auth/missing-email": "Enter the email address for your account.",
};

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

  if (sent) {
    return (
      <AuthShell
        title="Check your inbox."
        subtitle={`If an account exists for ${email.trim()}, a reset link is on its way. It expires in one hour.`}
      >
        <Badge variant="gain" className="mb-6">Sent</Badge>
        <div className="flex flex-col gap-3">
          <Button asChild className="w-full">
            <Link to="/login">Back to sign in</Link>
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              setSent(false);
              setError("");
            }}
          >
            Use a different email
          </Button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Reset your password."
      subtitle="Enter your email and we'll send you a reset link."
    >
      {error && (
        <Alert variant="destructive" className="mb-5">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="flex flex-col gap-4">
        <AuthField label="Email" htmlFor="reset-email">
          <Input
            id="reset-email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={handleKey}
            autoComplete="email"
          />
        </AuthField>
        <Button onClick={handleSend} disabled={loading} className="w-full">
          {loading ? "Sending…" : "Send reset link"}
        </Button>
      </div>
      <p className="text-xs text-graphite text-center mt-6">
        Remembered it?{" "}
        <Link to="/login" className="text-pencil hover:underline rounded-sm">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
