// Logged-out pages: what a visitor sees before signing up.
import { test, expect } from "@playwright/test";
import { failOnPageErrors } from "./helpers.mjs";

const TITLES = {
  "/demo": "Momentum on Apple, 2019–2024: a real result · Finertia",
  "/limits": "Limits · Finertia",
  "/privacy": "Privacy · Finertia",
  "/terms": "Terms of use · Finertia",
  "/docs": "How it works · Finertia",
  "/support": "Support · Finertia",
  "/writeup": "The best-looking strategy was the worst on new data · Finertia",
};

test("each public page names itself on the tab, and the landing title comes back after", async ({ page }) => {
  for (const [path, title] of Object.entries(TITLES)) {
    await page.goto(path);
    await expect(page).toHaveTitle(title);
  }
  await page.getByRole("link", { name: "Finertia" }).first().click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page).toHaveTitle("Finertia — Test a trading idea before you risk money on it");
});

for (const path of ["/", "/limits", "/privacy", "/terms", "/writeup", "/docs"]) {
  test(`${path} loads without errors`, async ({ page }) => {
    const noErrors = failOnPageErrors(page);
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    noErrors();
  });
}

// Personal, non-commercial project (DECISIONS 24 Nov): an old pricing link
// lands on the limits, and nothing on the way offers a plan to buy.
test("/pricing lands on the limits, with nothing for sale", async ({ page }) => {
  await page.goto("/pricing");
  await expect(page).toHaveURL(/\/limits$/);
  await expect(page.locator("main")).not.toContainText(/\$\d|\bPro\b|upgrade/i);
});

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
