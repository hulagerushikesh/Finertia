// Share cards: with `share-cards` on (and SHARE_CARDS=1 on the API), the
// copy-link button copies /api/share?…, which previews as this run's card in
// a chat and sends a person on to the same set-up in the workspace.
import { test, expect } from "@playwright/test";
import { register, runBacktest, freshEmail, failOnPageErrors } from "../helpers.mjs";

test("the copied link previews as a card and opens the same set-up", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const noErrors = failOnPageErrors(page);
  await register(page, freshEmail("share"));
  await runBacktest(page);

  await page.getByRole("button", { name: "Copy link to this set-up" }).click();
  const link = await page.evaluate(() => navigator.clipboard.readText());
  expect(link).toContain("/api/share?");

  // What a chat app's crawler sees: the run's figures, and a card to fetch.
  const preview = await page.request.get(link);
  expect(preview.status()).toBe(200);
  const html = await preview.text();
  expect(html).toMatch(/property="og:title" content="\w[^"]* on [A-Z.^-]+, \d{4} to \d{4}"/);
  const card = new URL(html.match(/property="og:image" content="([^"]+)"/)[1].replaceAll("&amp;", "&"));
  const image = await page.request.get(card.pathname + card.search);
  expect(image.headers()["content-type"]).toBe("image/png");

  // What a person sees: the workspace, on the same set-up.
  const ticker = new URL(link).searchParams.get("ticker");
  await page.goto(link);
  await expect(page).toHaveURL(new RegExp(`/dashboard\\?ticker=${ticker}&`));
  noErrors();
});
