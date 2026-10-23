// The Pro wall with `calm-pro-wall` on: a free member who has used this
// month's validation (or has none) is told once, in the Validation panel,
// not by a red banner, a toast and the panel together (by-hand check, 23 Oct).
import { test, expect } from "@playwright/test";
import { register, runBacktest, freshEmail, failOnPageErrors } from "../helpers.mjs";

test("the plan boundary is said once, in the panel", async ({ page }) => {
  const noErrors = failOnPageErrors(page);
  await register(page, freshEmail("calmwall"));
  await runBacktest(page);

  // This server allows one free validation a month: spend it, then load the
  // run fresh so the next attempt meets the wall on an unvalidated run.
  await page.getByRole("tab", { name: /Validation/ }).click();
  await expect(page.getByTestId("free-validation-used")).toBeVisible({ timeout: 30_000 });
  await page.reload();
  await runBacktest(page);
  await page.getByRole("tab", { name: /Validation/ }).click();

  await expect(page.getByRole("link", { name: /see Pro/ })).toBeVisible();
  await expect(page.getByTestId("pro-wall-reason")).toBeVisible();
  // Said once on the whole page: no banner in #main, no toast.
  await expect(page.getByText(/used your free validation/)).toHaveCount(1);
  noErrors();
});
