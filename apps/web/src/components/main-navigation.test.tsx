import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { setTestLocale } from "@/test/setup";

import { MainNavigation } from "./main-navigation";

vi.mock("next/navigation", () => ({
  usePathname: () => "/validations",
}));

describe("MainNavigation localization", () => {
  it.each([
    ["en-US", "Tasks", "Validation", "Interface language"],
    ["zh-CN", "任务", "验证", "界面语言"],
  ] as const)(
    "renders the shared navigation in %s",
    (locale, tasks, validation, languageLabel) => {
      setTestLocale(locale);
      render(<MainNavigation />);

      expect(screen.getByRole("link", { name: tasks })).toBeVisible();
      expect(screen.getByRole("link", { name: validation })).toHaveAttribute(
        "aria-current",
        "page",
      );
      expect(screen.getByRole("combobox", { name: languageLabel })).toHaveValue(
        locale,
      );
      expect(screen.getByRole("option", { name: "中文" })).toBeVisible();
      expect(screen.getByRole("option", { name: "English" })).toBeVisible();
    },
  );
});
