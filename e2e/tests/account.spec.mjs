import { test, expect } from "@playwright/test";
import { freshEmail, register, runBacktest } from "./helpers.mjs";

// Account export and deletion (backend/account.py), through the API with the
// signed-in user's own token, read from where the Firebase SDK keeps it. The
// Profile buttons are behind the "account-data" switch (switched-on/
// account-data.spec.mjs); the last test checks they stay hidden here.
const API = "http://127.0.0.1:8001";
const AUTH_EMULATOR = "http://127.0.0.1:9099";

async function idToken(page) {
  return page.evaluate(async () => {
    const db = await new Promise((resolve, reject) => {
      const req = indexedDB.open("firebaseLocalStorageDb");
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    const rows = await new Promise((resolve) => {
      const req = db.transaction("firebaseLocalStorage").objectStore("firebaseLocalStorage").getAll();
      req.onsuccess = () => resolve(req.result);
    });
    return rows.find((r) => r.value?.stsTokenManager).value.stsTokenManager.accessToken;
  });
}

test("export holds the user's run; delete removes the account and its data", async ({ page, request }) => {
  const email = freshEmail("delete");
  const password = "e2e-pass-123";
  await register(page, email, password);
  await runBacktest(page);
  const headers = { Authorization: `Bearer ${await idToken(page)}` };

  const exported = await request.get(`${API}/api/me/export`, { headers });
  expect(exported.status()).toBe(200);
  expect(exported.headers()["content-disposition"]).toMatch(/^attachment; filename="finertia-export-/);
  const body = await exported.json();
  expect(body.account.email).toBe(email);
  expect(body.runs).toHaveLength(1);
  expect(body.runs[0].ticker).toBe("AAPL");

  // Wrong confirmation: nothing happens.
  const refused = await request.delete(`${API}/api/me`, { headers, data: { confirm: "not-me@e2e.test" } });
  expect(refused.status()).toBe(400);
  expect((await (await request.get(`${API}/api/me/export`, { headers })).json()).runs).toHaveLength(1);

  const deleted = await request.delete(`${API}/api/me`, { headers, data: { confirm: email } });
  expect(deleted.status()).toBe(200);
  expect(await deleted.json()).toMatchObject({ deleted: true, runs: 1 });

  // The account is gone from Auth: the password no longer signs in.
  const signIn = await request.post(
    `${AUTH_EMULATOR}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=e2e`,
    { data: { email, password, returnSecureToken: true } },
  );
  expect(signIn.ok()).toBe(false);

  // And nothing is left behind under that uid.
  const after = await (await request.get(`${API}/api/me/export`, { headers })).json();
  expect(after.profile).toBeNull();
  expect(after.runs).toEqual([]);
});

test("Profile shows no export or delete buttons while the switch is off", async ({ page }) => {
  await register(page, freshEmail("noswitch"));
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Change password" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download my data" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Delete my account/ })).toHaveCount(0);
});
