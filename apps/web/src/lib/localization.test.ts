import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";

import enUS from "../../messages/en-US.json";
import zhCN from "../../messages/zh-CN.json";
import { ApiError } from "./api";
import {
  localizeApiError,
  localizeErrorCode,
  localizeStatus,
} from "./localization";

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
    const result = localizeErrorCode(
      "future_error_code",
      errorTranslator("zh-CN"),
      "req-future-42",
    );

    expect(result).toContain("future_error_code");
    expect(result).toContain("req-future-42");
  });

  it.each([
    ["en-US", "The Delivery Authorization expired before dispatch"],
    ["zh-CN", "交付授权在派发前已过期"],
  ] as const)("localizes a Delivery lifecycle code in %s", (locale, copy) => {
    const result = localizeErrorCode(
      "delivery_authorization_expired",
      errorTranslator(locale),
      "req-delivery-7",
    );

    expect(result).toContain(copy);
    expect(result).toContain("delivery_authorization_expired");
    expect(result).toContain("req-delivery-7");
  });

  it("uses a specific mapping for a known conflict code", () => {
    const result = localizeApiError(
      new ApiError("server-authored prose", {
        status: 409,
        code: "delivery_readiness_required",
        requestId: "req-delivery-ready",
      }),
      errorTranslator("zh-CN"),
    );

    expect(result).toContain("准确、新鲜、已批准且就绪");
    expect(result).toContain("delivery_readiness_required");
    expect(result).toContain("req-delivery-ready");
    expect(result).not.toContain("server-authored prose");
  });
});

describe("status localization", () => {
  function statusTranslator(locale: "zh-CN" | "en-US") {
    const translator = createTranslator({
      locale,
      messages: locale === "zh-CN" ? zhCN : enUS,
      namespace: "common.status",
    });
    return (key: string, values?: Record<string, string | number>) =>
      translator(key as never, values as never);
  }

  it.each([
    ["sealed", "已封存"],
    ["not_ready", "尚未就绪"],
    ["skipped", "已跳过"],
  ])("localizes %s in zh-CN", (status, copy) => {
    expect(localizeStatus(status, statusTranslator("zh-CN"))).toBe(copy);
  });

  it("uses a localized fallback while retaining an unknown status code", () => {
    expect(localizeStatus("future_state", statusTranslator("zh-CN"))).toContain(
      "future_state",
    );
  });
});
