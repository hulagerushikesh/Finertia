import React, { createContext, useState, useEffect, useRef } from "react";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { clearWorkspace } from "../lib/workspaceStore";
import { doc, getDoc } from "firebase/firestore/lite";
import { auth, db } from "../firebase";
import { setMonitoringUser } from "../lib/monitoring";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  // Kept as its own boolean rather than read off `user`. Firebase mutates the
  // user object in place when verification state changes, so its identity never
  // changes and React has nothing to re-render on.
  const [emailVerified, setEmailVerified] = useState(false);

  // Registration signs the new account in before it writes the profile
  // document. Until that write lands, the sign-in pages hold off redirecting:
  // leaving (or reloading) mid-write would strand an account with no profile,
  // and the read made at sign-in would have found nothing (RegisterPage).
  const [registering, setRegistering] = useState(false);
  // Profile reads can overlap (sign-in, then the read after registration's
  // write), and only the latest one may land.
  const profileRead = useRef(0);

  async function loadProfile(uid) {
    const read = ++profileRead.current;
    let profile = null;
    try {
      const snap = await getDoc(doc(db, "users", uid));
      profile = snap.exists() ? snap.data() : null;
    } catch {
      /* treated as no profile */
    }
    if (read === profileRead.current) setUserProfile(profile);
  }

  async function refreshProfile() {
    if (auth.currentUser) await loadProfile(auth.currentUser.uid);
  }

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (firebaseUser) => {
      // The kept workspace belongs to the account that ran it.
      if (!firebaseUser) clearWorkspace();
      setUser(firebaseUser);
      setMonitoringUser(firebaseUser?.uid ?? null);
      setEmailVerified(Boolean(firebaseUser?.emailVerified));
      if (firebaseUser) {
        await loadProfile(firebaseUser.uid);
      } else {
        profileRead.current += 1;
        setUserProfile(null);
      }
      setLoading(false);
    });
    return unsub;
  }, []);

  /**
   * Re-read the signed-in account from Firebase and return whether it is now
   * verified.
   *
   * Clicking the link in a verification email marks the account verified on
   * Firebase's side, but this tab is holding a cached user object that still
   * says otherwise. Nothing pushes the change down and `onAuthStateChanged`
   * does not fire for it, so without an explicit reload the banner would keep
   * nagging a user who has already done what it asked.
   */
  async function refreshUser() {
    if (!auth.currentUser) return false;
    await auth.currentUser.reload();
    const verified = Boolean(auth.currentUser.emailVerified);
    setEmailVerified(verified);
    setUser(auth.currentUser);
    return verified;
  }

  async function logout() {
    await signOut(auth);
    clearWorkspace();
    setUser(null);
    profileRead.current += 1;
    setUserProfile(null);
    setEmailVerified(false);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        userProfile,
        loading,
        emailVerified,
        registering,
        setRegistering,
        refreshUser,
        refreshProfile,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
