import { describe, expect, it } from "vitest";

import { localeCookieMaxAge, localeCookieName } from "@/i18n/config";

import { POST } from "./route";

describe("locale Cookie endpoint", () => {
  it.each(["zh-CN", "en-US"])(
    "persists %s as the server locale source",
    async (locale) => {
      const response = await POST(
        new Request("http://localhost/api/locale", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ locale }),
        }),
      );

      expect(response.status).toBe(200);
      expect(await response.json()).toEqual({ locale });
      expect(response.headers.get("set-cookie")).toContain(
        `${localeCookieName}=${locale}`,
      );
      expect(response.headers.get("set-cookie")).toContain("Path=/");
      expect(response.headers.get("set-cookie")).toContain("HttpOnly");
      expect(response.headers.get("set-cookie")).toContain("SameSite=lax");
      expect(response.headers.get("set-cookie")).toContain(
        `Max-Age=${localeCookieMaxAge}`,
      );
    },
  );

  it("rejects an unsupported locale without setting a Cookie", async () => {
    const response = await POST(
      new Request("http://localhost/api/locale", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ locale: "fr-FR" }),
      }),
    );

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      error: { code: "unsupported_locale" },
    });
    expect(response.headers.get("set-cookie")).toBeNull();
  });
});
