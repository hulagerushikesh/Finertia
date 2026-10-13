/**
 * Hidden switches for finished work that is not shown yet.
 *
 * `VITE_FEATURES` is a comma-separated list, read at build time, e.g.
 * `VITE_FEATURES=free-validation,onboarding`. Unset on production while the
 * tester round runs, so testers see the same product throughout; set for
 * local development, the E2E run and, if wanted, Vercel preview builds.
 *
 * Read on every call rather than once at import, so tests can switch a
 * feature with `vi.stubEnv` without reloading modules.
 *
 * These hide UI only. Anything that matters for money or access is enforced
 * by the API (the free validation is `FREE_VALIDATIONS_PER_MONTH` there).
 */

export const FEATURES = ["free-validation", "onboarding", "account-data"];

export function feature(name) {
  const raw = import.meta.env.VITE_FEATURES || "";
  return raw
    .split(",")
    .map((s) => s.trim())
    .includes(name);
}
