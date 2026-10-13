import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

const api = vi.hoisted(() => ({ exportMyData: vi.fn(), deleteMyAccount: vi.fn() }));
vi.mock("../api", () => api);
const auth = vi.hoisted(() => ({ user: null, userProfile: null, logout: vi.fn() }));
vi.mock("../hooks/useAuth", () => ({ useAuth: () => auth }));
const toast = vi.hoisted(() => vi.fn());
vi.mock("../hooks/useToast", () => ({ useToast: () => ({ showToast: toast }) }));

import { useLocation } from "react-router-dom";
import AccountData from "./AccountData";

function GonePage() {
  return <p>gone page {String(useLocation().state?.deleted)}</p>;
}

const renderIt = () => render(
  <MemoryRouter initialEntries={["/profile"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Routes>
      <Route path="/profile" element={<AccountData />} />
      <Route path="/account-deleted" element={<GonePage />} />
    </Routes>
  </MemoryRouter>
);

beforeEach(() => {
  api.exportMyData.mockReset();
  api.deleteMyAccount.mockReset();
  auth.logout.mockReset().mockResolvedValue();
  toast.mockReset();
  auth.user = { email: "Me@Example.com" };
  auth.userProfile = { role: "user", totalRuns: 3 };
});

const openConfirm = () => fireEvent.click(screen.getByRole("button", { name: "Delete my account…" }));
const confirmBox = () => screen.getByLabelText("Type your email address to confirm");
const deleteButton = () => screen.getByRole("button", { name: "Delete my account for good" });

describe("AccountData — export", () => {
  it("downloads the export as a dated JSON file", async () => {
    api.exportMyData.mockResolvedValue({ exported_at: "2026-10-13T10:00:00Z", runs: [] });
    URL.createObjectURL = vi.fn(() => "blob:x");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderIt();
    fireEvent.click(screen.getByRole("button", { name: "Download my data" }));
    await waitFor(() => expect(click).toHaveBeenCalled());
    expect(click.mock.contexts[0].download).toBe("finertia-export-2026-10-13.json");
    expect(toast).toHaveBeenCalledWith("Your data is downloading.", "success");
    click.mockRestore();
  });

  it("says when the export fails", async () => {
    api.exportMyData.mockRejectedValue(new Error("HTTP 500"));
    renderIt();
    fireEvent.click(screen.getByRole("button", { name: "Download my data" }));
    await waitFor(() => expect(toast).toHaveBeenCalledWith("Could not export your data — HTTP 500", "error"));
  });
});

describe("AccountData — delete", () => {
  it("only enables deletion once the account's email is typed", () => {
    renderIt();
    openConfirm();
    expect(screen.getByText(/every saved run and your sign-in/)).toBeInTheDocument();
    expect(deleteButton()).toBeDisabled();
    fireEvent.change(confirmBox(), { target: { value: "someone@else.com" } });
    expect(deleteButton()).toBeDisabled();
    // Case and surrounding spaces don't matter, as on the server.
    fireEvent.change(confirmBox(), { target: { value: "  me@example.COM " } });
    expect(deleteButton()).toBeEnabled();
  });

  it("deletes, then hands over to the goodbye page", async () => {
    api.deleteMyAccount.mockResolvedValue({ deleted: true });
    renderIt();
    openConfirm();
    fireEvent.change(confirmBox(), { target: { value: "me@example.com" } });
    fireEvent.click(deleteButton());
    expect(await screen.findByText("gone page true")).toBeInTheDocument();
    expect(api.deleteMyAccount).toHaveBeenCalledWith("me@example.com");
  });

  it("shows the server's refusal and stays signed in", async () => {
    api.deleteMyAccount.mockRejectedValue(new Error("Cancel your subscription before deleting the account."));
    renderIt();
    openConfirm();
    fireEvent.change(confirmBox(), { target: { value: "me@example.com" } });
    fireEvent.click(deleteButton());
    expect(await screen.findByText("Cancel your subscription before deleting the account.")).toBeInTheDocument();
    expect(auth.logout).not.toHaveBeenCalled();
    expect(deleteButton()).toBeEnabled();
  });

  it("cancel closes the confirmation and forgets what was typed", () => {
    renderIt();
    openConfirm();
    fireEvent.change(confirmBox(), { target: { value: "me@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    openConfirm();
    expect(confirmBox()).toHaveValue("");
  });

  it("offers no delete button to an admin", () => {
    auth.userProfile = { role: "admin" };
    renderIt();
    expect(screen.getByTestId("delete-admin-note")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete my account…" })).toBeNull();
  });
});
