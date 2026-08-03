import { randomUUID } from "node:crypto";

import {
  expect,
  type APIRequestContext,
  type TestInfo,
} from "@playwright/test";

type JsonObject = Record<string, unknown>;

const apiBaseUrl = (
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:18000"
).replace(/\/+$/, "");

const terminalJobStates = new Set(["succeeded", "failed", "cancelled"]);
const terminalRunStates = new Set([
  "approved",
  "rejected",
  "failed",
  "cancelled",
]);
const settledWorkspaceStates = new Set([
  "ready",
  "active",
  "sealed",
  "rolled_back",
  "discarded",
  "failed",
  "expired",
  "recovery_required",
  "quarantined",
]);

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} is unavailable`);
  }
  return value;
}

async function responseBody(response: {
  json(): Promise<unknown>;
}): Promise<JsonObject> {
  const body = await response.json();
  if (!isJsonObject(body)) throw new Error("E2E API response is invalid");
  return body;
}

async function apiRequest(
  request: APIRequestContext,
  method: "get" | "post",
  path: string,
  data?: JsonObject,
): Promise<{ body: JsonObject; status: number; ok: boolean }> {
  const response =
    method === "get"
      ? await request.get(`${apiBaseUrl}${path}`)
      : await request.post(`${apiBaseUrl}${path}`, {
          data,
          headers: { "X-Request-ID": randomUUID() },
        });
  return {
    body: await responseBody(response),
    status: response.status(),
    ok: response.ok(),
  };
}

async function apiJson(
  request: APIRequestContext,
  method: "get" | "post",
  path: string,
  data?: JsonObject,
): Promise<JsonObject> {
  const result = await apiRequest(request, method, path, data);
  if (!result.ok) {
    const code = isJsonObject(result.body.error)
      ? result.body.error.code
      : undefined;
    throw new Error(
      `E2E cleanup ${method.toUpperCase()} ${path} failed: ${result.status}${typeof code === "string" ? ` (${code})` : ""}`,
    );
  }
  return result.body;
}

async function waitFor(
  description: string,
  predicate: () => Promise<boolean>,
  timeout = 60_000,
): Promise<void> {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`Timed out while ${description}`);
}

export function uniqueE2eLabel(testInfo: TestInfo, prefix: string): string {
  return [
    prefix,
    testInfo.project.name,
    `w${testInfo.workerIndex}`,
    `r${testInfo.retry}`,
    randomUUID(),
  ].join("-");
}

export class E2eTestResources {
  readonly #request: APIRequestContext;
  readonly #grantIds = new Set<string>();
  readonly #jobIds = new Set<string>();
  readonly #runIds = new Set<string>();
  readonly #workspaceIds = new Set<string>();
  #cleaned = false;

  constructor(request: APIRequestContext) {
    this.#request = request;
  }

  trackGrant(grantId: string): string {
    this.#grantIds.add(grantId);
    return grantId;
  }

  trackJob(jobId: string): string {
    this.#jobIds.add(jobId);
    return jobId;
  }

  trackRun(runId: string): string {
    this.#runIds.add(runId);
    return runId;
  }

  trackWorkspace(workspaceId: string): string {
    this.#workspaceIds.add(workspaceId);
    return workspaceId;
  }

  async #cancelRun(runId: string): Promise<void> {
    const run = await apiJson(this.#request, "get", `/api/v1/runs/${runId}`);
    const status = requireString(run.status, "Run status");
    if (terminalRunStates.has(status)) return;
    const result = await apiRequest(
      this.#request,
      "post",
      `/api/v1/runs/${runId}/cancel`,
      { reason: "Playwright test teardown" },
    );
    if (!result.ok && result.status !== 409) {
      throw new Error(`Run ${runId} cleanup failed: ${result.status}`);
    }
    await waitFor(`waiting for Run ${runId} to terminate`, async () => {
      const current = await apiJson(
        this.#request,
        "get",
        `/api/v1/runs/${runId}`,
      );
      return terminalRunStates.has(requireString(current.status, "Run status"));
    });
  }

  async #cancelJob(jobId: string): Promise<void> {
    let job = await apiJson(
      this.#request,
      "get",
      `/api/v1/runner-jobs/${jobId}`,
    );
    let state = requireString(job.state, "Runner Job state");
    if (!terminalJobStates.has(state)) {
      const result = await apiRequest(
        this.#request,
        "post",
        `/api/v1/runner-jobs/${jobId}/cancel`,
      );
      if (!result.ok && result.status !== 409) {
        throw new Error(`Runner Job ${jobId} cleanup failed: ${result.status}`);
      }
    }
    await waitFor(`waiting for Runner Job ${jobId} to terminate`, async () => {
      job = await apiJson(this.#request, "get", `/api/v1/runner-jobs/${jobId}`);
      state = requireString(job.state, "Runner Job state");
      return terminalJobStates.has(state);
    });
  }

  async #trackWorkspaceJobs(): Promise<void> {
    const response = await apiJson(this.#request, "get", "/api/v1/runner-jobs");
    if (!Array.isArray(response.items)) {
      throw new Error("Runner Job list is invalid during E2E cleanup");
    }
    for (const item of response.items) {
      if (!isJsonObject(item)) continue;
      const workspaceId = item.workspace_id;
      const jobId = item.id;
      if (
        typeof workspaceId === "string" &&
        this.#workspaceIds.has(workspaceId) &&
        typeof jobId === "string"
      ) {
        this.#jobIds.add(jobId);
      }
    }
  }

  async #workspaceState(workspaceId: string): Promise<string> {
    const workspace = await apiJson(
      this.#request,
      "get",
      `/api/v1/workspaces/${workspaceId}`,
    );
    return requireString(workspace.state, "Workspace state");
  }

  async #waitForWorkspaceState(workspaceId: string): Promise<string> {
    let state = await this.#workspaceState(workspaceId);
    await waitFor(
      `waiting for Workspace ${workspaceId} to settle`,
      async () => {
        state = await this.#workspaceState(workspaceId);
        return settledWorkspaceStates.has(state);
      },
    );
    return state;
  }

  async #runWorkspaceAction(
    workspaceId: string,
    action: "diff" | "discard",
  ): Promise<void> {
    const response = await apiJson(
      this.#request,
      "post",
      `/api/v1/workspaces/${workspaceId}/actions/${action}`,
    );
    if (!isJsonObject(response.job)) {
      throw new Error(`Workspace ${action} cleanup Job is invalid`);
    }
    const jobId = this.trackJob(
      requireString(response.job.id, `Workspace ${action} cleanup Job ID`),
    );
    await this.#cancelOrWaitForCleanupJob(jobId);
  }

  async #cancelOrWaitForCleanupJob(jobId: string): Promise<void> {
    await waitFor(`waiting for cleanup Job ${jobId}`, async () => {
      const job = await apiJson(
        this.#request,
        "get",
        `/api/v1/runner-jobs/${jobId}`,
      );
      return terminalJobStates.has(
        requireString(job.state, "Runner Job state"),
      );
    });
    const completed = await apiJson(
      this.#request,
      "get",
      `/api/v1/runner-jobs/${jobId}`,
    );
    expect(completed.state).toBe("succeeded");
  }

  async #cleanupWorkspace(workspaceId: string): Promise<void> {
    let state = await this.#waitForWorkspaceState(workspaceId);
    if (state === "discarded") return;
    if (state === "recovery_required" || state === "quarantined") {
      throw new Error(
        `Workspace ${workspaceId} requires test-specific proof restoration before teardown`,
      );
    }
    if (state === "ready" || state === "active") {
      await this.#runWorkspaceAction(workspaceId, "diff");
      state = await this.#waitForWorkspaceState(workspaceId);
    }
    if (["sealed", "rolled_back", "failed", "expired"].includes(state)) {
      await this.#runWorkspaceAction(workspaceId, "discard");
      state = await this.#waitForWorkspaceState(workspaceId);
    }
    if (state !== "discarded") {
      throw new Error(
        `Workspace ${workspaceId} cleanup ended in unexpected state ${state}`,
      );
    }
  }

  async #revokeGrant(grantId: string): Promise<void> {
    const grant = await apiJson(
      this.#request,
      "get",
      `/api/v1/execution-grants/${grantId}`,
    );
    const status = requireString(grant.status, "Execution Grant status");
    if (["revoked", "rejected", "expired"].includes(status)) return;
    const revoked = await apiJson(
      this.#request,
      "post",
      `/api/v1/execution-grants/${grantId}/revoke`,
    );
    expect(["revoke_requested", "revoked"]).toContain(revoked.status);
    await waitFor(
      `waiting for Execution Grant ${grantId} revocation`,
      async () => {
        const current = await apiJson(
          this.#request,
          "get",
          `/api/v1/execution-grants/${grantId}`,
        );
        return current.status === "revoked";
      },
    );
  }

  async cleanup(): Promise<void> {
    if (this.#cleaned) return;
    this.#cleaned = true;
    const errors: unknown[] = [];
    const capture = async (operation: () => Promise<void>) => {
      try {
        await operation();
      } catch (error) {
        errors.push(error);
      }
    };

    for (const runId of [...this.#runIds].reverse()) {
      await capture(() => this.#cancelRun(runId));
    }
    await capture(() => this.#trackWorkspaceJobs());
    for (const jobId of [...this.#jobIds].reverse()) {
      await capture(() => this.#cancelJob(jobId));
    }
    for (const workspaceId of [...this.#workspaceIds].reverse()) {
      await capture(() => this.#cleanupWorkspace(workspaceId));
    }
    for (const grantId of [...this.#grantIds].reverse()) {
      await capture(() => this.#revokeGrant(grantId));
    }

    if (errors.length > 0) {
      throw new AggregateError(
        errors,
        "Playwright test resource teardown failed",
      );
    }
  }
}
