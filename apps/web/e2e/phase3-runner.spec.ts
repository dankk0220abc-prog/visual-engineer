import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { expectUiLocale, setUiLocale } from "./support/locale";

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

async function openOnlineRegistry(page: Page) {
  await page.goto("/runners");
  await expectUiLocale(page, uiLocale);
  await expect(
    page.getByRole("heading", { name: "Local Runner console" }),
  ).toBeVisible();
  await expect(page.locator('[data-status="online"]')).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByLabel("Permission Envelope preview")).toContainText(
    "Repository accessnone",
  );
  await expect(page.getByLabel("Permission Envelope preview")).toContainText(
    "Shell accessfalse",
  );
  await expect(page.getByLabel("Permission Envelope preview")).toContainText(
    "Networkcontrol-plane only",
  );
  await expect(page.getByLabel("Permission Envelope preview")).toContainText(
    "Project codenot accessed",
  );
}

test.describe("Phase 3 browser-orchestrated Local Runner", () => {
  test("Flow A dispatches a durable redacted system diagnostic", async ({
    context,
    page,
    resources,
  }) => {
    await setUiLocale(context, uiLocale);
    await openOnlineRegistry(page);
    const [jobResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().endsWith("/api/v1/runner-jobs") &&
          response.ok(),
      ),
      page.getByRole("button", { name: "Create and view Job" }).click(),
    ]);
    const job = (await jobResponse.json()) as { id?: unknown };
    if (typeof job.id !== "string") throw new Error("Runner Job ID is invalid");
    resources.trackJob(job.id);
    await expect(page).toHaveURL(/\/runners\/jobs\/[0-9a-f-]+$/);

    await expect(page.locator('[data-status="succeeded"]').first()).toBeVisible(
      { timeout: 30_000 },
    );
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
      page.locator('[data-status="succeeded"]').first(),
    ).toBeVisible();
    await expect(page.getByText("job_succeeded")).toBeVisible();
    await expectAccessibleAndContained(page);
  });

  test("Flow B visibly requests and acknowledges controlled-wait cancellation", async ({
    context,
    page,
    resources,
  }) => {
    await setUiLocale(context, uiLocale);
    await openOnlineRegistry(page);
    await page.getByRole("radio", { name: /Controlled Wait/ }).check();
    await page.getByLabel("Duration (milliseconds)").fill("10000");
    const [jobResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().endsWith("/api/v1/runner-jobs") &&
          response.ok(),
      ),
      page.getByRole("button", { name: "Create and view Job" }).click(),
    ]);
    const job = (await jobResponse.json()) as { id?: unknown };
    if (typeof job.id !== "string") throw new Error("Runner Job ID is invalid");
    resources.trackJob(job.id);
    await expect(page).toHaveURL(/\/runners\/jobs\/[0-9a-f-]+$/);

    await expect(page.locator('[data-status="running"]').first()).toBeVisible({
      timeout: 30_000,
    });
    const [cancelResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().endsWith(`/api/v1/runner-jobs/${job.id}/cancel`) &&
          response.ok(),
      ),
      page.getByRole("button", { name: "Cancel Job" }).click(),
    ]);
    const cancelResult = (await cancelResponse.json()) as { state?: unknown };
    expect(cancelResult.state).toBe("cancel_requested");
    await expect(page.locator('[data-status="cancelled"]').first()).toBeVisible(
      { timeout: 30_000 },
    );
    await expect(
      page.getByText(
        /Cancellation was requested and is awaiting Runner confirmation/,
      ),
    ).toHaveCount(0);
    await expect(
      page.getByText("cancel_requested", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("cancel_acknowledged", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("job_succeeded")).toHaveCount(0);
    await expect(
      page.getByText("This terminal state has no successful result."),
    ).toBeVisible();
    await expectAccessibleAndContained(page);
  });
});
