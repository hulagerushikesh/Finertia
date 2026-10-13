import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PasswordInput from "./PasswordInput";

describe("PasswordInput", () => {
  it("masks by default and toggles to readable text", async () => {
    render(<PasswordInput id="pw" value="hunter2" onChange={() => {}} />);
    const input = document.getElementById("pw");
    expect(input).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(input).toHaveAttribute("type", "text");
    await userEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(input).toHaveAttribute("type", "password");
  });

  it("reports the typed value, not the event", async () => {
    const onChange = vi.fn();
    render(<PasswordInput id="pw" value="" onChange={onChange} />);
    await userEvent.type(document.getElementById("pw"), "a");
    expect(onChange).toHaveBeenCalledWith("a");
  });
});
