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
import { useToast } from "../hooks/useToast";

const PASSWORD_ERROR_MAP = {
  "auth/wrong-password": "Your current password is incorrect.",
  "auth/invalid-credential": "Your current password is incorrect.",
  "auth/weak-password": "New password must be at least 6 characters.",
  "auth/too-many-requests": "Too many attempts. Please try again later.",
  "auth/requires-recent-login": "Please sign out and back in, then try again.",
};

const inputClass =
  "w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary placeholder-text-faint focus:outline-none focus:border-accent transition-colors";

const labelClass = "text-xs text-text-muted font-medium block mb-1";

function Card({ title, description, children }) {
  return (
    <section className="panel rounded-2xl p-6">
      <h2 className="text-sm font-bold text-text-primary">{title}</h2>
      {description && <p className="text-xs text-text-muted mt-1 mb-5">{description}</p>}
      {children}
    </section>
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
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-6">
        <UsageMeter />
      </div>
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">Profile</h1>
        <p className="text-sm text-text-muted mt-1">
          Manage your account details and password.
        </p>
      </header>

      <div className="flex flex-col gap-4">
        <Card title="Account">
          <dl className="grid grid-cols-[110px_1fr] gap-y-3 text-sm">
            <dt className="text-text-muted text-xs pt-0.5">Email</dt>
            <dd className="text-xs break-all">
              <span className="font-mono text-text-primary">{user.email}</span>{" "}
              <span
                className={`inline-block text-2xs font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border align-middle ${
                  emailVerified
                    ? "bg-success/10 border-success/30 text-success"
                    : "bg-warning/10 border-warning/30 text-warning"
                }`}
              >
                {emailVerified ? "verified" : "unverified"}
              </span>
            </dd>

            <dt className="text-text-muted text-xs pt-0.5">Role</dt>
            <dd>
              <span
                className={`inline-block text-2xs font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                  userProfile?.role === "admin"
                    ? "bg-accent/10 border-accent/30 text-accent"
                    : "bg-bg border-border text-text-muted"
                }`}
              >
                {userProfile?.role || "user"}
              </span>
            </dd>

            <dt className="text-text-muted text-xs pt-0.5">Backtests run</dt>
            <dd className="font-mono text-xs text-text-primary tabular-nums">
              {userProfile?.totalRuns ?? 0}
            </dd>

            <dt className="text-text-muted text-xs pt-0.5">Member since</dt>
            <dd className="font-mono text-xs text-text-primary">{joined}</dd>
          </dl>
        </Card>

        <Card
          title="Display name"
          description="Shown in the admin panel. Your email address is never changed here."
        >
          <div className="flex flex-col gap-4">
            <div>
              <label className={labelClass}>Display name</label>
              <input
                className={inputClass}
                type="text"
                placeholder="Your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveName()}
                autoComplete="name"
              />
            </div>
            <button
              onClick={handleSaveName}
              disabled={savingName}
              className="btn-primary self-start px-5 py-2 text-sm"
            >
              {savingName ? "Saving…" : "Save"}
            </button>
          </div>
        </Card>

        <Card
          title="Change password"
          description="You'll need your current password to set a new one."
        >
          {passwordError && (
            <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-lg px-4 py-3 mb-4">
              {passwordError}
            </div>
          )}

          <div className="flex flex-col gap-4">
            <div>
              <label className={labelClass}>Current password</label>
              <input
                className={inputClass}
                type="password"
                placeholder="••••••••"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <div>
              <label className={labelClass}>New password</label>
              <input
                className={inputClass}
                type="password"
                placeholder="At least 6 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className={labelClass}>Confirm new password</label>
              <input
                className={inputClass}
                type="password"
                placeholder="Re-enter new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleChangePassword()}
                autoComplete="new-password"
              />
            </div>
            <button
              onClick={handleChangePassword}
              disabled={savingPassword}
              className="btn-primary self-start px-5 py-2 text-sm"
            >
              {savingPassword ? "Updating…" : "Change password"}
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}
