import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import type { E2eTestResources } from "./support/isolation";
import { uniqueE2eLabel } from "./support/isolation";
import { expectUiLocale, setUiLocale } from "./support/locale";

const repositoryLocator = "/repositories/e2e/adversarial";
const uiLocale = "en-US";
test.use({ locale: uiLocale });

async function createTaskAndOpenRun(
  page: Page,
  resources: E2eTestResources,
  title: string,
) {
  await page.goto("/");
  await expectUiLocale(page, uiLocale);
  await page.getByLabel("Task title").fill(title);
  await page
    .getByLabel("Task objective")
    .fill("Review a governed frontend quality remediation plan.");
  await page.getByLabel("Display name").fill("Synthetic adversarial fixture");
  await page.getByLabel("Repository locator").fill(repositoryLocator);
  await page.getByRole("button", { name: "Create task" }).click();
  const taskCard = page
    .getByRole("article")
    .filter({ has: page.getByRole("heading", { name: title }) });
  await taskCard.getByRole("link", { name: "View details" }).click();
  const [runResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        /\/api\/v1\/tasks\/[0-9a-f-]+\/runs$/.test(response.url()) &&
        response.ok(),
    ),
    page.getByRole("button", { name: "Start read-only investigation" }).click(),
  ]);
  const run: unknown = await runResponse.json();
  if (
    typeof run !== "object" ||
    run === null ||
    !("id" in run) ||
    typeof run.id !== "string"
  ) {
    throw new Error("Created Run response is invalid");
  }
  resources.trackRun(run.id);
  await expect(page.getByText("Read-only Run created.")).toBeVisible();
  await page.getByRole("link", { name: "Open Run" }).click();
  await expect(page).toHaveURL(/\/runs\/[0-9a-f-]+$/);
}

async function createSnapshotAndPlan(page: Page) {
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
    context,
    page,
    resources,
  }, testInfo) => {
    await setUiLocale(context, uiLocale);
    const title = uniqueE2eLabel(testInfo, "Phase 2 approve");
    await createTaskAndOpenRun(page, resources, title);
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
    await expect(
      page.locator('[data-status="awaiting_plan_approval"]'),
    ).toBeVisible();
    await page.getByRole("button", { name: "Approve Plan" }).click();
    await expect(
      page.locator('[data-status="approved"]').first(),
    ).toBeVisible();
    await expect(
      page.getByText("Execution is not available in Phase 2."),
    ).toBeVisible();

    await page.reload();
    await expect(
      page.locator('[data-status="approved"]').first(),
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
    context,
    page,
    resources,
  }, testInfo) => {
    await setUiLocale(context, uiLocale);
    const title = uniqueE2eLabel(testInfo, "Phase 2 reject");
    await createTaskAndOpenRun(page, resources, title);
    await createSnapshotAndPlan(page);

    await page.getByRole("button", { name: "Submit latest Plan" }).click();
    await expect(
      page.locator('[data-status="awaiting_plan_approval"]'),
    ).toBeVisible();
    await page.getByRole("button", { name: "Reject Plan" }).click();
    await expect(
      page.getByText("A non-empty reason is required to reject."),
    ).toBeVisible();
    await page
      .getByLabel("Rejection reason")
      .fill("The proposed scope requires a human-authored revision.");
    await page.getByRole("button", { name: "Reject Plan" }).click();
    await expect(
      page.locator('[data-status="rejected"]').first(),
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
