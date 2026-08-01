import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import enUS from "../../messages/en-US.json";
import zhCN from "../../messages/zh-CN.json";

const testIntl = vi.hoisted<{ locale: "zh-CN" | "en-US" }>(() => ({
  locale: "en-US",
}));

vi.mock("next-intl", async (importOriginal) => {
  const original = await importOriginal<typeof import("next-intl")>();
  const translators = new Map<
    string,
    ReturnType<typeof original.createTranslator>
  >();
  return {
    ...original,
    useLocale: () => testIntl.locale,
    useTranslations: (namespace?: string) => {
      const cacheKey = `${testIntl.locale}:${namespace ?? ""}`;
      const cached = translators.get(cacheKey);
      if (cached) return cached;
      const translator = original.createTranslator({
        locale: testIntl.locale,
        messages: testIntl.locale === "zh-CN" ? zhCN : enUS,
        namespace: namespace as never,
      });
      translators.set(cacheKey, translator);
      return translator;
    },
  };
});

export function setTestLocale(locale: "zh-CN" | "en-US") {
  testIntl.locale = locale;
}

afterEach(() => {
  cleanup();
  testIntl.locale = "en-US";
});
