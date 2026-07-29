import { randomUUID } from "node:crypto";

import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

test.setTimeout(180_000);

const apiBaseUrl = (
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:18000"
).replace(/\/+$/, "");

type JsonObject = Record<string, unknown>;

function requireString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} is unavailable`);
  }
  return value;
}

function requireItems(value: JsonObject): JsonObject[] {
  const items = value.items;
  if (!Array.isArray(items)) throw new Error("API list payload is invalid");
  return items.filter(
    (item): item is JsonObject =>
      typeof item === "object" && item !== null && !Array.isArray(item),
  );
}

async function apiJson(
  request: APIRequestContext,
  method: "get" | "post",
  path: string,
  data?: JsonObject,
): Promise<JsonObject> {
  const response =
    method === "get"
      ? await request.get(`${apiBaseUrl}${path}`)
      : await request.post(`${apiBaseUrl}${path}`, {
          data,
          headers: { "X-Request-ID": randomUUID() },
        });
  const body: unknown = await response.json();
  if (!response.ok() || typeof body !== "object" || body === null) {
    throw new Error(
      `API ${method.toUpperCase()} ${path} failed: ${response.status()}`,
    );
  }
  return body as JsonObject;
}

async function waitForJob(
  request: APIRequestContext,
  jobId: string,
): Promise<JsonObject> {
  await expect
    .poll(
      async () =>
        (await apiJson(request, "get", `/api/v1/runner-jobs/${jobId}`)).state,
      { timeout: 60_000 },
    )
    .toMatch(/^(succeeded|failed|cancelled)$/);
  return apiJson(request, "get", `/api/v1/runner-jobs/${jobId}`);
}

async function exactValidationCheckpoint(request: APIRequestContext): Promise<{
  checkpointId: string;
  implementationGrantId: string;
  workspaceId: string;
}> {
  const contexts = requireItems(
    await apiJson(request, "get", "/api/v1/execution-grants/eligible-contexts"),
  );
  const context = contexts[0];
  if (!context) throw new Error("No eligible synthetic fixture context");
  let grant = await apiJson(request, "post", "/api/v1/execution-grants", {
    plan_id: requireString(context.plan_id, "Plan ID"),
    repository_handle_id: requireString(
      context.repository_handle_id,
      "Repository Handle ID",
    ),
  });
  if (grant.status === "pending") {
    grant = await apiJson(
      request,
      "post",
      `/api/v1/execution-grants/${requireString(grant.id, "Grant ID")}/decisions`,
      {
        decision: "approve",
        reason: "Synthetic Phase 5 browser fixture approval.",
      },
    );
  }
  expect(grant.status).toBe("approved");
  const implementationGrantId = requireString(grant.id, "Grant ID");

  const prepared = await apiJson(request, "post", "/api/v1/workspaces", {
    grant_id: implementationGrantId,
  });
  const workspace = prepared.workspace as JsonObject;
  const prepareJob = prepared.job as JsonObject;
  expect(
    (
      await waitForJob(
        request,
        requireString(prepareJob.id, "Workspace prepare Job ID"),
      )
    ).state,
  ).toBe("succeeded");
  const workspaceId = requireString(workspace.id, "Workspace ID");

  const diff = await apiJson(
    request,
    "post",
    `/api/v1/workspaces/${workspaceId}/actions/diff`,
  );
  const diffJob = diff.job as JsonObject;
  expect(
    (
      await waitForJob(
        request,
        requireString(diffJob.id, "Workspace diff Job ID"),
      )
    ).state,
  ).toBe("succeeded");
  const checkpoints = requireItems(
    await apiJson(
      request,
      "get",
      `/api/v1/workspaces/${workspaceId}/checkpoints`,
    ),
  );
  const current = checkpoints.at(-1);
  if (!current) throw new Error("Workspace Checkpoint was not created");
  return {
    checkpointId: requireString(current.id, "Checkpoint ID"),
    implementationGrantId,
    workspaceId,
  };
}

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

test("Phase 5 fixed Profile runs from browser approval to isolated evidence", async ({
  page,
  request,
}) => {
  const { checkpointId, implementationGrantId, workspaceId } =
    await exactValidationCheckpoint(request);

  await page.goto("/validations");
  await expect(
    page.getByRole("heading", { name: "Validation Runs" }),
  ).toBeVisible();
  await expect(page.getByText("Trusted fixture Python contract")).toBeVisible({
    timeout: 30_000,
  });
  await expect(
    page.getByText("python -I -S <system-owned-fixture-validator>").first(),
  ).toBeVisible();
  await expect(page.getByText(/network none · Shell false/)).toBeVisible();
  await page
    .getByLabel("Exact Workspace Checkpoint")
    .selectOption(checkpointId);
  const [grantResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/v1/execution-grants") &&
        response.ok(),
    ),
    page.getByRole("button", { name: "创建 pending Validation Grant" }).click(),
  ]);
  const createdGrant: unknown = await grantResponse.json();
  if (typeof createdGrant !== "object" || createdGrant === null) {
    throw new Error("Validation Grant response is invalid");
  }
  const validationGrantId = requireString(
    (createdGrant as JsonObject).id,
    "Validation Grant ID",
  );

  const grantCard = page
    .getByRole("listitem")
    .filter({ hasText: checkpointId });
  await expect(grantCard.getByText("pending", { exact: true })).toBeVisible({
    timeout: 30_000,
  });
  await grantCard
    .getByRole("button", { name: "Approve exact Validation Grant" })
    .click();
  await expect(grantCard.getByText("approved", { exact: true })).toBeVisible({
    timeout: 30_000,
  });

  const [createdResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/v1/validation-runs") &&
        response.ok(),
    ),
    grantCard.getByRole("button", { name: "Run fixed Profile" }).click(),
  ]);
  const created: unknown = await createdResponse.json();
  if (typeof created !== "object" || created === null) {
    throw new Error("Validation Run response is invalid");
  }
  const validationRunId = requireString(
    (created as JsonObject).id,
    "Validation Run ID",
  );
  const runCard = page
    .getByRole("listitem")
    .filter({ hasText: validationRunId });
  await expect(runCard.getByText("succeeded", { exact: true })).toBeVisible({
    timeout: 60_000,
  });
  await expect(runCard.getByText("VE_VALIDATION_PROFILE_PASS")).toBeVisible();
  await expect(
    runCard.getByText(/network true · filesystem true · cleaned true/),
  ).toBeVisible();
  await expect(
    runCard.getByText(/fixture-contract · succeeded · exit 0/),
  ).toBeVisible();
  await expect(
    runCard.getByRole("link", { name: "Workspace" }),
  ).toHaveAttribute("href", `/workspaces/${workspaceId}`);
  await expectAccessibleAndContained(page);

  await page.reload();
  const persistedRun = page
    .getByRole("listitem")
    .filter({ hasText: validationRunId });
  await expect(
    persistedRun.getByText("succeeded", { exact: true }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    persistedRun.getByText("VE_VALIDATION_PROFILE_PASS"),
  ).toBeVisible();

  const revokedValidation = await apiJson(
    request,
    "post",
    `/api/v1/execution-grants/${validationGrantId}/revoke`,
  );
  expect(revokedValidation.status).toBe("revoked");
  const discarded = await apiJson(
    request,
    "post",
    `/api/v1/workspaces/${workspaceId}/actions/discard`,
  );
  expect(
    (
      await waitForJob(
        request,
        requireString(
          (discarded.job as JsonObject).id,
          "Workspace discard Job ID",
        ),
      )
    ).state,
  ).toBe("succeeded");
  const revokedImplementation = await apiJson(
    request,
    "post",
    `/api/v1/execution-grants/${implementationGrantId}/revoke`,
  );
  expect(revokedImplementation.status).toBe("revoked");
});
