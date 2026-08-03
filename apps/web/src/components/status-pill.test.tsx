import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { setTestLocale } from "@/test/setup";

import { StatusPill } from "./status-pill";

describe("StatusPill semantic selector", () => {
  it.each([
    ["en-US", "Ready"],
    ["zh-CN", "就绪"],
  ] as const)(
    "keeps raw status metadata while rendering %s",
    (locale, label) => {
      setTestLocale(locale);
      render(<StatusPill>ready</StatusPill>);

      expect(screen.getByText(label)).toHaveAttribute("data-status", "ready");
    },
  );
});
