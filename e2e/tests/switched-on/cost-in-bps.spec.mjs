// Transaction cost with `cost-in-bps` on: entered in basis points, the unit
// the results report it in, and still sent to the API as a fraction
// (by-hand check, 23 Oct: the field took 0.001 while the result said 10 bps).
import { test, expect } from "@playwright/test";
import { register, runBacktest, freshEmail, failOnPageErrors } from "../helpers.mjs";

test("cost is entered in bps and sent as a fraction", async ({ page }) => {
  const noErrors = failOnPageErrors(page);
  await register(page, freshEmail("bps"));

  await page.getByRole("button", { name: /^Advanced/ }).click();
  const cost = page.getByLabel("Transaction cost (bps)");
  await expect(cost).toHaveValue("10");
  await cost.fill("25");

  const sent = page.waitForRequest((r) => r.url().endsWith("/api/backtest") && r.method() === "POST");
  await runBacktest(page);
  expect((await sent).postDataJSON().transaction_cost).toBeCloseTo(0.0025, 10);
  await expect(page.getByText(/at a flat 25 bps cost/)).toBeVisible();
  noErrors();
});
