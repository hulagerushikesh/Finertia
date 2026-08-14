import React, { createContext, useState, useEffect } from "react";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { doc, getDoc } from "firebase/firestore";
import { auth, db } from "../firebase";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  // Kept as its own boolean rather than read off `user`. Firebase mutates the
  // user object in place when verification state changes, so its identity never
  // changes and React has nothing to re-render on.
  const [emailVerified, setEmailVerified] = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      setEmailVerified(Boolean(firebaseUser?.emailVerified));
      if (firebaseUser) {
        try {
          const snap = await getDoc(doc(db, "users", firebaseUser.uid));
          setUserProfile(snap.exists() ? snap.data() : null);
        } catch {
          setUserProfile(null);
        }
      } else {
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
    setUser(null);
    setUserProfile(null);
    setEmailVerified(false);
  }

  return (
    <AuthContext.Provider
      value={{ user, userProfile, loading, emailVerified, refreshUser, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
