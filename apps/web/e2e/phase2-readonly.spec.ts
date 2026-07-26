import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const repositoryLocator = "/repositories/e2e/adversarial";

async function createTaskAndOpenRun(
  page: import("@playwright/test").Page,
  title: string,
) {
  await page.goto("/");
  await page.getByLabel("任务标题").fill(title);
  await page
    .getByLabel("任务目标")
    .fill("Review a governed frontend quality remediation plan.");
  await page.getByLabel("显示名称").fill("Synthetic adversarial fixture");
  await page.getByLabel("仓库位置").fill(repositoryLocator);
  await page.getByRole("button", { name: "创建任务" }).click();
  const taskCard = page
    .getByRole("article")
    .filter({ has: page.getByRole("heading", { name: title }) });
  await taskCard.getByRole("link", { name: /查看详情/ }).click();
  await page
    .getByRole("button", { name: "Start read-only investigation" })
    .click();
  await expect(page.getByText("Read-only Run 已创建。")).toBeVisible();
  await page.getByRole("link", { name: "打开 Run" }).click();
  await expect(page).toHaveURL(/\/runs\/[0-9a-f-]+$/);
}

async function createSnapshotAndPlan(page: import("@playwright/test").Page) {
  await page
    .getByRole("button", { name: "Create committed-HEAD Snapshot" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Repository Intelligence" }),
  ).toBeVisible();
  await expect(page.getByText("Dirty working tree detected")).toBeVisible();
  await expect(page.getByText(/environment_file · \.env/)).toBeVisible();
  await expect(page.getByText(/prompt_injection_/).first()).toBeVisible();
  await page
    .getByRole("button", { name: "Generate deterministic Plan" })
    .click();
  await expect(page.getByText(/deterministic plan · v1/i)).toBeVisible();
  await expect(
    page.getByText("Plan approval does not execute code."),
  ).toBeVisible();
  await expect(
    page.getByText("Execution is not available in Phase 2."),
  ).toBeVisible();
}

test.describe("Phase 2 governed read-only flow", () => {
  test("Flow A revises, submits, and approves without execution", async ({
    page,
  }, testInfo) => {
    const title = `Phase 2 approve ${testInfo.project.name}-${Date.now()}`;
    await createTaskAndOpenRun(page, title);
    await createSnapshotAndPlan(page);

    await page
      .getByLabel("Objective summary")
      .fill("Approve a bounded responsive and accessibility remediation plan.");
    await page
      .getByLabel("Scope, one item per line")
      .fill(
        "Review the approved frontend surface\nPreserve existing design tokens",
      );
    await page.getByRole("button", { name: "Create revision" }).click();
    await expect(page.getByText(/deterministic plan · v2/i)).toBeVisible();

    await page.getByRole("button", { name: "Submit latest Plan" }).click();
    await expect(page.getByText("awaiting_plan_approval")).toBeVisible();
    await page.getByRole("button", { name: "Approve Plan" }).click();
    await expect(
      page.getByText("approved", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("Execution is not available in Phase 2."),
    ).toBeVisible();

    await page.reload();
    await expect(
      page.getByText("approved", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Audit Timeline" }),
    ).toBeVisible();
    await expect(page.getByText("plan_approved")).toBeVisible();
    await expect(page.getByText("snapshot_completed")).toBeVisible();

    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      ),
    ).toBe(false);
  });

  test("Flow B requires a reason and rejects durably", async ({
    page,
  }, testInfo) => {
    const title = `Phase 2 reject ${testInfo.project.name}-${Date.now()}`;
    await createTaskAndOpenRun(page, title);
    await createSnapshotAndPlan(page);

    await page.getByRole("button", { name: "Submit latest Plan" }).click();
    await expect(page.getByText("awaiting_plan_approval")).toBeVisible();
    await page.getByRole("button", { name: "Reject Plan" }).click();
    await expect(page.getByText("Reject 必须填写非空理由。")).toBeVisible();
    await page
      .getByLabel("Rejection reason")
      .fill("The proposed scope requires a human-authored revision.");
    await page.getByRole("button", { name: "Reject Plan" }).click();
    await expect(
      page.getByText("rejected", { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByText("plan_rejected")).toBeVisible();

    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      ),
    ).toBe(false);
  });
});
