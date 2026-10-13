import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const auth = vi.hoisted(() => ({ user: { uid: "u1" }, logout: vi.fn() }));
vi.mock("../hooks/useAuth", () => ({ useAuth: () => auth }));

import AccountDeletedPage from "./AccountDeletedPage";

const renderAt = (entry) => render(
  <MemoryRouter initialEntries={[entry]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <AccountDeletedPage />
  </MemoryRouter>
);

beforeEach(() => {
  auth.logout.mockReset().mockResolvedValue();
  window.scrollTo = vi.fn();
});

describe("AccountDeletedPage", () => {
  it("signs the browser out when arriving from a deletion", () => {
    renderAt({ pathname: "/account-deleted", state: { deleted: true } });
    expect(screen.getByRole("heading", { name: "Your account is deleted." })).toBeInTheDocument();
    expect(auth.logout).toHaveBeenCalledTimes(1);
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("signs nobody out on a plain visit", () => {
    renderAt("/account-deleted");
    expect(auth.logout).not.toHaveBeenCalled();
  });
});
