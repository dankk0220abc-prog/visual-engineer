import { describe, expect, it } from "vitest";

import enUS from "../../messages/en-US.json";
import zhCN from "../../messages/zh-CN.json";

import { detectLocale, resolveLocale } from "./config";

function messageKeys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return [prefix];
  }

  return Object.entries(value).flatMap(([key, child]) =>
    messageKeys(child, prefix ? `${prefix}.${key}` : key),
  );
}

describe("locale resources", () => {
  it("keeps the zh-CN and en-US semantic key sets identical", () => {
    expect(messageKeys(zhCN).sort()).toEqual(messageKeys(enUS).sort());
  });
});

describe("locale resolution", () => {
  it.each([
    ["zh-CN,zh;q=0.9,en;q=0.8", "zh-CN"],
    ["zh-TW;q=0.8,en-US;q=0.7", "zh-CN"],
    ["fr-FR,en;q=0.8", "en-US"],
    ["en-US,zh;q=0.1", "en-US"],
    [null, "en-US"],
  ])("detects %s as %s", (header, expected) => {
    expect(detectLocale(header)).toBe(expected);
  });

  it("uses a supported Cookie before browser negotiation", () => {
    expect(resolveLocale("zh-CN", "en-US")).toBe("zh-CN");
    expect(resolveLocale("en-US", "zh-CN")).toBe("en-US");
  });

  it("ignores an invalid Cookie and safely negotiates the header", () => {
    expect(resolveLocale("de-DE", "zh-HK, en;q=0.5")).toBe("zh-CN");
  });
});
