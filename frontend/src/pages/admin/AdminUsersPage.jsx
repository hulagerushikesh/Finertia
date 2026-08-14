import React, { useState, useEffect, useCallback } from "react";
import { getAdminUsers, updateUser } from "../../api";
import { SkeletonRows } from "../../components/SkeletonRow";
import { useToast } from "../../hooks/useToast";

// Mirrors the 7 columns of the users table.
const SKELETON_WIDTHS = ["80%", "40%", "60%", "60%", "35%", "45%", "70%"];

function fmtDate(ts) {
  if (!ts) return "—";
  const d = ts._seconds ? new Date(ts._seconds * 1000) : new Date(ts);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export default function AdminUsersPage() {
  const { showToast } = useToast();
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [confirmModal, setConfirmModal] = useState(null);

  const PAGE_SIZE = 50;

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    getAdminUsers(PAGE_SIZE, page * PAGE_SIZE, search)
      .then((d) => { setUsers(d.users); setTotal(d.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [page, search]);

  useEffect(() => { load(); }, [load]);

  async function applyPatch(uid, patch, successMessage) {
    try {
      const updated = await updateUser(uid, patch);
      setUsers((prev) => prev.map((u) => (u.uid === uid ? updated : u)));
      showToast(successMessage, "success");
    } catch (e) {
      setError(e.message);
      showToast(e.message, "error");
    }
  }

  function confirmAction(label, uid, patch, successMessage) {
    setConfirmModal({ label, uid, patch, successMessage });
  }

  async function handleConfirm() {
    await applyPatch(confirmModal.uid, confirmModal.patch, confirmModal.successMessage);
    setConfirmModal(null);
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      {/* Search */}
      <div className="flex gap-3 mb-5">
        <input
          className="flex-1 max-w-xs bg-surface border border-border rounded-lg px-4 py-2 text-sm text-text-primary placeholder-text-muted/50 focus:outline-none focus:border-accent"
          placeholder="Search by email…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { setSearch(searchInput); setPage(0); } }}
        />
        <button
          onClick={() => { setSearch(searchInput); setPage(0); }}
          className="bg-accent hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-lg"
        >
          Search
        </button>
        {search && (
          <button
            onClick={() => { setSearch(""); setSearchInput(""); setPage(0); }}
            className="text-sm text-text-muted hover:text-text-primary"
          >
            Clear
          </button>
        )}
      </div>

      {error && <div className="text-danger bg-danger/10 border border-danger/20 rounded-xl px-5 py-4 mb-4 text-sm">{error}</div>}

      <>
          <div className="bg-surface border border-border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-5 py-3">Email</th>
                  <th className="text-left px-5 py-3">Role</th>
                  <th className="text-left px-5 py-3">Joined</th>
                  <th className="text-left px-5 py-3">Last Active</th>
                  <th className="text-right px-5 py-3">Runs</th>
                  <th className="text-center px-5 py-3">Status</th>
                  <th className="text-right px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && <SkeletonRows rows={8} widths={SKELETON_WIDTHS} />}
                {!loading && users.map((u) => (
                  <tr key={u.uid} className="border-b border-border/50 hover:bg-border/20 transition-colors">
                    <td className="px-5 py-3 text-text-primary text-xs font-mono">{u.email}</td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${u.role === "admin" ? "bg-accent/10 text-accent" : "bg-border text-text-muted"}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-text-muted text-xs">{fmtDate(u.createdAt)}</td>
                    <td className="px-5 py-3 text-text-muted text-xs">{fmtDate(u.lastLoginAt)}</td>
                    <td className="px-5 py-3 text-right font-mono text-xs">{u.totalRuns ?? 0}</td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${u.isActive !== false ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}>
                        {u.isActive !== false ? "Active" : "Blocked"}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button
                          onClick={() => {
                            const blocking = u.isActive !== false;
                            confirmAction(
                              blocking
                                ? `Block ${u.email}? They will be signed out of the API immediately and cannot run backtests.`
                                : `Unblock ${u.email}? They will regain full access.`,
                              u.uid,
                              { isActive: !blocking },
                              blocking ? `${u.email} blocked.` : `${u.email} unblocked.`
                            );
                          }}
                          className="text-xs text-text-muted hover:text-danger transition-colors"
                        >
                          {u.isActive !== false ? "Block" : "Unblock"}
                        </button>
                        <button
                          onClick={() => {
                            const nextRole = u.role === "admin" ? "user" : "admin";
                            confirmAction(
                              `Change ${u.email} role to ${nextRole}?`,
                              u.uid,
                              { role: nextRole },
                              `${u.email} is now ${nextRole}.`
                            );
                          }}
                          className="text-xs text-accent hover:underline"
                        >
                          Make {u.role === "admin" ? "User" : "Admin"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && users.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-12 text-text-muted">No users found.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {!loading && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="text-sm text-text-muted hover:text-text-primary disabled:opacity-30">← Previous</button>
              <span className="text-xs text-text-muted">{page + 1} / {totalPages}</span>
              <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page === totalPages - 1} className="text-sm text-text-muted hover:text-text-primary disabled:opacity-30">Next →</button>
            </div>
          )}
      </>

      {/* Confirm modal */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setConfirmModal(null)}>
          <div className="bg-surface border border-border rounded-2xl p-6 max-w-sm w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-text-primary mb-2">Confirm Action</h3>
            <p className="text-sm text-text-muted mb-5">{confirmModal.label}</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setConfirmModal(null)} className="text-sm text-text-muted hover:text-text-primary px-4 py-2">Cancel</button>
              <button onClick={handleConfirm} className="text-sm bg-accent hover:bg-indigo-500 text-white px-4 py-2 rounded-lg">Confirm</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
