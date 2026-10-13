import { readFileSync } from "node:fs";
import { expect } from "@playwright/test";

export const USERS = JSON.parse(
  readFileSync(new URL("../fixtures/users.json", import.meta.url), "utf8"),
);

/** A fresh address per call, so a test never trips over an earlier run. */
export function freshEmail(tag) {
  return `${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@e2e.test`;
}

export async function register(page, email, password = "e2e-pass-123") {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/dashboard**");
}

export async function login(page, { email, password }) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard**");
}

/** Run the backtest currently set up in the panel and wait for the result. */
export async function runBacktest(page) {
  await page.getByRole("button", { name: /^Run backtest/ }).first().click();
  await expect(page.getByText("Total return").first()).toBeVisible({ timeout: 30_000 });
}

/** Fail the test on any uncaught page error. */
export function failOnPageErrors(page) {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  return () => expect(errors, "uncaught page errors").toEqual([]);
}
