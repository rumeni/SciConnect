import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  vi.resetModules();
  const store = new Map<string, string>();
  vi.stubGlobal("window", {
    __SCICONNECT__: { apiUrl: "http://api.example.test" },
    sessionStorage: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => { store.set(key, value); },
      removeItem: (key: string) => { store.delete(key); },
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("admin catalog credential rotation", () => {
  it("expires a stale admin session when the admin catalog returns 401", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "A valid admin token is required" }), {
        status: 401,
        headers: { "Content-Type": "application/json", "WWW-Authenticate": "Bearer" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { enterAsAdmin, session } = await import("./session");
    const { api, ApiError } = await import("./api");
    enterAsAdmin("old-token");
    await expect(api.adminInstitutions()).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/api/v1/admin/catalog/institutions",
      { headers: { Authorization: "Bearer old-token" } },
    );
    expect(session()).toMatchObject({ role: null, key: "", expired: true });
  });
});
