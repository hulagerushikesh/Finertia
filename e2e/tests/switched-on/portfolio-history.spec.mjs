// Portfolio runs in History with SAVE_PORTFOLIO_RUNS on (the API's switch):
// a basket is kept like a single run, named by its holdings, and Re-run
// brings it back as a portfolio (by-hand check, 23 Oct: it was not kept).
import { test, expect } from "@playwright/test";
import { register, freshEmail, failOnPageErrors } from "../helpers.mjs";

test("a portfolio run is kept in History and re-runs as a portfolio", async ({ page }) => {
  const noErrors = failOnPageErrors(page);
  await register(page, freshEmail("basketrun"));

  await page.getByRole("button", { name: /^Advanced/ }).click();
  await page.getByRole("button", { name: "Portfolio", exact: true }).click();
  await page.getByRole("button", { name: /^Run portfolio/ }).first().click();
  await expect(page.getByText("Total return").first()).toBeVisible({ timeout: 30_000 });

  await page.getByRole("link", { name: "History" }).first().click();
  const row = page.getByRole("row", { name: /AAPL · MSFT/ });
  await expect(row).toBeVisible();
  await expect(row.getByRole("checkbox")).toBeDisabled();

  await row.getByRole("button", { name: "Re-run" }).click();
  await expect(page.getByRole("button", { name: /^Run portfolio/ }).first()).toBeVisible();
  noErrors();
});
