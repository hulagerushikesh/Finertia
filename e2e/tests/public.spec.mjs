// Logged-out pages: what a visitor sees before signing up.
import { test, expect } from "@playwright/test";
import { failOnPageErrors } from "./helpers.mjs";

for (const path of ["/", "/pricing", "/writeup", "/docs"]) {
  test(`${path} loads without errors`, async ({ page }) => {
    const noErrors = failOnPageErrors(page);
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    noErrors();
  });
}

test("/demo shows a result and its validation verdict without an account", async ({ page }) => {
  const noErrors = failOnPageErrors(page);
  await page.goto("/demo");
  await expect(page.getByText("Total return").first()).toBeVisible();
  await page.getByRole("tab", { name: /Validation/ }).click();
  await expect(page.getByText(/checks? passed/i).first()).toBeVisible();
  noErrors();
});

test("/demo has no horizontal scroll on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/demo");
  await expect(page.getByText("Total return").first()).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("the dashboard sends a logged-out visitor to sign in", async ({ page }) => {
  await page.goto("/dashboard");
  await page.waitForURL(/\/(login|register)/);
});
