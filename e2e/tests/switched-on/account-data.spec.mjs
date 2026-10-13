// Sprint 2 item 4 with its switch on: Profile → download my data, then
// delete the account, against the real API and the Auth/Firestore emulators.
import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
import { register, runBacktest, freshEmail, failOnPageErrors } from "../helpers.mjs";

const AUTH_EMULATOR = "http://127.0.0.1:9099";

test("a member downloads their data, then deletes the account for good", async ({ page, request }) => {
  const noErrors = failOnPageErrors(page);
  const email = freshEmail("acctdata");
  const password = "e2e-pass-123";
  await register(page, email, password);
  await runBacktest(page);
  await page.goto("/profile");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download my data" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^finertia-export-\d{4}-\d{2}-\d{2}\.json$/);
  const body = JSON.parse(readFileSync(await download.path(), "utf8"));
  expect(body.account.email).toBe(email);
  expect(body.runs).toHaveLength(1);

  await page.getByRole("button", { name: "Delete my account…" }).click();
  const remove = page.getByRole("button", { name: "Delete my account for good" });
  await expect(remove).toBeDisabled();
  await page.getByLabel("Type your email address to confirm").fill(email.toUpperCase());
  await remove.click();

  await page.waitForURL("**/account-deleted");
  await expect(page.getByRole("heading", { name: "Your account is deleted." })).toBeVisible();
  // Signed out: the navbar offers sign-in again, and /profile sends to login.
  await page.goto("/profile");
  await page.waitForURL("**/login");

  // The password no longer signs in.
  const signIn = await request.post(
    `${AUTH_EMULATOR}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=e2e`,
    { data: { email, password, returnSecureToken: true } },
  );
  expect(signIn.ok()).toBe(false);
  noErrors();
});
