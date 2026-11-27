import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import ValidationPanel from "./ValidationPanel";
import demoValidation from "../demoValidation.json";

// The working opens with every section visible.
beforeEach(() => {
  try {
    localStorage.setItem("finertia-validation-working", "open");
  } catch {
    /* private mode: the test below still renders the verdict card */
  }
});

/** The demo payload reshaped into what the API returns for one rule. */
function ruleValidation() {
  const wf = demoValidation.walk_forward;
  return {
    ...demoValidation,
    strategy: "rules",
    walk_forward: {
      ...wf,
      combinations_tested: 1,
      best_params: {},
      deflated: { ...wf.deflated, n_trials: 1, expected_max_sharpe: 0, effective_trials: { computable: false } },
      overfitting: { computable: false, reason: "Only one parameter combination fits this period." },
      snooping: { ...wf.snooping, n_candidates: 1, best: { ...wf.snooping.best, params: {} }, cells: wf.snooping.cells.slice(0, 1) },
      user_params: null,
    },
    rolling_walk_forward: {
      ...demoValidation.rolling_walk_forward,
      strategy: "rules",
      folds: demoValidation.rolling_walk_forward.folds.map((f) => ({ ...f, best_params: {} })),
    },
  };
}

describe("ValidationPanel for a user's own rule", () => {
  it("describes one rule as written, not a search over a grid", () => {
    render(<ValidationPanel data={ruleValidation()} />);
    expect(screen.getByText("your rule as written, nothing tuned")).toBeInTheDocument();
    expect(screen.getByText("Earlier part")).toBeInTheDocument();
    expect(screen.getByText(/cannot see rules you tried before it/)).toBeInTheDocument();
    expect(screen.getByText("Sharpe ratio against zero")).toBeInTheDocument();
    expect(screen.getByText("Your rule against holding")).toBeInTheDocument();
    // The figures that only price a search are left out.
    for (const gone of ["Best parameters found", "Noise bar", "Reality Check", "Chosen parameters", /combinations tested/]) {
      expect(screen.queryByText(gone)).toBeNull();
    }
  });

  it("keeps the search wording for a built-in strategy", () => {
    render(<ValidationPanel data={demoValidation} />);
    expect(screen.getByText("Best parameters found")).toBeInTheDocument();
    expect(screen.getByText("Deflated Sharpe ratio")).toBeInTheDocument();
    expect(screen.queryByText("your rule as written, nothing tuned")).toBeNull();
  });
});
