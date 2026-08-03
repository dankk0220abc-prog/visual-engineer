import AxeBuilder from "@axe-core/playwright";

import { expect, test } from "./support/fixtures";
import { uniqueE2eLabel } from "./support/isolation";
import { expectUiLocale, setUiLocale } from "./support/locale";

const uiLocale = "en-US";
test.use({ locale: uiLocale });

test.describe("Foundation smoke", () => {
  test("creates, retrieves, and persists a task", async ({
    context,
    page,
  }, testInfo) => {
    const uniqueSuffix = uniqueE2eLabel(testInfo, "foundation");
    const title = `E2E Foundation ${uniqueSuffix}`;

    await setUiLocale(context, uiLocale);
    await page.goto("/");
    await expectUiLocale(page, uiLocale);

    await expect(
      page.getByRole("heading", {
        name: "Governed frontend delivery task console",
      }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("listitem")
        .filter({ hasText: "Liveness" })
        .getByText("Healthy"),
    ).toBeVisible();
    await expect(
      page
        .getByRole("listitem")
        .filter({ hasText: "Readiness" })
        .getByText("Healthy"),
    ).toBeVisible();

    await page.getByLabel("Task title").fill(title);
    await page
      .getByLabel("Task objective")
      .fill("Verify the real Foundation API and PostgreSQL persistence.");
    await page.getByLabel("Display name").fill("visual-engineer-e2e");
    await page
      .getByLabel("Repository locator")
      .fill(`/test-fixtures/${uniqueSuffix}`);
    await page.getByRole("button", { name: "Create task" }).click();

    await expect(page.getByText("Task created")).toBeVisible();
    const taskCard = page
      .getByRole("article")
      .filter({ has: page.getByRole("heading", { name: title }) });
    await expect(taskCard).toBeVisible();
    await expect(taskCard.locator('[data-status="draft"]')).toBeVisible();
    await taskCard.getByRole("link", { name: "View details" }).click();

    await expect(page).toHaveURL(/\/tasks\/[0-9a-f-]+$/);
    const taskDetail = page.getByRole("article");
    await expect(
      taskDetail.getByRole("heading", { name: title }),
    ).toBeVisible();
    await expect(taskDetail.locator('[data-status="draft"]')).toBeVisible();

    await page.reload();
    await expect(
      taskDetail.getByRole("heading", { name: title }),
    ).toBeVisible();
    await expect(taskDetail.locator('[data-status="draft"]')).toBeVisible();

    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
  });
});
