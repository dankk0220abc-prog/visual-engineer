import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { setTestLocale } from "@/test/setup";

import { StatusPill } from "./status-pill";

describe("StatusPill semantic selector", () => {
  it.each([
    ["en-US", "online", "Online"],
    ["zh-CN", "online", "在线"],
    ["en-US", "ready", "Ready"],
    ["zh-CN", "ready", "就绪"],
  ] as const)(
    "keeps raw status metadata while rendering %s",
    (locale, status, label) => {
      setTestLocale(locale);
      render(<StatusPill>{status}</StatusPill>);

      expect(screen.getByText(label)).toHaveAttribute("data-status", status);
    },
  );
});
