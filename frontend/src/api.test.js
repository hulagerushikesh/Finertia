import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// The real module initialises Firebase; the API layer only needs currentUser.
const authState = vi.hoisted(() => ({ currentUser: null }));
vi.mock("./firebase", () => ({ auth: authState }));

import { runBacktest, getHistory, getAdminUsers, deleteMyAccount } from "./api";

function reply(status, body, headers = {}) {
  return Promise.resolve(
    new Response(body === undefined ? "not json" : JSON.stringify(body), { status, headers })
  );
}

let fetchMock;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  authState.currentUser = null;
});
afterEach(() => vi.unstubAllGlobals());

describe("apiFetch error messages", () => {
  it("passes a string detail through", async () => {
    fetchMock.mockReturnValue(reply(402, { detail: "Validation is a Pro feature." }));
    await expect(runBacktest({})).rejects.toMatchObject({
      message: "Validation is a Pro feature.",
      status: 402,
    });
  });

  // A 422 detail is an array of {loc, msg}; it used to render as "[object Object]".
  it("turns a 422 array into readable lines, naming the field and dropping 'Value error,'", async () => {
    fetchMock.mockReturnValue(
      reply(422, {
        detail: [
          { loc: ["body"], msg: "Value error, Date range 2024-01-01 → 2024-01-06 is too short" },
          { loc: ["body", "ticker"], msg: "Field required" },
        ],
      })
    );
    const err = await runBacktest({}).catch((e) => e);
    expect(err.message).toBe("Date range 2024-01-01 → 2024-01-06 is too short\nticker: Field required");
    expect(err.message).not.toContain("[object Object]");
  });

  it("falls back to the status when the body is not JSON", async () => {
    fetchMock.mockReturnValue(reply(500, undefined));
    await expect(runBacktest({})).rejects.toThrow("Unknown error");
  });

  it("falls back to HTTP <status> for an empty detail", async () => {
    fetchMock.mockReturnValue(reply(503, { detail: [] }));
    await expect(runBacktest({})).rejects.toThrow("HTTP 503");
  });

  it("carries the request id and Retry-After for the UI", async () => {
    fetchMock.mockReturnValue(
      reply(429, { detail: "Slow down" }, { "Retry-After": "12", "X-Request-Id": "req-abc" })
    );
    const err = await runBacktest({}).catch((e) => e);
    expect(err.retryAfter).toBe(12);
    expect(err.requestId).toBe("req-abc");
  });

  it("explains an unreachable API instead of 'Failed to fetch'", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(runBacktest({})).rejects.toThrow(/Cannot reach the API/);
  });
});

describe("apiFetch requests", () => {
  it("sends the Firebase ID token when signed in", async () => {
    authState.currentUser = { getIdToken: () => Promise.resolve("tok-123") };
    fetchMock.mockReturnValue(reply(200, { ok: true }));
    await runBacktest({ ticker: "AAPL" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer tok-123");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ ticker: "AAPL" });
  });

  it("sends no Authorization header when signed out", async () => {
    fetchMock.mockReturnValue(reply(200, []));
    await getHistory();
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/history\?limit=20&offset=0$/);
  });

  it("encodes the admin search term", async () => {
    fetchMock.mockReturnValue(reply(200, {}));
    await getAdminUsers(50, 0, "a+b@x.com");
    expect(fetchMock.mock.calls[0][0]).toContain("search=a%2Bb%40x.com");
  });

  it("sends the typed confirmation with an account deletion", async () => {
    fetchMock.mockReturnValue(reply(200, { deleted: true }));
    await deleteMyAccount("me@x.com");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/me$/);
    expect(init.method).toBe("DELETE");
    expect(JSON.parse(init.body)).toEqual({ confirm: "me@x.com" });
  });
});
