import React, { Suspense } from "react";
import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { lazyPage } from "./lazyPage";

const Page = () => <p>the page</p>;

describe("lazyPage", () => {
  it("renders in the first commit once preloaded, without the fallback", async () => {
    const Lazy = lazyPage(() => Promise.resolve({ default: Page }));
    await Lazy.preload();
    render(
      <Suspense fallback={<p>loading</p>}>
        <Lazy />
      </Suspense>,
    );
    expect(screen.getByText("the page")).toBeInTheDocument();
    expect(screen.queryByText("loading")).not.toBeInTheDocument();
  });

  it("still loads on first render when nobody preloaded it", async () => {
    const Lazy = lazyPage(() => Promise.resolve({ default: Page }));
    render(
      <Suspense fallback={<p>loading</p>}>
        <Lazy />
      </Suspense>,
    );
    expect(screen.getByText("loading")).toBeInTheDocument();
    await act(async () => {});
    expect(screen.getByText("the page")).toBeInTheDocument();
  });
});
