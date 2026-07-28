import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.setTimeout(180_000);

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

test("Phase 4 grant, typed tools, rollback, and discard stay browser-visible", async ({
  page,
}, testInfo) => {
  await page.goto("/repositories");
  await expect(
    page.getByRole("heading", { name: "Repository Handles" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Phase 4 Adversarial Fixture" }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("available", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/Source working-tree status is intentionally unknown/),
  ).toBeVisible();
  await expect(page.locator("main")).not.toContainText("/repositories/fixture");
  await expectAccessibleAndContained(page);

  await page.goto("/execution-grants");
  await expect(
    page.getByText(
      "Plan approval does not authorize execution. This Execution Grant is a separate human decision.",
    ),
  ).toBeVisible();
  const createGrant = page.getByRole("button", {
    name: "创建 pending Grant",
  });
  await expect(createGrant).toBeVisible();
  const approved = page.getByText("approved", { exact: true });
  const pending = page.getByText("pending", { exact: true });
  if ((await approved.count()) === 0) {
    await createGrant.click();
    await expect(pending.or(approved).first()).toBeVisible({ timeout: 30_000 });
    if ((await approved.count()) === 0) {
      await expect(pending).toBeVisible();
      await expect(
        page.getByText(/network none · Shell false/).first(),
      ).toBeVisible();
      await Promise.all([
        page.waitForResponse(
          (response) =>
            response.request().method() === "POST" &&
            response.url().endsWith("/decisions") &&
            response.ok(),
        ),
        page.getByRole("button", { name: "Approve Grant" }).click(),
      ]);
    }
  }
  await expect(approved).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByText("sandbox/**", { exact: true }).first(),
  ).toBeVisible();
  await expectAccessibleAndContained(page);

  await page.goto("/workspaces");
  await expect(
    page.getByRole("heading", { name: "Isolated Workspaces" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Prepare Workspace" }).click();
  await expect(page).toHaveURL(/\/workspaces\/[0-9a-f-]+$/);
  await expect(page.getByText("ready", { exact: true })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/no自由 Shell|无自由 Shell/)).toBeVisible();

  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.getByText("List 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("sandbox/original.txt").last()).toBeVisible();

  await page.getByRole("button", { name: "Read text" }).click();
  await expect(page.getByText("Read 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("Original fixture text.")).toBeVisible();

  await page.getByLabel("UTF-8 content").fill("Browser typed replacement.\n");
  await page.getByRole("button", { name: "Replace text" }).click();
  await expect(page.getByText("Replace text 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });

  await page.getByRole("radio", { name: "create" }).check();
  await page.getByLabel("Relative path").fill("sandbox/.env");
  await page.getByRole("button", { name: "Create text" }).click();
  await expect(page.locator("main [role=alert]")).toContainText(
    "sensitive_path_denied",
    { timeout: 30_000 },
  );

  await page.getByLabel("Relative text path").fill("../outside");
  await page.getByRole("button", { name: "Read text" }).click();
  await expect(page.locator("main [role=alert]")).toContainText(
    "validation_error",
    { timeout: 30_000 },
  );

  await page.getByLabel("Relative text path").fill("sandbox/outside-link");
  await page.getByRole("button", { name: "Read text" }).click();
  await expect(page.locator("main [role=alert]")).toContainText(
    "symlink_denied",
    {
      timeout: 30_000,
    },
  );

  await page.getByRole("radio", { name: "replace" }).check();
  await page.getByLabel("Relative path").fill("sandbox/original.txt");
  await page.getByLabel("Expected SHA-256").fill("0".repeat(64));
  await page.getByLabel("UTF-8 content").fill("Stale write must fail.\n");
  await page.getByRole("button", { name: "Replace text" }).click();
  await expect(page.locator("main [role=alert]")).toContainText(
    "content_conflict",
    {
      timeout: 30_000,
    },
  );

  await page.getByRole("radio", { name: "create" }).check();
  await page
    .getByLabel("Relative path")
    .fill(`sandbox/create-here/browser-${testInfo.project.name}.txt`);
  await page.getByLabel("UTF-8 content").fill("Browser-created text.\n");
  await page.getByRole("button", { name: "Create text" }).click();
  await expect(page.getByText("Create text 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });

  await page.getByRole("button", { name: "Status" }).click();
  await expect(page.getByText("Status 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await page.getByRole("button", { name: "Diff + Seal" }).click();
  await expect(page.getByText("Diff + Seal 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("sealed", { exact: true })).toBeVisible();
  const sealedCheckpoint = page
    .getByText("Checkpoint #3", { exact: true })
    .locator("..");
  await expect(sealedCheckpoint).toBeVisible();
  await expect(sealedCheckpoint.locator("pre")).toContainText(
    "Browser-created text.",
  );
  const writeCheckpoint = page
    .getByText("Checkpoint #1", { exact: true })
    .locator("..");
  await expect(writeCheckpoint.getByText(/permit [0-9a-f-]{36}/)).toBeVisible();
  await expect(page.getByText(/No source repository write/)).toBeVisible();

  const persistedUrl = page.url();
  await page.reload();
  await expect(page).toHaveURL(persistedUrl);
  await expect(page.getByText("sealed", { exact: true })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("Checkpoint #3")).toBeVisible();

  await page.getByRole("button", { name: "Rollback to initial" }).click();
  await expect(page.getByText("Rollback 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("rolled_back", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Status" }).click();
  await expect(page.getByText("Status 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/0\/8 files/)).toBeVisible();

  await page.getByRole("button", { name: "Discard" }).click();
  await expect(page.getByText("Discard 已完成并持久化。")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("discarded", { exact: true })).toBeVisible();
  await expect(page.getByText(/Workspace 已销毁/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Discard" })).toBeDisabled();
  await expect(page.getByText("workspace_discarded")).toBeVisible();
  await expectAccessibleAndContained(page);
});
