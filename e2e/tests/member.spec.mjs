// A new free member, end to end. Each test registers its own account.
import { test, expect } from "@playwright/test";
import { register, runBacktest, freshEmail, failOnPageErrors } from "./helpers.mjs";

test("register → unverified banner → run a backtest", async ({ page }) => {
  const noErrors = failOnPageErrors(page);
  await register(page, freshEmail("run"));
  // Email verification is a nudge, not a gate (DECISIONS 13 Oct): the
  // banner shows and the workspace still works.
  await expect(page.getByText("Confirm your email address.")).toBeVisible();
  await runBacktest(page);
  await expect(page.getByRole("heading", { name: "AAPL" })).toBeVisible();
  noErrors();
});

// Tester bugs #6 and #7, 12 Oct (fixed in #84): clearing the ticker box after
// a run sent an empty validation request, so a free user saw "ticker missing"
// before the Pro wall.
test("Validation checks the run on screen, and a free user goes straight to the Pro wall", async ({ page }) => {
  await register(page, freshEmail("prowall"));
  await runBacktest(page);

  await page.getByLabel("Ticker").fill("");
  await page.getByRole("tab", { name: /Validation/ }).click();

  await expect(page.getByRole("link", { name: "Validation is on Pro — see plans" })).toBeVisible();
  // The toast repeats the message; the banner in the page is the one to read.
  await expect(page.locator("#main").getByText(/Pro features/)).toBeVisible();
  await expect(page.locator("#main").getByText(/ticker/i).filter({ hasText: /required|missing|field/i })).toHaveCount(0);
  // The result header still names the run, not the emptied box.
  await expect(page.getByRole("heading", { name: "AAPL" })).toBeVisible();

  // Nor the strategy picked since (by-hand check, 23 Oct): choosing MACD
  // without running it relabelled the Momentum result "MACD".
  await page.getByRole("button", { name: "MACD", exact: true }).click();
  const header = page.getByRole("heading", { name: "AAPL" }).locator("..");
  await expect(header.getByText("Momentum", { exact: true })).toBeVisible();
  await expect(header.getByText("MACD", { exact: true })).toHaveCount(0);
});

// Tester bug #2, 12 Oct (fixed in #84): a dd/mm reading of the date turned a
// five-month range into five days; the error now shows the dates it parsed.
test("a too-short range names the dates it read", async ({ page }) => {
  await register(page, freshEmail("dates"));
  await page.getByRole("button", { name: "MACD" }).click();
  await page.getByLabel("Start").fill("2024-01-01");
  await page.getByLabel("End").fill("2024-01-06");
  await page.getByRole("button", { name: /^Run backtest/ }).first().click();
  await expect(page.locator("#main").getByText(/2024-01-01 → 2024-01-06 is too short/)).toBeVisible();
});

test("a run appears in History and re-opens in the workspace", async ({ page }) => {
  await register(page, freshEmail("history"));
  await runBacktest(page);
  await page.goto("/history");
  await expect(page.getByRole("heading", { name: "History" })).toBeVisible();
  await expect(page.getByText("AAPL").first()).toBeVisible();
  await page.getByRole("button", { name: "Re-run" }).first().click();
  await page.waitForURL("**/dashboard**");
  await expect(page.getByLabel("Ticker")).toHaveValue("AAPL");
});

// Tester report, 13 Oct: leaving the workspace for History and coming back
// emptied it, and getting the answer back cost another monthly run. Moves
// through the navbar, not page.goto: a reload is a fresh start by design.
test("the workspace keeps its run across a trip to History", async ({ page }) => {
  await register(page, freshEmail("keep"));
  await runBacktest(page);
  let backtests = 0;
  page.on("request", (r) => r.url().includes("/api/backtest") && r.method() === "POST" && backtests++);

  await page.getByRole("link", { name: "History" }).first().click();
  await expect(page.getByRole("heading", { name: "History" })).toBeVisible();
  await page.getByRole("link", { name: "Workspace" }).first().click();

  // In #main: the "AAPL complete" toast also says "total return". Exact: the
  // empty state's heading is "Run AAPL and see what comes back".
  const main = page.locator("#main");
  await expect(main.getByRole("heading", { name: "AAPL", exact: true })).toBeVisible();
  await expect(main.getByText("Total return").first()).toBeVisible();
  await expect(main.getByText("Nothing run yet", { exact: false })).toHaveCount(0);
  expect(backtests).toBe(0);
});

test("Profile saves a display name", async ({ page }) => {
  await register(page, freshEmail("profile"));
  await page.goto("/profile");
  await page.getByLabel("Display name").fill("E2E Tester");
  await page.getByRole("button", { name: "Save" }).first().click();
  await expect(page.getByText("Display name updated.")).toBeVisible();
});
