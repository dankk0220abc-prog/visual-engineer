import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

async function expectAccessibleAndContained(
  page: import("@playwright/test").Page,
) {
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
  ).toBe(false);
}

async function openOnlineRegistry(page: import("@playwright/test").Page) {
  await page.goto("/runners");
  await expect(
    page.getByRole("heading", { name: "Local Runner 控制台" }),
  ).toBeVisible();
  await expect(page.getByText("online", { exact: true })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByLabel("Permission Envelope 预览")).toContainText(
    "Repository accessnone",
  );
  await expect(page.getByLabel("Permission Envelope 预览")).toContainText(
    "Shell accessfalse",
  );
  await expect(page.getByLabel("Permission Envelope 预览")).toContainText(
    "Networkcontrol-plane only",
  );
  await expect(page.getByLabel("Permission Envelope 预览")).toContainText(
    "Project codenot accessed",
  );
}

test.describe("Phase 3 browser-orchestrated Local Runner", () => {
  test("Flow A dispatches a durable redacted system diagnostic", async ({
    page,
  }) => {
    await openOnlineRegistry(page);
    await page.getByRole("button", { name: "创建并查看 Job" }).click();
    await expect(page).toHaveURL(/\/runners\/jobs\/[0-9a-f-]+$/);

    await expect(
      page.getByText("succeeded", { exact: true }).first(),
    ).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("job_created")).toBeVisible();
    await expect(page.getByText("job_claimed")).toBeVisible();
    await expect(page.getByText("job_started")).toBeVisible();
    await expect(page.getByText("job_succeeded")).toBeVisible();
    await expect(page.getByText("runner_software_version")).toBeVisible();
    await expect(page.getByText("python_version")).toBeVisible();
    await expect(page.getByText("os_family")).toBeVisible();
    await expect(page.getByText("architecture")).toBeVisible();

    const result = page.getByRole("heading", { name: "Result" }).locator("..");
    await expect(result).not.toContainText("hostname");
    await expect(result).not.toContainText("username");
    await expect(result).not.toContainText("environment");
    await expect(result).not.toContainText("absolute_path");
    await expect(page.getByText("none", { exact: true })).toBeVisible();
    await expect(page.getByText("false", { exact: true })).toBeVisible();
    await expect(
      page.getByText("control_plane_only", { exact: true }),
    ).toBeVisible();

    const persistedUrl = page.url();
    await page.reload();
    await expect(page).toHaveURL(persistedUrl);
    await expect(
      page.getByText("succeeded", { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByText("job_succeeded")).toBeVisible();
    await expectAccessibleAndContained(page);
  });

  test("Flow B visibly requests and acknowledges controlled-wait cancellation", async ({
    page,
  }) => {
    await openOnlineRegistry(page);
    await page.getByRole("radio", { name: /Controlled Wait/ }).check();
    await page.getByLabel("Duration（毫秒）").fill("10000");
    await page.getByRole("button", { name: "创建并查看 Job" }).click();
    await expect(page).toHaveURL(/\/runners\/jobs\/[0-9a-f-]+$/);

    await expect(
      page.getByText("running", { exact: true }).first(),
    ).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Cancel Job" }).click();
    await expect(
      page.getByText(/已请求取消，正在等待 Runner 确认/),
    ).toBeVisible();
    await expect(
      page.getByText("cancel_requested", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("cancelled", { exact: true }).first(),
    ).toBeVisible({ timeout: 30_000 });
    await expect(
      page.getByText(/已请求取消，正在等待 Runner 确认/),
    ).toHaveCount(0);
    await expect(
      page.getByText("cancel_requested", { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByText("cancel_acknowledged")).toBeVisible();
    await expect(page.getByText("job_succeeded")).toHaveCount(0);
    await expect(page.getByText("此终态没有成功结果。")).toBeVisible();
    await expectAccessibleAndContained(page);
  });
});
