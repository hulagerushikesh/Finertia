// The admin Pro grant, and what it unlocks for the member who gets it.
// Uses the two seeded fixture accounts (backend/scripts/seed_e2e.py).
import { test, expect } from "@playwright/test";
import { USERS, login, runBacktest } from "./helpers.mjs";

test.describe.configure({ mode: "serial" });

async function memberRow(page) {
  await page.goto("/admin/users");
  const row = page.getByRole("row").filter({ hasText: USERS.member.email });
  await expect(row).toBeVisible();
  return row;
}

async function confirm(page) {
  await page.getByRole("button", { name: "Confirm" }).click();
}

test("a member cannot open the admin panel", async ({ page }) => {
  await login(page, USERS.member);
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "Admin Panel" })).toHaveCount(0);
});

test("admin gives Pro → member runs validation → admin removes Pro", async ({ browser }) => {
  test.setTimeout(180_000);

  const admin = await browser.newPage();
  await login(admin, USERS.admin);
  let row = await memberRow(admin);
  await row.getByRole("button", { name: "Give Pro" }).click();
  await confirm(admin);
  await expect(row.getByText("comp")).toBeVisible();

  const member = await browser.newPage();
  await login(member, USERS.member);
  await runBacktest(member);
  await member.getByRole("tab", { name: /Validation/ }).click();
  // The real validation suite on seeded prices: a verdict, not a wall.
  await expect(member.getByText(/checks? passed/i).first()).toBeVisible({ timeout: 120_000 });
  await expect(member.locator("#main").getByText(/Pro features/)).toHaveCount(0);

  row = await memberRow(admin);
  await row.getByRole("button", { name: "Remove Pro" }).click();
  await confirm(admin);
  await expect(row.getByRole("button", { name: "Give Pro" })).toBeVisible();
});

test("the Actions column lines up across rows", async ({ page }) => {
  await login(page, USERS.admin);
  await page.goto("/admin/users");
  await expect(page.getByRole("row").nth(2)).toBeVisible();
  // Each verb sits in the same horizontal slot on every row (#84).
  for (const name of [/^(Block|Unblock)$/, /^(Give|Remove) Pro$/, /^Make (Admin|User)$/]) {
    const lefts = await page
      .getByRole("button", { name })
      .evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().left)));
    expect(new Set(lefts).size, `${name} column`).toBe(1);
  }
});
