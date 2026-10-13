import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorBoundary from "./ErrorBoundary";

function Boom() {
  throw new Error("chart data was undefined");
}

describe("ErrorBoundary", () => {
  it("renders children when nothing throws", () => {
    render(<ErrorBoundary><p>fine</p></ErrorBoundary>);
    expect(screen.getByText("fine")).toBeInTheDocument();
  });

  it("shows a recovery screen with the error instead of a blank page", () => {
    // React logs caught render errors; keep the test output readable.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByRole("heading", { name: "Something broke on this page." })).toBeInTheDocument();
    expect(screen.getByText("chart data was undefined")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload Finertia" })).toBeInTheDocument();
    spy.mockRestore();
  });
});
