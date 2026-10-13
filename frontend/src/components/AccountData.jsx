import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { exportMyData, deleteMyAccount } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import ProfileSection from "./ProfileSection";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

/** Hand a JSON body to the browser as a file download. */
function downloadJson(body, filename) {
  const blob = new Blob([JSON.stringify(body, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const sameEmail = (a, b) => (a || "").trim().toLowerCase() === (b || "").trim().toLowerCase();

/**
 * Profile → export my data, delete my account (DPDP access and erasure), on
 * `GET /api/me/export` and `DELETE /api/me`. Behind the "account-data"
 * switch until the tester round closes.
 *
 * Deletion cannot be undone, so it takes two deliberate steps: open the
 * confirmation, then type the account's email address. The API checks the
 * same email, so the typed confirmation is not only a UI guard.
 */
export default function AccountData() {
  const { user, userProfile } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [exporting, setExporting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const isAdmin = userProfile?.role === "admin";
  const matches = sameEmail(typed, user.email);

  async function handleExport() {
    setExporting(true);
    try {
      const body = await exportMyData();
      const stamp = (body.exported_at || new Date().toISOString()).slice(0, 10);
      downloadJson(body, `finertia-export-${stamp}.json`);
      showToast("Your data is downloading.", "success");
    } catch (err) {
      showToast(`Could not export your data — ${err.message}`, "error");
    } finally {
      setExporting(false);
    }
  }

  function cancelDelete() {
    setConfirming(false);
    setTyped("");
    setDeleteError("");
  }

  async function handleDelete() {
    if (!matches) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteMyAccount(typed.trim());
    } catch (err) {
      setDeleteError(err.message);
      setDeleting(false);
      return;
    }
    // The goodbye page signs out, not this one. Signing out here would make
    // the Profile page's route guard, still on screen during the route
    // transition, redirect to the login page instead.
    navigate("/account-deleted", { replace: true, state: { deleted: true } });
  }

  return (
    <>
      <ProfileSection
        title="Your data"
        description="A copy of everything Finertia stores about you, as a JSON file."
      >
        <p className="text-sm text-graphite leading-relaxed mb-4">
          Your profile, your plan and usage counters, and every saved run with its settings and
          results.
        </p>
        <Button variant="outline" onClick={handleExport} disabled={exporting}>
          {exporting ? "Preparing…" : "Download my data"}
        </Button>
      </ProfileSection>

      <ProfileSection title="Delete account" description="Removes the account for good. This can't be undone.">
        {isAdmin ? (
          <p className="text-sm text-graphite leading-relaxed" data-testid="delete-admin-note">
            Admin accounts can't delete themselves. Ask another admin to remove the admin role first.
          </p>
        ) : !confirming ? (
          <>
            <p className="text-sm text-graphite leading-relaxed mb-4">
              Deletes your saved runs, your profile and your sign-in. Download your data first if you
              want a copy.
            </p>
            <Button variant="outline" className="text-loss border-loss/40" onClick={() => setConfirming(true)}>
              Delete my account…
            </Button>
          </>
        ) : (
          <div className="flex flex-col gap-4">
            <Alert variant="destructive">
              <AlertDescription>
                This deletes your account, your saved runs ({userProfile?.totalRuns ?? 0}) and your
                sign-in straight away. There is no undo, and support can't bring it back.
              </AlertDescription>
            </Alert>
            {deleteError && (
              <Alert variant="destructive">
                <AlertDescription>{deleteError}</AlertDescription>
              </Alert>
            )}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="delete-confirm" className="eyebrow">
                Type your email address to confirm
              </Label>
              <Input
                id="delete-confirm"
                type="email"
                placeholder={user.email}
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleDelete()}
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button variant="destructive" onClick={handleDelete} disabled={!matches || deleting}>
                {deleting ? "Deleting…" : "Delete my account for good"}
              </Button>
              <Button variant="ghost" onClick={cancelDelete} disabled={deleting}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </ProfileSection>
    </>
  );
}
