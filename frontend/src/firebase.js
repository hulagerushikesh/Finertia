import { initializeApp } from "firebase/app";
import { getAuth, sendEmailVerification, sendPasswordResetEmail } from "firebase/auth";
// The lite SDK: REST calls, no realtime listeners, no offline cache. The
// client only ever does getDoc/setDoc/updateDoc on its own profile — the
// full SDK was ~250 kB minified on the landing page for a websocket nobody
// opened. Security rules apply identically.
import { getFirestore } from "firebase/firestore/lite";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

// Firebase's hosted "email verified" / "reset password" pages are dead ends
// unless the email carries a continue URL, in which case they show a
// Continue button back to it. The domain must be in Firebase Auth's
// authorised domains; if it is not (a preview deploy, a new domain), Firebase
// refuses to send at all, so retry without the link rather than lose the email.
const CONTINUE_URI_ERRORS = new Set(["auth/unauthorized-continue-uri", "auth/invalid-continue-uri"]);

async function withContinueUrl(path, send) {
  try {
    await send({ url: `${window.location.origin}${path}` });
  } catch (err) {
    if (!CONTINUE_URI_ERRORS.has(err.code)) throw err;
    await send(undefined);
  }
}

export function sendVerificationEmail(user) {
  return withContinueUrl("/dashboard", (settings) => sendEmailVerification(user, settings));
}

export function sendResetEmail(email) {
  return withContinueUrl("/login", (settings) => sendPasswordResetEmail(auth, email, settings));
}
