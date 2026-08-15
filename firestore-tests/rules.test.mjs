import {
  initializeTestEnvironment,
  assertFails,
  assertSucceeds,
} from "@firebase/rules-unit-testing";
import { doc, getDoc, setDoc, updateDoc, deleteDoc } from "firebase/firestore";
import { readFileSync } from "node:fs";

const RULES = new URL("../firestore.rules", import.meta.url).pathname;

const env = await initializeTestEnvironment({
  projectId: "finertia-rules-test",
  firestore: { rules: readFileSync(RULES, "utf8"), host: "127.0.0.1", port: 8080 },
});

// The emulator keeps data between runs. Without this, a second run finds
// alice already present, so `setDoc` is an update rather than a create and the
// registration test fails for a reason that has nothing to do with the rules.
await env.clearFirestore();

const alice = env.authenticatedContext("alice").firestore();
const mallory = env.authenticatedContext("mallory").firestore();
const anon = env.unauthenticatedContext().firestore();

// A valid profile, exactly as RegisterPage writes it.
const profile = (uid) => ({
  uid,
  email: `${uid}@example.com`,
  displayName: uid,
  role: "user",
  createdAt: new Date(),
  lastLoginAt: new Date(),
  totalRuns: 0,
  isActive: true,
});

let pass = 0,
  fail = 0;
async function check(name, promise) {
  try {
    await promise;
    console.log(`  ok   ${name}`);
    pass++;
  } catch (e) {
    console.log(`  FAIL ${name}\n       ${e.message.split("\n")[0]}`);
    fail++;
  }
}

console.log("\nusers — the app's own flows must still work");
await check(
  "register: alice creates her own profile",
  assertSucceeds(setDoc(doc(alice, "users/alice"), profile("alice")))
);
await check(
  "read: alice reads her own profile",
  assertSucceeds(getDoc(doc(alice, "users/alice")))
);
await check(
  "profile page: alice changes her displayName",
  assertSucceeds(updateDoc(doc(alice, "users/alice"), { displayName: "Alice A" }))
);

console.log("\nusers — privilege escalation must be refused");
await check(
  "alice cannot make herself an admin",
  assertFails(updateDoc(doc(alice, "users/alice"), { role: "admin" }))
);
await check(
  "alice cannot register as an admin",
  assertFails(
    setDoc(doc(alice, "users/alice2"), { ...profile("alice2"), role: "admin" })
  )
);
await check(
  "alice cannot grant herself the Pro plan",
  assertFails(updateDoc(doc(alice, "users/alice"), { plan: "pro" }))
);
await check(
  "alice cannot arrive pre-paid at registration",
  assertFails(
    setDoc(doc(alice, "users/alice3"), { ...profile("alice3"), plan: "pro" })
  )
);
await check(
  "alice cannot reset her own quota counter",
  assertFails(updateDoc(doc(alice, "users/alice"), { runsThisPeriod: 0 }))
);
await check(
  "alice cannot inflate her own run total",
  assertFails(updateDoc(doc(alice, "users/alice"), { totalRuns: 9999 }))
);
// Suspend her the way an admin would — server-side, bypassing rules — so the
// reactivation attempt is a real state change rather than a no-op write.
// Writing the value a field already holds changes nothing, affectedKeys() is
// empty, and the rule allows it: correct behaviour, but it proves nothing.
await env.withSecurityRulesDisabled(async (ctx) => {
  await setDoc(doc(ctx.firestore(), "users/alice"), { ...profile("alice"), isActive: false });
});
await check(
  "a suspended user cannot reactivate themselves",
  assertFails(updateDoc(doc(alice, "users/alice"), { isActive: true }))
);
await check(
  "a no-op write of an unchanged field is harmless",
  assertSucceeds(updateDoc(doc(alice, "users/alice"), { isActive: false }))
);
await check(
  "displayName plus a smuggled role is still refused",
  assertFails(
    updateDoc(doc(alice, "users/alice"), { displayName: "X", role: "admin" })
  )
);
await check(
  "alice cannot delete her profile",
  assertFails(deleteDoc(doc(alice, "users/alice")))
);

console.log("\nusers — cross-account access must be refused");
await check(
  "mallory cannot read alice's profile",
  assertFails(getDoc(doc(mallory, "users/alice")))
);
await check(
  "mallory cannot write alice's profile",
  assertFails(updateDoc(doc(mallory, "users/alice"), { displayName: "pwned" }))
);
await check(
  "mallory cannot create a profile under alice's uid",
  assertFails(setDoc(doc(mallory, "users/alice9"), profile("alice9")))
);
await check(
  "signed-out reads are refused",
  assertFails(getDoc(doc(anon, "users/alice")))
);

console.log("\nruns — the client has no business here at all");
await check(
  "alice cannot read a run",
  assertFails(getDoc(doc(alice, "runs/r1")))
);
await check(
  "alice cannot forge a run",
  assertFails(setDoc(doc(alice, "runs/r1"), { uid: "alice", ticker: "AAPL" }))
);
await check(
  "alice cannot forge a run attributed to mallory",
  assertFails(setDoc(doc(alice, "runs/r2"), { uid: "mallory" }))
);

console.log(`\n${pass} passed, ${fail} failed\n`);
await env.cleanup();
process.exit(fail ? 1 : 0);
