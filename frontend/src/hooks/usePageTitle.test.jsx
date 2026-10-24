import React, { StrictMode } from "react";
import { render } from "@testing-library/react";
import { expect, it } from "vitest";
import { usePageTitle } from "./usePageTitle";
import { DEFAULT_TITLE, PAGE_META } from "../lib/pageMeta";

function Page() {
  usePageTitle("demo");
  return null;
}

it("sets the page's title, and puts the landing title back on leaving, under StrictMode", () => {
  document.title = DEFAULT_TITLE;
  const { unmount } = render(<StrictMode><Page /></StrictMode>);
  expect(document.title).toBe(PAGE_META.demo.title);
  unmount();
  expect(document.title).toBe(DEFAULT_TITLE);
});
