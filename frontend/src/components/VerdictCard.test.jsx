import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VerdictCard, { readChecks } from "./VerdictCard";

const wf = (verdict, extra = {}) => ({ walk_forward: { verdict, ...extra } });

describe("readChecks", () => {
  it("skips checks that did not run and maps unknown verdicts to 'unclear'", () => {
    const checks = readChecks({
      walk_forward: { verdict: "held_up", deflated: { computable: false } },
      permutation: { significant: true },
      rolling_walk_forward: { computable: true, verdict: "something_new" },
    });
    expect(checks.map((c) => c.id)).toEqual(["walk-forward", "rolling", "timing"]);
    expect(checks[1]).toMatchObject({ word: "unclear", tone: "faint" });
  });
});

describe("VerdictCard", () => {
  it("says 'Holds up' when every check passes", () => {
    render(<VerdictCard data={{ ...wf("held_up"), permutation: { significant: true } }} />);
    expect(screen.getByRole("heading", { name: "2 of 2 checks passed." })).toBeInTheDocument();
    expect(screen.getByText("Holds up")).toBeInTheDocument();
    expect(screen.getByText(/Every check agrees/)).toBeInTheDocument();
  });

  // Failing on unseen data outweighs anything else passing.
  it("says 'Not proven' when walk-forward fails, even if timing passes", () => {
    render(<VerdictCard data={{ ...wf("overfit"), permutation: { significant: true } }} />);
    expect(screen.getByText("Not proven")).toBeInTheDocument();
    expect(screen.getByText(/fitted too tightly/)).toBeInTheDocument();
  });

  it("says 'Mixed' for a warning", () => {
    render(<VerdictCard data={{ ...wf("weakened"), permutation: { significant: true } }} />);
    expect(screen.getByText("Mixed")).toBeInTheDocument();
  });

  it("handles a run where nothing could be judged", () => {
    render(<VerdictCard data={wf("inconclusive")} />);
    expect(screen.getByRole("heading", { name: /None of the checks could run/ })).toBeInTheDocument();
    expect(screen.getByText("Nothing to judge")).toBeInTheDocument();
  });

  it("jumps to a section when a chip is clicked", async () => {
    const onJump = vi.fn();
    render(<VerdictCard data={{ ...wf("held_up"), permutation: { significant: false } }} onJump={onJump} />);
    await userEvent.click(screen.getByRole("button", { name: /Timing vs luck/ }));
    expect(onJump).toHaveBeenCalledWith("timing");
  });
});
