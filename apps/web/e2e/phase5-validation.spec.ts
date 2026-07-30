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

test("Phase 5 fixed Profile compatibility and multi-step Suite run to aggregate evidence", async ({
  page,
  request,
}) => {
  const { checkpointId, implementationGrantId, workspaceId } =
    await exactValidationCheckpoint(request);

  let profileGrant = await apiJson(
    request,
    "post",
    "/api/v1/execution-grants",
    {
      plan_id: requireString(
        (
          await apiJson(
            request,
            "get",
            `/api/v1/execution-grants/${implementationGrantId}`,
          )
        ).plan_id,
        "Plan ID",
      ),
      repository_handle_id: requireString(
        (
          await apiJson(
            request,
            "get",
            `/api/v1/execution-grants/${implementationGrantId}`,
          )
        ).repository_handle_id,
        "Repository Handle ID",
      ),
      validation_checkpoint_id: checkpointId,
      validation_profile_id: "fixture-python-stdlib-v1",
    },
  );
  if (profileGrant.status === "pending") {
    profileGrant = await apiJson(
      request,
      "post",
      `/api/v1/execution-grants/${requireString(profileGrant.id, "Profile Grant ID")}/decisions`,
      {
        decision: "approve",
        reason: "Sealed first-slice compatibility approval.",
      },
    );
  }
  const profileGrantId = requireString(profileGrant.id, "Profile Grant ID");

  await page.goto("/validations");
  await expect(
    page.getByRole("heading", { name: "Validation Runs" }),
  ).toBeVisible();
  await expect(page.getByText("Trusted fixture integrity suite")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/network none · Shell false/)).toBeVisible();

  const profileGrantCard = page
    .getByRole("listitem")
    .filter({ hasText: profileGrantId });
  const [profileRunResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/v1/validation-runs") &&
        response.ok(),
    ),
    profileGrantCard
      .getByRole("button", { name: "Run sealed first-slice Profile" })
      .click(),
  ]);
  const profileRunBody: unknown = await profileRunResponse.json();
  if (typeof profileRunBody !== "object" || profileRunBody === null) {
    throw new Error("First-slice Validation Run response is invalid");
  }
  const validationRunId = requireString(
    (profileRunBody as JsonObject).id,
    "Validation Run ID",
  );
  const runCard = page
    .getByRole("listitem")
    .filter({ hasText: validationRunId });
  await expect(runCard.getByText("succeeded", { exact: true })).toBeVisible({
    timeout: 60_000,
  });
  await expect(runCard.getByText("VE_VALIDATION_PROFILE_PASS")).toBeVisible();

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
    page.getByRole("button", { name: "创建 pending Suite Grant" }).click(),
  ]);
  const createdGrant: unknown = await grantResponse.json();
  if (typeof createdGrant !== "object" || createdGrant === null) {
    throw new Error("Validation Grant response is invalid");
  }
  const suiteGrantId = requireString(
    (createdGrant as JsonObject).id,
    "Suite Grant ID",
  );

  const grantCard = page
    .getByRole("listitem")
    .filter({ hasText: suiteGrantId });
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
        response.url().endsWith("/api/v1/validation-suite-runs") &&
        response.ok(),
    ),
    grantCard.getByRole("button", { name: "Run fixed Suite" }).click(),
  ]);
  const created: unknown = await createdResponse.json();
  if (typeof created !== "object" || created === null) {
    throw new Error("Validation Suite Run response is invalid");
  }
  const suiteRunId = requireString(
    (created as JsonObject).id,
    "Validation Suite Run ID",
  );
  const suiteRunCard = page
    .getByRole("listitem")
    .filter({ hasText: suiteRunId });
  await expect(
    suiteRunCard.getByText("succeeded", { exact: true }).first(),
  ).toBeVisible({
    timeout: 60_000,
  });
  await expect(
    suiteRunCard.getByText("VE_VALIDATION_PROFILE_PASS"),
  ).toBeVisible();
  await expect(
    suiteRunCard.getByText("VE_VALIDATION_PROFILE_MANIFEST_PASS"),
  ).toBeVisible();
  await expect(
    suiteRunCard.getByText("Aggregate Result: succeeded"),
  ).toBeVisible();
  await expect(
    suiteRunCard.getByText(/Evidence 2 · redactions 0 · artifacts 0/),
  ).toBeVisible();
  await expect(suiteRunCard.getByText(/1\. fixture-contract/)).toBeVisible();
  await expect(suiteRunCard.getByText(/2\. fixture-manifest/)).toBeVisible();
  await expectAccessibleAndContained(page);

  await page.reload();
  const persistedSuite = page
    .getByRole("listitem")
    .filter({ hasText: suiteRunId });
  await expect(
    persistedSuite.getByText("Aggregate Result: succeeded"),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    persistedSuite.getByText("VE_VALIDATION_PROFILE_MANIFEST_PASS"),
  ).toBeVisible();

  await page.goto("/reviews");
  await expect(
    page.getByRole("heading", { name: "Review & Release Readiness" }),
  ).toBeVisible();
  const reviewCandidate = page
    .getByRole("listitem")
    .filter({ hasText: suiteRunId });
  const [packageResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/v1/review-packages") &&
        response.ok(),
    ),
    reviewCandidate
      .getByRole("button", { name: "Create immutable Review Package" })
      .click(),
  ]);
  const packageBody: unknown = await packageResponse.json();
  if (typeof packageBody !== "object" || packageBody === null) {
    throw new Error("Review Package response is invalid");
  }
  const packageId = requireString(
    (packageBody as JsonObject).id,
    "Review Package ID",
  );
  const packageCard = page.getByRole("listitem").filter({ hasText: packageId });
  await expect(packageCard.getByText("Evidence Manifest 2/2")).toBeVisible({
    timeout: 30_000,
  });
  await expect(packageCard.getByText("Generation 1 / current 1")).toBeVisible();
  await expect(
    packageCard.getByText("Critical 0 · High 0 · Blocking medium 0"),
  ).toBeVisible();
  await expect(
    packageCard.getByText("governed-review-security-findings:v1"),
  ).toBeVisible();
  await expect(
    packageCard.getByText(
      "Git authorization: false · Deployment authorization: false",
    ),
  ).toBeVisible();
  await packageCard.getByRole("button", { name: "Recheck freshness" }).click();
  await expect(packageCard.getByText("fresh", { exact: true })).toBeVisible();
  await packageCard
    .getByRole("button", { name: "Approve Review Package" })
    .click();
  await expect(packageCard.getByText(/Decision: approve/)).toBeVisible({
    timeout: 30_000,
  });
  await packageCard
    .getByRole("button", { name: "Compute deterministic Readiness" })
    .click();
  await expect(packageCard.getByText("Release Readiness: ready")).toBeVisible({
    timeout: 30_000,
  });
  await expectAccessibleAndContained(page);

  const revokedSuite = await apiJson(
    request,
    "post",
    `/api/v1/execution-grants/${suiteGrantId}/revoke`,
  );
  expect(revokedSuite.status).toBe("revoked");
  const revokedProfile = await apiJson(
    request,
    "post",
    `/api/v1/execution-grants/${profileGrantId}/revoke`,
  );
  expect(revokedProfile.status).toBe("revoked");
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
