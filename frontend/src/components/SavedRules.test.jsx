import { describe, it, expect, vi, beforeEach } from "vitest";
import React, { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const api = vi.hoisted(() => ({
  listRules: vi.fn(),
  saveRule: vi.fn(),
  updateRule: vi.fn(),
  deleteRule: vi.fn(),
}));
vi.mock("../api", () => api);

import SavedRules from "./SavedRules";
import { DEFAULT_RULE } from "./RuleBuilder";

const RSI = {
  direction: "long",
  entry: { all: [{ left: { ind: "rsi", n: 14 }, op: "<", right: { value: 30 } }] },
  exit: { all: [{ left: { ind: "rsi", n: 14 }, op: ">", right: { value: 55 } }] },
};
const SAVED = { id: "r1", name: "RSI dip", rule: RSI, createdAt: "2026-11-28", updatedAt: "2026-11-28" };

function Harness() {
  const [rule, setRule] = useState(DEFAULT_RULE);
  return (
    <>
      <SavedRules rule={rule} onLoad={setRule} />
      <p data-testid="rule">{JSON.stringify(rule)}</p>
    </>
  );
}

beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
});

describe("SavedRules", () => {
  it("loads a saved rule into the builder", async () => {
    api.listRules.mockResolvedValue({ rules: [SAVED], max: 20 });
    render(<Harness />);
    await userEvent.selectOptions(await screen.findByLabelText("Saved rules"), "r1");
    expect(screen.getByTestId("rule")).toHaveTextContent('"ind":"rsi"');
    expect(screen.getByRole("button", { name: "Update “RSI dip”" })).toBeInTheDocument();
  });

  it("saves the current rule under a name", async () => {
    api.listRules.mockResolvedValueOnce({ rules: [], max: 20 }).mockResolvedValue({ rules: [{ ...SAVED, rule: DEFAULT_RULE, name: "Cross" }], max: 20 });
    api.saveRule.mockResolvedValue({ ...SAVED, name: "Cross" });
    render(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Save as…" }));
    await userEvent.type(screen.getByLabelText("Rule name"), "Cross");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(api.saveRule).toHaveBeenCalledWith("Cross", DEFAULT_RULE);
    expect(await screen.findByRole("status")).toHaveTextContent("Saved as “Cross”.");
  });

  it("shows the server's reason when a save is refused", async () => {
    api.listRules.mockResolvedValue({ rules: [SAVED], max: 20 });
    api.saveRule.mockRejectedValue(new Error("You already have a rule called “RSI dip”."));
    render(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: "Save as…" }));
    await userEvent.type(screen.getByLabelText("Rule name"), "RSI dip");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("status")).toHaveTextContent("already have a rule");
  });

  it("deletes the loaded rule", async () => {
    api.listRules.mockResolvedValueOnce({ rules: [SAVED], max: 20 }).mockResolvedValue({ rules: [], max: 20 });
    api.deleteRule.mockResolvedValue({});
    render(<Harness />);
    await userEvent.selectOptions(await screen.findByLabelText("Saved rules"), "r1");
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(api.deleteRule).toHaveBeenCalledWith("r1");
    expect(await screen.findByText("No saved rules yet")).toBeInTheDocument();
  });

  it("stays out of the way when the list cannot be read", async () => {
    api.listRules.mockRejectedValue(new Error("Not Found"));
    const { container } = render(<Harness />);
    await Promise.resolve();
    expect(container.querySelector('[data-testid="saved-rules"]')).toBeNull();
  });

  it("stops offering to save at the limit", async () => {
    api.listRules.mockResolvedValue({ rules: [SAVED], max: 1 });
    render(<Harness />);
    expect(await screen.findByRole("button", { name: "Save as…" })).toBeDisabled();
    expect(screen.getByText(/the most there is room for/)).toBeInTheDocument();
  });
});
