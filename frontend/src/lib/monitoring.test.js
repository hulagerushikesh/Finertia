import { describe, it, expect, vi } from "vitest";
import { stripQuery, scrubEvent, scrubBreadcrumb, initMonitoring } from "./monitoring";

describe("what leaves the browser", () => {
  it("strips query strings and fragments", () => {
    expect(stripQuery("https://f.in/dashboard?ticker=AAPL&start=2020-01-01#x")).toBe("https://f.in/dashboard");
    expect(stripQuery(undefined)).toBeUndefined();
  });

  // The dashboard URL holds the user's strategy settings; the referrer repeats it.
  it("an event keeps the path, the browser and the uid — nothing else", () => {
    const out = scrubEvent({
      request: {
        url: "https://f.in/dashboard?ticker=AAPL",
        query_string: "ticker=AAPL",
        cookies: "s=1",
        headers: { "User-Agent": "ua", Referer: "https://f.in/admin/users?search=a@b.com" },
      },
      user: { id: "u1", email: "a@b.com", ip_address: "1.2.3.4" },
    });
    expect(out.request).toEqual({ url: "https://f.in/dashboard", headers: { "User-Agent": "ua" } });
    expect(out.user).toEqual({ id: "u1" });
  });

  it("drops console breadcrumbs and strips URLs in the rest", () => {
    expect(scrubBreadcrumb({ category: "console", message: "token abc" })).toBeNull();
    expect(
      scrubBreadcrumb({ category: "fetch", data: { url: "https://api/api/admin/users?search=a@b.com", method: "GET" } }).data
    ).toEqual({ url: "https://api/api/admin/users", method: "GET" });
    expect(scrubBreadcrumb({ category: "navigation", data: { from: "/a?x=1", to: "/b?y=2" } }).data).toEqual({ from: "/a", to: "/b" });
  });
});

describe("initMonitoring", () => {
  it("is off in dev and tests", () => {
    expect(initMonitoring({ PROD: false, MODE: "test" })).toBe(false);
  });

  it("is off against the Firebase emulators even in a production build", () => {
    expect(initMonitoring({ PROD: true, VITE_FIREBASE_EMULATORS: "1" })).toBe(false);
  });

  it("an empty VITE_SENTRY_DSN switches it off", () => {
    expect(initMonitoring({ PROD: true, VITE_SENTRY_DSN: "" })).toBe(false);
  });
});
