import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("Foundation smoke", () => {
  test("creates, retrieves, and persists a task", async ({
    page,
  }, testInfo) => {
    const uniqueSuffix = `${testInfo.project.name}-${Date.now()}`;
    const title = `E2E Foundation ${uniqueSuffix}`;

    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: "受治理的前端交付任务控制台" }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("listitem")
        .filter({ hasText: "Liveness" })
        .getByText("正常"),
    ).toBeVisible();
    await expect(
      page
        .getByRole("listitem")
        .filter({ hasText: "Readiness" })
        .getByText("正常"),
    ).toBeVisible();

    await page.getByLabel("任务标题").fill(title);
    await page
      .getByLabel("任务目标")
      .fill("Verify the real Foundation API and PostgreSQL persistence.");
    await page.getByLabel("显示名称").fill("visual-engineer-e2e");
    await page.getByLabel("仓库位置").fill(`/test-fixtures/${uniqueSuffix}`);
    await page.getByRole("button", { name: "创建任务" }).click();

    await expect(page.getByText("任务创建成功")).toBeVisible();
    const taskCard = page
      .getByRole("article")
      .filter({ has: page.getByRole("heading", { name: title }) });
    await expect(taskCard).toBeVisible();
    await expect(taskCard.getByText("draft")).toBeVisible();
    await taskCard.getByRole("link", { name: /查看详情/ }).click();

    await expect(page).toHaveURL(/\/tasks\/[0-9a-f-]+$/);
    const taskDetail = page.getByRole("article");
    await expect(
      taskDetail.getByRole("heading", { name: title }),
    ).toBeVisible();
    await expect(taskDetail.getByText("draft", { exact: true })).toBeVisible();

    await page.reload();
    await expect(
      taskDetail.getByRole("heading", { name: title }),
    ).toBeVisible();
    await expect(taskDetail.getByText("draft", { exact: true })).toBeVisible();

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
