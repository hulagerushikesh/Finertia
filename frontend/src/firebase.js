import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
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
