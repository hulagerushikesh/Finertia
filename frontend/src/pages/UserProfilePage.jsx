import React, { useState, useEffect } from "react";
import {
  updateProfile,
  updatePassword,
  reauthenticateWithCredential,
  EmailAuthProvider,
} from "firebase/auth";
import { doc, updateDoc } from "firebase/firestore";
import { auth, db } from "../firebase";
import { useAuth } from "../hooks/useAuth";
import UsageMeter from "../components/UsageMeter";
import PasswordInput from "../components/PasswordInput";
import { Rise } from "../components/motion";
import { useToast } from "../hooks/useToast";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

const PASSWORD_ERROR_MAP = {
  "auth/wrong-password": "Your current password is incorrect.",
  "auth/invalid-credential": "Your current password is incorrect.",
  "auth/weak-password": "New password must be at least 6 characters.",
  "auth/too-many-requests": "Too many attempts. Please try again later.",
  "auth/requires-recent-login": "Please sign out and back in, then try again.",
};

/** A titled sheet with the title set in the margin from lg up. */
function Card({ title, description, children }) {
  return (
    <section className="sheet p-6 grid lg:grid-cols-[11rem_minmax(0,1fr)] gap-x-8 gap-y-4">
      <div>
        <h2 className="font-display text-lg font-medium text-foreground leading-tight">{title}</h2>
        {description && <p className="text-xs text-graphite mt-1.5 leading-relaxed">{description}</p>}
      </div>
      <div>{children}</div>
    </section>
  );
}

function Pill({ children, tone }) {
  return (
    <Badge variant="outline" className={cn("font-mono text-tick uppercase tracking-wider px-1.5 py-0 align-middle", tone)}>
      {children}
    </Badge>
  );
}

export default function UserProfilePage() {
  const { user, userProfile, emailVerified } = useAuth();
  const { showToast } = useToast();

  const [displayName, setDisplayName] = useState("");
  const [savingName, setSavingName] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  useEffect(() => {
    setDisplayName(userProfile?.displayName || user?.displayName || "");
  }, [userProfile, user]);

  async function handleSaveName() {
    const trimmed = displayName.trim();
    if (!trimmed) {
      showToast("Display name can't be empty.", "error");
      return;
    }
    setSavingName(true);
    try {
      // Firebase Auth carries the name on the token; Firestore is what the
      // admin panel reads. Both have to be updated to stay consistent.
      await updateProfile(auth.currentUser, { displayName: trimmed });
      await updateDoc(doc(db, "users", user.uid), { displayName: trimmed });
      showToast("Display name updated.", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setSavingName(false);
    }
  }

  async function handleChangePassword() {
    setPasswordError("");

    if (!currentPassword) {
      setPasswordError("Enter your current password.");
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords don't match.");
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError("New password must be different from the current one.");
      return;
    }

    setSavingPassword(true);
    try {
      // Firebase requires a recent login before a password change; re-auth
      // with the current password satisfies that without a full sign-out.
      const credential = EmailAuthProvider.credential(user.email, currentPassword);
      await reauthenticateWithCredential(auth.currentUser, credential);
      await updatePassword(auth.currentUser, newPassword);

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      showToast("Password changed.", "success");
    } catch (err) {
      setPasswordError(PASSWORD_ERROR_MAP[err.code] || err.message);
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) return null;

  const joined = userProfile?.createdAt?.toDate
    ? userProfile.createdAt.toDate().toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <Rise>
        <header className="mb-8">
          <p className="eyebrow mb-3">Account</p>
          <h1 className="font-display text-display-sm font-medium text-foreground">Profile</h1>
        </header>
      </Rise>

      <Rise delay={0.05} className="flex flex-col gap-4">
        <UsageMeter />

        <Card title="Account">
          <dl className="grid grid-cols-[7rem_1fr] gap-y-3 text-sm items-baseline">
            <dt className="eyebrow">Email</dt>
            <dd className="text-xs break-all flex items-center gap-2 flex-wrap">
              <span className="font-mono text-foreground">{user.email}</span>
              <Pill tone={emailVerified ? "text-gain border-gain/40" : "text-warn border-warn/40"}>
                {emailVerified ? "verified" : "unverified"}
              </Pill>
            </dd>

            <dt className="eyebrow">Role</dt>
            <dd>
              <Pill tone={userProfile?.role === "admin" ? "text-pencil border-pencil/40" : "text-graphite"}>
                {userProfile?.role || "user"}
              </Pill>
            </dd>

            <dt className="eyebrow">Backtests run</dt>
            <dd className="font-mono text-xs text-foreground">{userProfile?.totalRuns ?? 0}</dd>

            <dt className="eyebrow">Member since</dt>
            <dd className="font-mono text-xs text-foreground">{joined}</dd>
          </dl>
        </Card>

        <Card title="Display name" description="Shown in the admin panel. Your email address is never changed here.">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="profile-name" className="eyebrow">Display name</Label>
              <Input
                id="profile-name"
                type="text"
                placeholder="Your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveName()}
                autoComplete="name"
              />
            </div>
            <Button onClick={handleSaveName} disabled={savingName} className="self-start">
              {savingName ? "Saving…" : "Save"}
            </Button>
          </div>
        </Card>

        <Card title="Change password" description="You'll need your current password to set a new one.">
          {passwordError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{passwordError}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pw-current" className="eyebrow">Current password</Label>
              <PasswordInput
                id="pw-current"
                placeholder="Your current password"
                value={currentPassword}
                onChange={setCurrentPassword}
                autoComplete="current-password"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pw-new" className="eyebrow">New password</Label>
              <PasswordInput
                id="pw-new"
                placeholder="At least 6 characters"
                value={newPassword}
                onChange={setNewPassword}
                autoComplete="new-password"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pw-confirm" className="eyebrow">Confirm new password</Label>
              <PasswordInput
                id="pw-confirm"
                placeholder="Re-enter new password"
                value={confirmPassword}
                onChange={setConfirmPassword}
                onKeyDown={(e) => e.key === "Enter" && handleChangePassword()}
                autoComplete="new-password"
              />
            </div>
            <Button onClick={handleChangePassword} disabled={savingPassword} className="self-start">
              {savingPassword ? "Updating…" : "Change password"}
            </Button>
          </div>
        </Card>
      </Rise>
    </div>
  );
}
