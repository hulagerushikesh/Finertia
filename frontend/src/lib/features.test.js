import { afterEach, describe, it, expect, vi } from "vitest";
import { feature } from "./features";

afterEach(() => vi.unstubAllEnvs());

describe("feature switches", () => {
  it("are off when nothing is set", () => {
    vi.stubEnv("VITE_FEATURES", "");
    expect(feature("free-validation")).toBe(false);
  });

  it("read a comma-separated list, spaces allowed", () => {
    vi.stubEnv("VITE_FEATURES", "onboarding, free-validation");
    expect(feature("free-validation")).toBe(true);
    expect(feature("onboarding")).toBe(true);
    expect(feature("account-data")).toBe(false);
  });

  it("match whole names only", () => {
    vi.stubEnv("VITE_FEATURES", "free-validation-v2");
    expect(feature("free-validation")).toBe(false);
  });
});
