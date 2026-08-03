import { execFileSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";

import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import type { E2eTestResources } from "./support/isolation";
import { expectUiLocale, setUiLocale } from "./support/locale";

test.setTimeout(180_000);
const uiLocale = "en-US";
test.use({ locale: uiLocale });

const apiBaseUrl = (
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:18000"
).replace(/\/+$/, "");
const repositoryRoot = process.env.PLAYWRIGHT_REPOSITORY_ROOT;
const composeProject = process.env.PLAYWRIGHT_COMPOSE_PROJECT_NAME;
const e2eRepository = process.env.PLAYWRIGHT_E2E_REPOSITORY_PATH;
const fixtureRepository =
  process.env.PLAYWRIGHT_WORKSPACE_FIXTURE_REPOSITORY_PATH;

type JsonObject = Record<string, unknown>;

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
      async () => {
        const job = await apiJson(
          request,
          "get",
          `/api/v1/runner-jobs/${jobId}`,
        );
        return job.state;
      },
      { timeout: 60_000 },
    )
    .toMatch(/^(succeeded|failed|cancelled)$/);
  return apiJson(request, "get", `/api/v1/runner-jobs/${jobId}`);
}

async function approvedGrant(
  request: APIRequestContext,
  resources: E2eTestResources,
): Promise<JsonObject> {
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
        reason: "Synthetic browser security-flow approval.",
      },
    );
  }
  expect(grant.status).toBe("approved");
  resources.trackGrant(requireString(grant.id, "Grant ID"));
  return grant;
}

async function preparedWorkspace(
  request: APIRequestContext,
  resources: E2eTestResources,
  grant: JsonObject,
): Promise<JsonObject> {
  const action = await apiJson(request, "post", "/api/v1/workspaces", {
    grant_id: requireString(grant.id, "Grant ID"),
  });
  const workspace = action.workspace as JsonObject;
  const job = action.job as JsonObject;
  resources.trackWorkspace(requireString(workspace.id, "Workspace ID"));
  resources.trackJob(requireString(job.id, "Workspace prepare Job ID"));
  const completed = await waitForJob(
    request,
    requireString(job.id, "Workspace prepare Job ID"),
  );
  expect(completed.state).toBe("succeeded");
  return workspace;
}

function compose(...arguments_: string[]): string {
  if (
    !repositoryRoot ||
    !composeProject ||
    !e2eRepository ||
    !fixtureRepository
  ) {
    throw new Error("Playwright Compose security context is unavailable");
  }
  return execFileSync(
    "docker",
    [
      "compose",
      "-p",
      composeProject,
      "-f",
      `${repositoryRoot}/compose.yaml`,
      "-f",
      `${repositoryRoot}/infra/compose.workspace.yaml`,
      "-f",
      `${repositoryRoot}/infra/compose.e2e.yaml`,
      ...arguments_,
    ],
    {
      cwd: repositoryRoot,
      encoding: "utf-8",
      env: {
        ...process.env,
        E2E_REPOSITORY_PATH: e2eRepository,
        WORKSPACE_FIXTURE_REPOSITORY_PATH: fixtureRepository,
      },
      timeout: 30_000,
    },
  ).trim();
}

function runnerPython(script: string): string {
  return compose(
    "run",
    "--rm",
    "--no-deps",
    "--entrypoint",
    "python",
    "runner",
    "-c",
    script,
  );
}

function workspaceHex(workspaceId: string): string {
  const normalized = workspaceId.replaceAll("-", "");
  if (!/^[0-9a-f]{32}$/.test(normalized)) {
    throw new Error("Workspace ID is invalid");
  }
  return normalized;
}

function inspectWorkspace(workspaceId: string): JsonObject {
  const workspaceName = `workspace-${workspaceHex(workspaceId)}`;
  const output = runnerPython(
    "import json;" +
      "from pathlib import Path;" +
      `w=Path('/var/lib/visual-engineer-runner/workspaces/${workspaceName}');` +
      "p=w/'sandbox/original.txt';" +
      "m=list(Path('/var/lib/visual-engineer-runner/mirrors').glob('mirror-*'));" +
      "print(json.dumps({'workspace':w.is_dir(),'content':p.read_text()," +
      "'mirror':any(x.is_dir() for x in m)}))",
  );
  const value: unknown = JSON.parse(output);
  if (typeof value !== "object" || value === null) {
    throw new Error("Runner Workspace inspection returned invalid JSON");
  }
  return value as JsonObject;
}

function hideRegistry(workspaceId: string): void {
  const workspaceName = `workspace-${workspaceHex(workspaceId)}`;
  runnerPython(
    "from pathlib import Path;" +
      `p=Path('/var/lib/visual-engineer-runner/registry/${workspaceName}.json');` +
      "b=p.with_name(p.name+'.e2e-backup');" +
      "p.rename(b)",
  );
}

function restoreRegistryAndControlState(workspaceId: string): void {
  const workspaceName = `workspace-${workspaceHex(workspaceId)}`;
  runnerPython(
    "from pathlib import Path;" +
      `p=Path('/var/lib/visual-engineer-runner/registry/${workspaceName}.json');` +
      "b=p.with_name(p.name+'.e2e-backup');" +
      "b.rename(p)",
  );
  compose(
    "exec",
    "-T",
    "db",
    "psql",
    "-U",
    "visualengineer",
    "-d",
    "visualengineer",
    "-v",
    "ON_ERROR_STOP=1",
    "-c",
    `UPDATE workspaces SET state='sealed', error_code=NULL, error_message=NULL, active_attempt_id=NULL WHERE id='${workspaceId}'::uuid AND state='recovery_required'`,
  );
}

function restoreRevokedGrantForCleanup(grantId: string): void {
  workspaceHex(grantId);
  compose(
    "exec",
    "-T",
    "db",
    "psql",
    "-U",
    "visualengineer",
    "-d",
    "visualengineer",
    "-v",
    "ON_ERROR_STOP=1",
    "-c",
    `UPDATE execution_grants SET status='approved', revocation_requested_at=NULL, revoked_at=NULL WHERE id='${grantId}'::uuid AND status IN ('revoke_requested', 'revoked')`,
  );
}

test("Phase 4 revocation and missing ownership proof stay fail-closed and visible", async ({
  context,
  page,
  request,
  resources,
}) => {
  await setUiLocale(context, uiLocale);
  let revokedGrantId: string | undefined;
  let hiddenRegistryWorkspaceId: string | undefined;
  try {
    const firstGrant = await approvedGrant(request, resources);
    revokedGrantId = requireString(firstGrant.id, "Grant ID");
    const revokedWorkspace = await preparedWorkspace(
      request,
      resources,
      firstGrant,
    );
    const revokedWorkspaceId = requireString(
      revokedWorkspace.id,
      "Revocation Workspace ID",
    );
    await page.goto(`/workspaces/${revokedWorkspaceId}`);
    await expectUiLocale(page, uiLocale);
    await expect(page.locator('[data-status="ready"]')).toBeVisible({
      timeout: 30_000,
    });
    await page.getByRole("button", { name: "Read text" }).click();
    await expect(page.getByText("Original fixture text.")).toBeVisible({
      timeout: 30_000,
    });

    const revoked = await apiJson(
      request,
      "post",
      `/api/v1/execution-grants/${requireString(firstGrant.id, "Grant ID")}/revoke`,
    );
    expect(revoked.status).toBe("revoked");
    expect(revoked.in_flight_permit_count).toBe(0);
    await page.goto("/execution-grants");
    await expect(page.locator('[data-status="revoked"]').first()).toBeVisible();
    await expect(page.getByText(/Revocation effective/).first()).toBeVisible();

    await page.goto(`/workspaces/${revokedWorkspaceId}`);
    await page
      .getByLabel("UTF-8 content")
      .fill("This write must be denied after effective revocation.\n");
    await expect(
      page.getByRole("button", { name: "Replace text" }),
    ).toBeDisabled();
    await expect(page.getByRole("button", { name: "Discard" })).toBeDisabled();
    const deniedWrite = await request.post(
      `${apiBaseUrl}/api/v1/workspaces/${revokedWorkspaceId}/actions/write-text`,
      {
        data: {
          mode: "replace",
          relative_path: "sandbox/original.txt",
          content: "This write must be denied after effective revocation.\n",
          expected_sha256: createHash("sha256")
            .update("Original fixture text.\n")
            .digest("hex"),
        },
        headers: { "X-Request-ID": randomUUID() },
      },
    );
    expect(deniedWrite.status()).toBe(409);
    expect(await deniedWrite.json()).toMatchObject({
      error: { code: "execution_grant_inactive" },
    });
    const revokedInspection = inspectWorkspace(revokedWorkspaceId);
    expect(revokedInspection.workspace).toBe(true);
    expect(revokedInspection.content).toBe("Original fixture text.\n");
    expect(revokedInspection.mirror).toBe(true);
    await expectAccessibleAndContained(page);

    const recoveryGrant = await approvedGrant(request, resources);
    const recoveryWorkspace = await preparedWorkspace(
      request,
      resources,
      recoveryGrant,
    );
    const recoveryWorkspaceId = requireString(
      recoveryWorkspace.id,
      "Recovery Workspace ID",
    );
    const sealed = await apiJson(
      request,
      "post",
      `/api/v1/workspaces/${recoveryWorkspaceId}/actions/diff`,
    );
    const sealedJob = sealed.job as JsonObject;
    const completedSeal = await waitForJob(
      request,
      requireString(sealedJob.id, "Recovery seal Job ID"),
    );
    expect(completedSeal.state).toBe("succeeded");
    await page.goto(`/workspaces/${recoveryWorkspaceId}`);
    await expect(page.locator('[data-status="sealed"]')).toBeVisible({
      timeout: 30_000,
    });
    hideRegistry(recoveryWorkspaceId);
    hiddenRegistryWorkspaceId = recoveryWorkspaceId;
    await page.getByRole("button", { name: "Discard" }).click();
    await expect(page.locator('[data-status="recovery_required"]')).toBeVisible(
      { timeout: 30_000 },
    );
    await expect(
      page.getByText("Workspace ownership proof is missing."),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Discard" })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Replace text" }),
    ).toBeDisabled();
    const recoveryInspection = inspectWorkspace(recoveryWorkspaceId);
    expect(recoveryInspection.workspace).toBe(true);
    expect(recoveryInspection.content).toBe("Original fixture text.\n");
    expect(recoveryInspection.mirror).toBe(true);
    await expectAccessibleAndContained(page);

    restoreRegistryAndControlState(recoveryWorkspaceId);
    hiddenRegistryWorkspaceId = undefined;
    const discarded = await apiJson(
      request,
      "post",
      `/api/v1/workspaces/${recoveryWorkspaceId}/actions/discard`,
    );
    const discardJob = discarded.job as JsonObject;
    const completedDiscard = await waitForJob(
      request,
      requireString(discardJob.id, "Cleanup discard Job ID"),
    );
    expect(completedDiscard.state).toBe("succeeded");
    await apiJson(
      request,
      "post",
      `/api/v1/execution-grants/${requireString(recoveryGrant.id, "Grant ID")}/revoke`,
    );
  } finally {
    try {
      if (hiddenRegistryWorkspaceId) {
        restoreRegistryAndControlState(hiddenRegistryWorkspaceId);
      }
    } finally {
      if (revokedGrantId) restoreRevokedGrantForCleanup(revokedGrantId);
    }
  }
});
