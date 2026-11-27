import { describe, it, expect } from "vitest";
import React, { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import RuleBuilder, { DEFAULT_RULE } from "./RuleBuilder";
import { encodeParams, decodeParams, shareLinkFor } from "../utils/permalink";
import { DEFAULTS } from "./ConfigPanel";

/** The builder with real state, exposing the latest rule for assertions. */
function Harness({ start = DEFAULT_RULE, onRule }) {
  const [rule, setRule] = useState(start);
  return (
    <RuleBuilder
      rule={rule}
      onChange={(r) => {
        setRule(r);
        onRule(r);
      }}
    />
  );
}

function setup(start) {
  const seen = { rule: start || DEFAULT_RULE };
  render(<Harness start={start} onRule={(r) => (seen.rule = r)} />);
  return seen;
}

describe("RuleBuilder", () => {
  it("starts from a moving-average crossover", () => {
    setup();
    const [entry] = screen.getAllByTestId("rule-condition");
    expect(within(entry).getByLabelText("Entry condition 1 left: indicator")).toHaveValue("sma");
    expect(within(entry).getByLabelText("Entry condition 1: comparison")).toHaveValue("crosses_above");
  });

  it("builds an RSI dip rule as the API's JSON", async () => {
    const seen = setup();
    await userEvent.selectOptions(screen.getByLabelText("Entry condition 1 left: indicator"), "rsi");
    await userEvent.selectOptions(screen.getByLabelText("Entry condition 1: comparison"), "<");
    await userEvent.selectOptions(screen.getByLabelText("Entry condition 1 right: indicator"), "value");
    const number = screen.getByLabelText("Entry condition 1 right: number");
    await userEvent.clear(number);
    await userEvent.type(number, "30");
    expect(seen.rule.entry.all[0]).toEqual({ left: { ind: "rsi", n: 14 }, op: "<", right: { value: 30 } });
  });

  it("adds, combines with any, and removes conditions", async () => {
    const seen = setup();
    await userEvent.click(screen.getAllByRole("button", { name: /Add a condition/ })[0]);
    expect(seen.rule.entry.all).toHaveLength(2);
    await userEvent.selectOptions(screen.getByLabelText("Entry: combine conditions"), "any");
    expect(seen.rule.entry.any).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Remove Entry condition 2" }));
    expect(seen.rule.entry.any).toHaveLength(1);
  });

  it("takes MACD's own parameters and a short direction", async () => {
    const seen = setup();
    await userEvent.selectOptions(screen.getByLabelText("Exit condition 1 left: indicator"), "macd_signal");
    expect(seen.rule.exit.all[0].left).toEqual({ ind: "macd_signal", fast: 12, slow: 26, signal: 9 });
    await userEvent.selectOptions(screen.getByLabelText("Direction"), "short");
    expect(seen.rule.direction).toBe("short");
  });
});

describe("permalinks carry a rule", () => {
  const params = { ...DEFAULTS, strategy: "rules" };

  it("round-trips the rule through the URL", () => {
    const back = decodeParams(encodeParams(params));
    expect(back.strategy).toBe("rules");
    expect(back.rule).toEqual(DEFAULT_RULE);
  });

  it("leaves the rule out of a built-in strategy's link", () => {
    expect(encodeParams(DEFAULTS)).not.toContain("rule=");
  });

  it("keeps the default rule when the link's rule is mangled", () => {
    const back = decodeParams("strategy=rules&rule=%7Bnot-json");
    expect(back.rule).toEqual(DEFAULT_RULE);
  });

  it("shares a rule as a set-up link, since it has no preview card", () => {
    expect(shareLinkFor(params)).toContain("/dashboard?");
  });
});
