import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { uniqueE2eLabel } from "./support/isolation";
import { expectUiLocale, setUiLocale } from "./support/locale";

test.setTimeout(180_000);
const uiLocale = "en-US";
test.use({ locale: uiLocale });

async function expectAccessibleAndContained(page: Page) {
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
  context,
  page,
  resources,
}, testInfo) => {
  await setUiLocale(context, uiLocale);
  await page.goto("/repositories");
  await expectUiLocale(page, uiLocale);
  await expect(
    page.getByRole("heading", { name: "Repository Intelligence" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Phase 4 Adversarial Fixture" }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-status="available"]')).toBeVisible();
  await expect(
    page.getByText(/Source working-tree status is intentionally unknown/),
  ).toBeVisible();
  await expect(page.locator("main")).not.toContainText("/repositories/fixture");
  await expectAccessibleAndContained(page);

  await page.goto("/execution-grants");
  await expect(
    page.getByText(
      "Plan Approval does not authorize execution. An Execution Grant is a separate human decision.",
    ),
  ).toBeVisible();
  const createGrant = page.getByRole("button", {
    name: "Create pending Grant",
  });
  await expect(createGrant).toBeVisible();
  const [grantResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/v1/execution-grants") &&
        response.ok(),
    ),
    createGrant.click(),
  ]);
  const grant: unknown = await grantResponse.json();
  if (
    typeof grant !== "object" ||
    grant === null ||
    !("id" in grant) ||
    typeof grant.id !== "string"
  ) {
    throw new Error("Execution Grant response is invalid");
  }
  const grantId = resources.trackGrant(grant.id);
  const grantCard = page.getByRole("listitem").filter({ hasText: grantId });
  await expect(grantCard.locator('[data-status="pending"]')).toBeVisible({
    timeout: 30_000,
  });
  await expect(grantCard.getByText(/network none · Shell false/)).toBeVisible();
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/execution-grants/${grantId}/decisions`) &&
        response.ok(),
    ),
    grantCard.getByRole("button", { name: "Approve Execution Grant" }).click(),
  ]);
  await expect(grantCard.locator('[data-status="approved"]')).toBeVisible({
    timeout: 30_000,
  });
  await expect(
    grantCard.getByText("sandbox/**", { exact: true }),
  ).toBeVisible();
  await expectAccessibleAndContained(page);

  await page.goto("/workspaces");
  await expect(
    page.getByRole("heading", { name: "Isolated Workspaces" }),
  ).toBeVisible();
  await page.getByLabel("Approved Execution Grant").selectOption(grantId);
  const [workspaceResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/v1/workspaces") &&
        response.ok(),
    ),
    page.getByRole("button", { name: "Prepare Workspace" }).click(),
  ]);
  const workspaceAction: unknown = await workspaceResponse.json();
  if (
    typeof workspaceAction !== "object" ||
    workspaceAction === null ||
    !("workspace" in workspaceAction) ||
    typeof workspaceAction.workspace !== "object" ||
    workspaceAction.workspace === null ||
    !("id" in workspaceAction.workspace) ||
    typeof workspaceAction.workspace.id !== "string" ||
    !("job" in workspaceAction) ||
    typeof workspaceAction.job !== "object" ||
    workspaceAction.job === null ||
    !("id" in workspaceAction.job) ||
    typeof workspaceAction.job.id !== "string"
  ) {
    throw new Error("Workspace preparation response is invalid");
  }
  const workspaceId = resources.trackWorkspace(workspaceAction.workspace.id);
  resources.trackJob(workspaceAction.job.id);
  await expect(page).toHaveURL(/\/workspaces\/[0-9a-f-]+$/);
  await expect(page).toHaveURL(new RegExp(`/workspaces/${workspaceId}$`));
  await expect(page.locator('[data-status="ready"]')).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/no free-form Shell/)).toBeVisible();

  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.getByText("List completed and was persisted.")).toBeVisible(
    {
      timeout: 30_000,
    },
  );
  await expect(page.getByText("sandbox/original.txt").last()).toBeVisible();

  await page.getByRole("button", { name: "Read text" }).click();
  await expect(
    page.getByText("Read text completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("Original fixture text.")).toBeVisible();

  await page.getByLabel("UTF-8 content").fill("Browser typed replacement.\n");
  await page.getByRole("button", { name: "Replace text" }).click();
  await expect(
    page.getByText("Replace text completed and was persisted."),
  ).toBeVisible({
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
    .fill(`sandbox/create-here/${uniqueE2eLabel(testInfo, "browser")}.txt`);
  await page.getByLabel("UTF-8 content").fill("Browser-created text.\n");
  await page.getByRole("button", { name: "Create text" }).click();
  await expect(
    page.getByText("Create text completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });

  await page.getByRole("button", { name: "Status" }).click();
  await expect(
    page.getByText("Status completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });
  await page.getByRole("button", { name: "Diff + Seal" }).click();
  await expect(
    page.getByText("Diff + Seal completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.locator('[data-status="sealed"]')).toBeVisible();
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
  await expect(page.locator('[data-status="sealed"]')).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText("Checkpoint #3")).toBeVisible();

  await page.getByRole("button", { name: "Rollback to initial" }).click();
  await expect(
    page.getByText("Rollback to initial completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.locator('[data-status="rolled_back"]')).toBeVisible();
  await page.getByRole("button", { name: "Status" }).click();
  await expect(
    page.getByText("Status completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/0\/8 files/)).toBeVisible();

  await page.getByRole("button", { name: "Discard" }).click();
  await expect(
    page.getByText("Discard completed and was persisted."),
  ).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.locator('[data-status="discarded"]')).toBeVisible();
  await expect(page.getByText(/Workspace destroyed/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Discard" })).toBeDisabled();
  await expect(page.getByText("workspace_discarded")).toBeVisible();
  await expectAccessibleAndContained(page);
});
