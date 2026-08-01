import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";

import enUS from "../../messages/en-US.json";
import zhCN from "../../messages/zh-CN.json";
import { ApiError } from "./api";
import { localizeApiError } from "./localization";

function errorTranslator(locale: "zh-CN" | "en-US") {
  const translator = createTranslator({
    locale,
    messages: locale === "zh-CN" ? zhCN : enUS,
    namespace: "errors",
  });
  return (key: string, values?: Record<string, string | number>) =>
    translator(key as never, values as never);
}

describe("API error localization", () => {
  it.each([
    ["en-US", "The state changed"],
    ["zh-CN", "状态已经变化"],
  ] as const)(
    "maps a stable conflict in %s and preserves diagnostics",
    (locale, copy) => {
      const result = localizeApiError(
        new ApiError("server-authored prose", {
          status: 409,
          code: "stale_lease",
          requestId: "req-raw-123",
        }),
        errorTranslator(locale),
      );

      expect(result).toContain(copy);
      expect(result).toContain("stale_lease");
      expect(result).toContain("req-raw-123");
      expect(result).not.toContain("server-authored prose");
    },
  );

  it("uses a safe localized fallback and retains an unknown diagnostic code", () => {
    const result = localizeApiError(
      new ApiError("opaque upstream message", {
        status: 500,
        code: "future_error_code",
      }),
      errorTranslator("zh-CN"),
    );

    expect(result).toContain("future_error_code");
    expect(result).not.toContain("opaque upstream message");
  });
});
