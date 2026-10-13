// Sprint 2 item 2 with its switches on: the free plan's one validation a
// month, end to end against the real API and Firestore emulator.
import { test, expect } from "@playwright/test";
import { register, runBacktest, freshEmail, failOnPageErrors } from "../helpers.mjs";

test("a free member gets one validation, then the Pro wall names it", async ({ page }) => {
  const noErrors = failOnPageErrors(page);
  await register(page, freshEmail("freeval"));
  await runBacktest(page);

  await page.getByRole("tab", { name: /Validation/ }).click();
  await expect(page.getByTestId("free-validation-used")).toHaveText(
    /That was a free validation: 0 of 1 left this month/,
    { timeout: 30_000 },
  );

  // The second one this month is refused by the API, with the reason.
  await page.getByRole("button", { name: "Re-run checks" }).click();
  await expect(page.locator("#main").getByText(/used your free validation/)).toBeVisible();

  // And the profile's usage meter agrees.
  await page.goto("/profile");
  await expect(page.getByText("0 of 1 free left")).toBeVisible();
  noErrors();
});
