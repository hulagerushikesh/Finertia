import { describe, it, expect } from "vitest";
import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ConfigPanel, { DEFAULTS } from "./ConfigPanel";
import { marketCost } from "./CostModelField";
import { encodeParams, decodeParams } from "../utils/permalink";
import table from "../lib/costModels.json";

function Harness() {
  const [params, setParams] = useState(DEFAULTS);
  return (
    <>
      <ConfigPanel params={params} setParams={setParams} onRun={() => {}} loading={false} />
      <output data-testid="state">{JSON.stringify(params)}</output>
    </>
  );
}
const state = () => JSON.parse(screen.getByTestId("state").textContent);

describe("marketCost", () => {
  it("matches the server's figure at the default slippage", () => {
    for (const [id, m] of Object.entries(table.models)) {
      expect(marketCost(id, table.default_slippage_bps).perSide).toBeCloseTo(m.per_side, 9);
    }
  });

  it("moves one for one with slippage", () => {
    const a = marketCost("india", 0).perSide;
    const b = marketCost("india", 5).perSide;
    expect((b - a) * 10000).toBeCloseTo(5, 9);
  });

  it("puts STT at the top of the Indian bill", () => {
    const parts = marketCost("india", 2).parts;
    const stt = parts.find((p) => p.label === "Securities transaction tax");
    expect(stt.perSide).toBeCloseTo(0.001, 9);
    expect(Math.max(...parts.map((p) => p.perSide))).toBe(stt.perSide);
  });
});

describe("cost model in the workspace", () => {
  it("switches to India and shows where the number comes from", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByText("Advanced"));
    await userEvent.click(screen.getByRole("button", { name: "India" }));
    expect(state().cost_model).toBe("india");
    expect(screen.getByTestId("market-cost")).toHaveTextContent("13.12 bps a side");
    const slip = screen.getByLabelText("Slippage (bps a side)");
    await userEvent.clear(slip);
    await userEvent.type(slip, "5");
    expect(state().slippage_bps).toBe(5);
    expect(screen.getByTestId("market-cost")).toHaveTextContent("16.12 bps a side");
  });

  it("travels in a set-up link, and a flat link stays as it was", () => {
    const india = { ...DEFAULTS, cost_model: "india", slippage_bps: 4 };
    const back = decodeParams(encodeParams(india));
    expect([back.cost_model, back.slippage_bps]).toEqual(["india", 4]);
    expect(encodeParams(india)).not.toContain("transaction_cost");
    const flat = encodeParams(DEFAULTS);
    expect(flat).not.toContain("cost_model");
    expect(flat).toContain("transaction_cost=0.001");
    expect(decodeParams("strategy=momentum&cost_model=uk").cost_model).toBe("flat");
  });
});
