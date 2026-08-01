import type { paths } from "@visual-engineer/api-contract";

type OperationAt<
  Path extends keyof paths,
  Method extends keyof paths[Path],
> = paths[Path][Method];

type JsonResponse<Operation, Status extends number> = Operation extends {
  responses: infer Responses;
}
  ? Status extends keyof Responses
    ? Responses[Status] extends {
        content: { "application/json": infer Body };
      }
      ? Body
      : never
    : never
  : never;

type JsonRequest<Operation> = Operation extends {
  requestBody: { content: { "application/json": infer Body } };
}
  ? Body
  : never;

type TaskDetailOperation = OperationAt<"/api/v1/tasks/{task_id}", "get">;
type TaskListOperation = OperationAt<"/api/v1/tasks", "get">;
type TaskCreateOperation = OperationAt<"/api/v1/tasks", "post">;
type RunCreateOperation = OperationAt<"/api/v1/tasks/{task_id}/runs", "post">;
type RunListOperation = OperationAt<"/api/v1/tasks/{task_id}/runs", "get">;
type RunDetailOperation = OperationAt<"/api/v1/runs/{run_id}", "get">;
type SnapshotCreateOperation = OperationAt<
  "/api/v1/runs/{run_id}/snapshot",
  "post"
>;
type SnapshotDetailOperation = OperationAt<
  "/api/v1/runs/{run_id}/snapshot",
  "get"
>;
type PlanCreateOperation = OperationAt<"/api/v1/runs/{run_id}/plans", "post">;
type PlanListOperation = OperationAt<"/api/v1/runs/{run_id}/plans", "get">;
type PlanRevisionOperation = OperationAt<
  "/api/v1/runs/{run_id}/plans/{version}/revisions",
  "post"
>;
type PlanSubmitOperation = OperationAt<
  "/api/v1/runs/{run_id}/plans/{version}/submit",
  "post"
>;
type PlanDecisionOperation = OperationAt<
  "/api/v1/runs/{run_id}/plans/{version}/decisions",
  "post"
>;
type AuditListOperation = OperationAt<
  "/api/v1/runs/{run_id}/audit-events",
  "get"
>;
type RunnerListOperation = OperationAt<"/api/v1/runners", "get">;
type RunnerDetailOperation = OperationAt<"/api/v1/runners/{runner_id}", "get">;
type RunnerRevokeOperation = OperationAt<
  "/api/v1/runners/{runner_id}/revoke",
  "post"
>;
type RunnerJobListOperation = OperationAt<"/api/v1/runner-jobs", "get">;
type RunnerJobCreateOperation = OperationAt<"/api/v1/runner-jobs", "post">;
type RunnerJobDetailOperation = OperationAt<
  "/api/v1/runner-jobs/{job_id}",
  "get"
>;
type RunnerJobCancelOperation = OperationAt<
  "/api/v1/runner-jobs/{job_id}/cancel",
  "post"
>;
type RunnerJobEventsOperation = OperationAt<
  "/api/v1/runner-jobs/{job_id}/events",
  "get"
>;
type RepositoryListOperation = OperationAt<"/api/v1/repositories", "get">;
type EligibleContextListOperation = OperationAt<
  "/api/v1/execution-grants/eligible-contexts",
  "get"
>;
type ExecutionGrantListOperation = OperationAt<
  "/api/v1/execution-grants",
  "get"
>;
type ExecutionGrantCreateOperation = OperationAt<
  "/api/v1/execution-grants",
  "post"
>;
type ExecutionGrantDecisionOperation = OperationAt<
  "/api/v1/execution-grants/{grant_id}/decisions",
  "post"
>;
type ExecutionGrantRevokeOperation = OperationAt<
  "/api/v1/execution-grants/{grant_id}/revoke",
  "post"
>;
type WorkspaceListOperation = OperationAt<"/api/v1/workspaces", "get">;
type WorkspaceCreateOperation = OperationAt<"/api/v1/workspaces", "post">;
type WorkspaceDetailOperation = OperationAt<
  "/api/v1/workspaces/{workspace_id}",
  "get"
>;
type WorkspaceDirectoryOperation = OperationAt<
  "/api/v1/workspaces/{workspace_id}/actions/list",
  "post"
>;
type WorkspaceReadOperation = OperationAt<
  "/api/v1/workspaces/{workspace_id}/actions/read-text",
  "post"
>;
type WorkspaceWriteOperation = OperationAt<
  "/api/v1/workspaces/{workspace_id}/actions/write-text",
  "post"
>;
type WorkspaceEventsOperation = OperationAt<
  "/api/v1/workspaces/{workspace_id}/events",
  "get"
>;
type WorkspaceCheckpointsOperation = OperationAt<
  "/api/v1/workspaces/{workspace_id}/checkpoints",
  "get"
>;
type ValidationProfileListOperation = OperationAt<
  "/api/v1/validation-profiles",
  "get"
>;
type ValidationRunListOperation = OperationAt<"/api/v1/validation-runs", "get">;
type ValidationRunCreateOperation = OperationAt<
  "/api/v1/validation-runs",
  "post"
>;
type ValidationRunDetailOperation = OperationAt<
  "/api/v1/validation-runs/{validation_run_id}",
  "get"
>;
type ValidationRunCancelOperation = OperationAt<
  "/api/v1/validation-runs/{validation_run_id}/cancel",
  "post"
>;
type ValidationSuiteListOperation = OperationAt<
  "/api/v1/validation-suites",
  "get"
>;
type ValidationSuiteRunListOperation = OperationAt<
  "/api/v1/validation-suite-runs",
  "get"
>;
type ValidationSuiteRunCreateOperation = OperationAt<
  "/api/v1/validation-suite-runs",
  "post"
>;
type ValidationSuiteRunDetailOperation = OperationAt<
  "/api/v1/validation-suite-runs/{suite_run_id}",
  "get"
>;
type ValidationSuiteRunCancelOperation = OperationAt<
  "/api/v1/validation-suite-runs/{suite_run_id}/cancel",
  "post"
>;
type ValidationSuiteRunRetryOperation = OperationAt<
  "/api/v1/validation-suite-runs/{suite_run_id}/retry",
  "post"
>;
type ReviewPackageListOperation = OperationAt<"/api/v1/review-packages", "get">;
type ReviewPackageCreateOperation = OperationAt<
  "/api/v1/review-packages",
  "post"
>;
type ReviewPackageDetailOperation = OperationAt<
  "/api/v1/review-packages/{package_id}",
  "get"
>;
type ReviewPackageFreshnessOperation = OperationAt<
  "/api/v1/review-packages/{package_id}/freshness",
  "post"
>;
type ReviewDecisionOperation = OperationAt<
  "/api/v1/review-packages/{package_id}/decisions",
  "post"
>;
type ReleaseReadinessOperation = OperationAt<
  "/api/v1/review-packages/{package_id}/readiness",
  "post"
>;
type DeliveryAuthorizationListOperation = OperationAt<
  "/api/v1/delivery-authorizations",
  "get"
>;
type DeliveryAuthorizationCreateOperation = OperationAt<
  "/api/v1/delivery-authorizations",
  "post"
>;
type DeliveryAuthorizationDetailOperation = OperationAt<
  "/api/v1/delivery-authorizations/{authorization_id}",
  "get"
>;
type DeliveryAuthorizationDecisionOperation = OperationAt<
  "/api/v1/delivery-authorizations/{authorization_id}/decisions",
  "post"
>;
type DeliveryAuthorizationDispatchOperation = OperationAt<
  "/api/v1/delivery-authorizations/{authorization_id}/dispatch",
  "post"
>;
type DeliveryPreviewOperation = OperationAt<
  "/api/v1/delivery-authorizations/{authorization_id}/preview",
  "get"
>;

export type Task = JsonResponse<TaskDetailOperation, 200>;
export type CreateTaskInput = JsonRequest<TaskCreateOperation>;
type TaskListPayload = JsonResponse<TaskListOperation, 200>;
type CreatedTask = JsonResponse<TaskCreateOperation, 201>;
export type Run = JsonResponse<RunDetailOperation, 200>;
export type CreateRunInput = JsonRequest<RunCreateOperation>;
type RunListPayload = JsonResponse<RunListOperation, 200>;
type CreatedRun = JsonResponse<RunCreateOperation, 201>;
export type Snapshot = JsonResponse<SnapshotDetailOperation, 200>;
type CreatedSnapshot = JsonResponse<SnapshotCreateOperation, 201>;
export type Plan = JsonResponse<PlanSubmitOperation, 200>;
export type CreatePlanInput = JsonRequest<PlanCreateOperation>;
export type PlanRevisionInput = JsonRequest<PlanRevisionOperation>;
export type PlanDecisionInput = JsonRequest<PlanDecisionOperation>;
type CreatedPlan = JsonResponse<PlanCreateOperation, 201>;
type RevisedPlan = JsonResponse<PlanRevisionOperation, 201>;
type PlanListPayload = JsonResponse<PlanListOperation, 200>;
export type ApprovalDecision = JsonResponse<PlanDecisionOperation, 201>;
type AuditListPayload = JsonResponse<AuditListOperation, 200>;
export type AuditEvent = AuditListPayload extends {
  items: Array<infer Item>;
}
  ? Item
  : never;
type RunnerListPayload = JsonResponse<RunnerListOperation, 200>;
export type Runner = JsonResponse<RunnerDetailOperation, 200>;
type RunnerJobListPayload = JsonResponse<RunnerJobListOperation, 200>;
export type RunnerJob = JsonResponse<RunnerJobDetailOperation, 200>;
type WorkspaceListResult = Extract<
  NonNullable<RunnerJob["result"]>,
  { kind: "workspace_list_v1" }
>;
export type WorkspaceEntry = WorkspaceListResult["entries"][number];
export type CreateRunnerJobInput = JsonRequest<RunnerJobCreateOperation>;
type CreatedRunnerJob = JsonResponse<RunnerJobCreateOperation, 201>;
type RunnerJobEventListPayload = JsonResponse<RunnerJobEventsOperation, 200>;
export type RunnerJobEvent = RunnerJobEventListPayload extends {
  items: Array<infer Item>;
}
  ? Item
  : never;
type RepositoryListPayload = JsonResponse<RepositoryListOperation, 200>;
export type RepositoryHandle = RepositoryListPayload["items"][number];
type EligibleContextListPayload = JsonResponse<
  EligibleContextListOperation,
  200
>;
export type EligibleExecutionContext =
  EligibleContextListPayload["items"][number];
type ExecutionGrantListPayload = JsonResponse<ExecutionGrantListOperation, 200>;
export type ExecutionGrant = ExecutionGrantListPayload["items"][number];
export type CreateExecutionGrantInput =
  JsonRequest<ExecutionGrantCreateOperation>;
export type ExecutionGrantDecisionInput =
  JsonRequest<ExecutionGrantDecisionOperation>;
type WorkspaceListPayload = JsonResponse<WorkspaceListOperation, 200>;
export type Workspace = WorkspaceListPayload["items"][number];
export type WorkspaceAction = JsonResponse<WorkspaceDirectoryOperation, 200>;
export type WorkspaceListInput = JsonRequest<WorkspaceDirectoryOperation>;
export type WorkspaceReadInput = JsonRequest<WorkspaceReadOperation>;
export type WorkspaceWriteInput = JsonRequest<WorkspaceWriteOperation>;
type WorkspaceEventListPayload = JsonResponse<WorkspaceEventsOperation, 200>;
export type WorkspaceEvent = WorkspaceEventListPayload["items"][number];
type WorkspaceCheckpointListPayload = JsonResponse<
  WorkspaceCheckpointsOperation,
  200
>;
export type WorkspaceCheckpoint =
  WorkspaceCheckpointListPayload["items"][number];
type ValidationProfileListPayload = JsonResponse<
  ValidationProfileListOperation,
  200
>;
export type ValidationProfile = ValidationProfileListPayload["items"][number];
type ValidationRunListPayload = JsonResponse<ValidationRunListOperation, 200>;
export type ValidationRun = JsonResponse<ValidationRunDetailOperation, 200>;
export type CreateValidationRunInput =
  JsonRequest<ValidationRunCreateOperation>;
type ValidationSuiteListPayload = JsonResponse<
  ValidationSuiteListOperation,
  200
>;
export type ValidationSuite = ValidationSuiteListPayload["items"][number];
type ValidationSuiteRunListPayload = JsonResponse<
  ValidationSuiteRunListOperation,
  200
>;
export type ValidationSuiteRun = JsonResponse<
  ValidationSuiteRunDetailOperation,
  200
>;
export type CreateValidationSuiteRunInput =
  JsonRequest<ValidationSuiteRunCreateOperation>;
export type RetryValidationSuiteRunInput =
  JsonRequest<ValidationSuiteRunRetryOperation>;
type ReviewPackageListPayload = JsonResponse<ReviewPackageListOperation, 200>;
export type ReviewPackage = JsonResponse<ReviewPackageDetailOperation, 200>;
export type CreateReviewPackageInput =
  JsonRequest<ReviewPackageCreateOperation>;
export type ReviewDecisionInput = JsonRequest<ReviewDecisionOperation>;
type DeliveryAuthorizationListPayload = JsonResponse<
  DeliveryAuthorizationListOperation,
  200
>;
export type DeliveryAuthorization = JsonResponse<
  DeliveryAuthorizationDetailOperation,
  200
>;
export type CreateDeliveryAuthorizationInput =
  JsonRequest<DeliveryAuthorizationCreateOperation>;
export type DeliveryAuthorizationDecisionInput =
  JsonRequest<DeliveryAuthorizationDecisionOperation>;
export type DeliveryDispatchInput =
  JsonRequest<DeliveryAuthorizationDispatchOperation>;
export type DeliveryPreview = JsonResponse<DeliveryPreviewOperation, 200>;

export type HealthCheck = "live" | "ready";
export type RepositoryKind = CreateTaskInput extends {
  repository_kind: infer Kind;
}
  ? Kind
  : never;

interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
  code?: string;
  detail?: string | Array<{ msg?: string }>;
  message?: string;
  request_id?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(
    message: string,
    options: { status: number; code?: string; requestId?: string },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code ?? "unexpected_error";
    this.requestId = options.requestId;
  }
}

const apiBaseUrl = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload | undefined;

  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    // Some upstream errors are intentionally not JSON.
  }

  const validationMessage = Array.isArray(payload?.detail)
    ? payload.detail
        .map((issue) => issue.msg)
        .filter(Boolean)
        .join("; ")
    : payload?.detail;
  const message =
    payload?.error?.message ??
    payload?.message ??
    validationMessage ??
    `请求失败（HTTP ${response.status}）`;

  return new ApiError(message, {
    status: response.status,
    code: payload?.error?.code ?? payload?.code,
    requestId:
      payload?.error?.request_id ??
      payload?.request_id ??
      response.headers.get("x-request-id") ??
      undefined,
  });
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<{ data: T; response: Response }> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("无法连接 API，请确认服务正在运行。", {
      status: 0,
      code: "network_error",
    });
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return {
    data: (await response.json()) as T,
    response,
  };
}

export async function getHealth(check: HealthCheck): Promise<boolean> {
  await request<unknown>(`/health/${check}`, { cache: "no-store" });
  return true;
}

export async function listTasks(): Promise<Task[]> {
  const { data } = await request<TaskListPayload>(
    "/api/v1/tasks?limit=50&offset=0",
    { cache: "no-store" },
  );

  if (Array.isArray(data)) {
    return data as Task[];
  }

  if (
    typeof data === "object" &&
    data !== null &&
    "items" in data &&
    Array.isArray(data.items)
  ) {
    return data.items as Task[];
  }

  throw new ApiError("API 返回了无法识别的任务列表。", {
    status: 502,
    code: "invalid_response",
  });
}

export async function getTask(taskId: string): Promise<Task> {
  const { data } = await request<Task>(
    `/api/v1/tasks/${encodeURIComponent(taskId)}`,
    { cache: "no-store" },
  );
  return data;
}

export async function createTask(
  input: CreateTaskInput,
  idempotencyKey: string,
): Promise<{ task: Task; replayed: boolean }> {
  const { data, response } = await request<CreatedTask>("/api/v1/tasks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(input),
  });

  return {
    task: data as Task,
    replayed: response.headers.get("idempotent-replay") === "true",
  };
}

export async function listRuns(taskId: string): Promise<Run[]> {
  const { data } = await request<RunListPayload>(
    `/api/v1/tasks/${encodeURIComponent(taskId)}/runs`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function getRun(runId: string): Promise<Run> {
  const { data } = await request<Run>(
    `/api/v1/runs/${encodeURIComponent(runId)}`,
    { cache: "no-store" },
  );
  return data;
}

export async function startRun(
  taskId: string,
  idempotencyKey: string,
): Promise<{ run: Run; replayed: boolean }> {
  const input: CreateRunInput = {
    permission_level: "read_only",
    snapshot_mode: "git_head",
  };
  const { data, response } = await request<CreatedRun>(
    `/api/v1/tasks/${encodeURIComponent(taskId)}/runs`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(input),
    },
  );
  return {
    run: data as Run,
    replayed: response.headers.get("idempotent-replay") === "true",
  };
}

export async function getSnapshot(runId: string): Promise<Snapshot> {
  const { data } = await request<Snapshot>(
    `/api/v1/runs/${encodeURIComponent(runId)}/snapshot`,
    { cache: "no-store" },
  );
  return data;
}

export async function createSnapshot(runId: string): Promise<Snapshot> {
  const { data } = await request<CreatedSnapshot>(
    `/api/v1/runs/${encodeURIComponent(runId)}/snapshot`,
    { method: "POST" },
  );
  return data as Snapshot;
}

export async function listPlans(runId: string): Promise<Plan[]> {
  const { data } = await request<PlanListPayload>(
    `/api/v1/runs/${encodeURIComponent(runId)}/plans`,
    { cache: "no-store" },
  );
  return data.items as Plan[];
}

export async function createPlan(
  runId: string,
  input: CreatePlanInput,
): Promise<Plan> {
  const { data } = await request<CreatedPlan>(
    `/api/v1/runs/${encodeURIComponent(runId)}/plans`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return data as Plan;
}

export async function revisePlan(
  runId: string,
  version: number,
  input: PlanRevisionInput,
): Promise<Plan> {
  const { data } = await request<RevisedPlan>(
    `/api/v1/runs/${encodeURIComponent(runId)}/plans/${version}/revisions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return data as Plan;
}

export async function submitPlan(
  runId: string,
  version: number,
): Promise<Plan> {
  const { data } = await request<Plan>(
    `/api/v1/runs/${encodeURIComponent(runId)}/plans/${version}/submit`,
    { method: "POST" },
  );
  return data;
}

export async function decidePlan(
  runId: string,
  version: number,
  input: PlanDecisionInput,
): Promise<ApprovalDecision> {
  const { data } = await request<ApprovalDecision>(
    `/api/v1/runs/${encodeURIComponent(runId)}/plans/${version}/decisions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function listAuditEvents(runId: string): Promise<AuditEvent[]> {
  const { data } = await request<AuditListPayload>(
    `/api/v1/runs/${encodeURIComponent(runId)}/audit-events`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function cancelRun(runId: string, reason?: string): Promise<Run> {
  const input: { reason?: string } = reason ? { reason } : {};
  const { data } = await request<Run>(
    `/api/v1/runs/${encodeURIComponent(runId)}/cancel`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function listRunners(): Promise<Runner[]> {
  const { data } = await request<RunnerListPayload>("/api/v1/runners", {
    cache: "no-store",
  });
  return data.items;
}

export async function getRunner(runnerId: string): Promise<Runner> {
  const { data } = await request<Runner>(
    `/api/v1/runners/${encodeURIComponent(runnerId)}`,
    { cache: "no-store" },
  );
  return data;
}

export async function revokeRunner(runnerId: string): Promise<Runner> {
  const { data } = await request<JsonResponse<RunnerRevokeOperation, 200>>(
    `/api/v1/runners/${encodeURIComponent(runnerId)}/revoke`,
    {
      method: "POST",
      headers: { "X-Request-ID": crypto.randomUUID() },
    },
  );
  return data;
}

export async function listRunnerJobs(): Promise<RunnerJob[]> {
  const { data } = await request<RunnerJobListPayload>("/api/v1/runner-jobs", {
    cache: "no-store",
  });
  return data.items;
}

export async function createRunnerJob(
  input: CreateRunnerJobInput,
): Promise<RunnerJob> {
  const { data } = await request<CreatedRunnerJob>("/api/v1/runner-jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data as RunnerJob;
}

export async function getRunnerJob(jobId: string): Promise<RunnerJob> {
  const { data } = await request<RunnerJob>(
    `/api/v1/runner-jobs/${encodeURIComponent(jobId)}`,
    { cache: "no-store" },
  );
  return data;
}

export async function cancelRunnerJob(jobId: string): Promise<RunnerJob> {
  const { data } = await request<JsonResponse<RunnerJobCancelOperation, 200>>(
    `/api/v1/runner-jobs/${encodeURIComponent(jobId)}/cancel`,
    {
      method: "POST",
      headers: { "X-Request-ID": crypto.randomUUID() },
    },
  );
  return data;
}

export async function listRunnerJobEvents(
  jobId: string,
): Promise<RunnerJobEvent[]> {
  const { data } = await request<RunnerJobEventListPayload>(
    `/api/v1/runner-jobs/${encodeURIComponent(jobId)}/events`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function listRepositories(): Promise<RepositoryHandle[]> {
  const { data } = await request<RepositoryListPayload>(
    "/api/v1/repositories",
    { cache: "no-store" },
  );
  return data.items;
}

export async function listEligibleExecutionContexts(): Promise<
  EligibleExecutionContext[]
> {
  const { data } = await request<EligibleContextListPayload>(
    "/api/v1/execution-grants/eligible-contexts",
    { cache: "no-store" },
  );
  return data.items;
}

export async function listExecutionGrants(): Promise<ExecutionGrant[]> {
  const { data } = await request<ExecutionGrantListPayload>(
    "/api/v1/execution-grants",
    { cache: "no-store" },
  );
  return data.items;
}

export async function createExecutionGrant(
  input: CreateExecutionGrantInput,
): Promise<ExecutionGrant> {
  const { data } = await request<
    JsonResponse<ExecutionGrantCreateOperation, 201>
  >("/api/v1/execution-grants", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function decideExecutionGrant(
  grantId: string,
  input: ExecutionGrantDecisionInput,
): Promise<ExecutionGrant> {
  const { data } = await request<
    JsonResponse<ExecutionGrantDecisionOperation, 200>
  >(`/api/v1/execution-grants/${encodeURIComponent(grantId)}/decisions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function revokeExecutionGrant(
  grantId: string,
): Promise<ExecutionGrant> {
  const { data } = await request<
    JsonResponse<ExecutionGrantRevokeOperation, 200>
  >(`/api/v1/execution-grants/${encodeURIComponent(grantId)}/revoke`, {
    method: "POST",
    headers: { "X-Request-ID": crypto.randomUUID() },
  });
  return data;
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const { data } = await request<WorkspaceListPayload>("/api/v1/workspaces", {
    cache: "no-store",
  });
  return data.items;
}

export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  const { data } = await request<JsonResponse<WorkspaceDetailOperation, 200>>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}`,
    {
      cache: "no-store",
    },
  );
  return data;
}

export async function createWorkspace(
  grantId: string,
): Promise<WorkspaceAction> {
  const { data } = await request<JsonResponse<WorkspaceCreateOperation, 201>>(
    "/api/v1/workspaces",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify({ grant_id: grantId }),
    },
  );
  return data;
}

async function workspaceAction(
  workspaceId: string,
  action: "status" | "diff" | "rollback" | "discard",
): Promise<WorkspaceAction> {
  const { data } = await request<WorkspaceAction>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/actions/${action}`,
    {
      method: "POST",
      headers: { "X-Request-ID": crypto.randomUUID() },
    },
  );
  return data;
}

export async function listWorkspaceDirectory(
  workspaceId: string,
  input: WorkspaceListInput,
): Promise<WorkspaceAction> {
  const { data } = await request<WorkspaceAction>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/actions/list`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function readWorkspaceText(
  workspaceId: string,
  input: WorkspaceReadInput,
): Promise<WorkspaceAction> {
  const { data } = await request<WorkspaceAction>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/actions/read-text`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function writeWorkspaceText(
  workspaceId: string,
  input: WorkspaceWriteInput,
): Promise<WorkspaceAction> {
  const { data } = await request<WorkspaceAction>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/actions/write-text`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export const getWorkspaceStatus = (workspaceId: string) =>
  workspaceAction(workspaceId, "status");
export const getWorkspaceDiff = (workspaceId: string) =>
  workspaceAction(workspaceId, "diff");
export const rollbackWorkspace = (workspaceId: string) =>
  workspaceAction(workspaceId, "rollback");
export const discardWorkspace = (workspaceId: string) =>
  workspaceAction(workspaceId, "discard");

export async function listWorkspaceEvents(
  workspaceId: string,
): Promise<WorkspaceEvent[]> {
  const { data } = await request<WorkspaceEventListPayload>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/events`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function listWorkspaceCheckpoints(
  workspaceId: string,
): Promise<WorkspaceCheckpoint[]> {
  const { data } = await request<WorkspaceCheckpointListPayload>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/checkpoints`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function listValidationProfiles(): Promise<ValidationProfile[]> {
  const { data } = await request<ValidationProfileListPayload>(
    "/api/v1/validation-profiles",
    { cache: "no-store" },
  );
  return data.items;
}

export async function listValidationRuns(
  workspaceId?: string,
): Promise<ValidationRun[]> {
  const query = workspaceId
    ? `?workspace_id=${encodeURIComponent(workspaceId)}`
    : "";
  const { data } = await request<ValidationRunListPayload>(
    `/api/v1/validation-runs${query}`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function createValidationRun(
  input: CreateValidationRunInput,
  idempotencyKey: string,
): Promise<ValidationRun> {
  const { data } = await request<
    JsonResponse<ValidationRunCreateOperation, 201>
  >("/api/v1/validation-runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function getValidationRun(
  validationRunId: string,
): Promise<ValidationRun> {
  const { data } = await request<ValidationRun>(
    `/api/v1/validation-runs/${encodeURIComponent(validationRunId)}`,
    { cache: "no-store" },
  );
  return data;
}

export async function cancelValidationRun(
  validationRunId: string,
): Promise<ValidationRun> {
  const { data } = await request<
    JsonResponse<ValidationRunCancelOperation, 200>
  >(`/api/v1/validation-runs/${encodeURIComponent(validationRunId)}/cancel`, {
    method: "POST",
    headers: { "X-Request-ID": crypto.randomUUID() },
  });
  return data;
}

export async function listValidationSuites(): Promise<ValidationSuite[]> {
  const { data } = await request<ValidationSuiteListPayload>(
    "/api/v1/validation-suites",
    { cache: "no-store" },
  );
  return data.items;
}

export async function listValidationSuiteRuns(
  workspaceId?: string,
): Promise<ValidationSuiteRun[]> {
  const query = workspaceId
    ? `?workspace_id=${encodeURIComponent(workspaceId)}`
    : "";
  const { data } = await request<ValidationSuiteRunListPayload>(
    `/api/v1/validation-suite-runs${query}`,
    { cache: "no-store" },
  );
  return data.items;
}

export async function createValidationSuiteRun(
  input: CreateValidationSuiteRunInput,
  idempotencyKey: string,
): Promise<ValidationSuiteRun> {
  const { data } = await request<
    JsonResponse<ValidationSuiteRunCreateOperation, 201>
  >("/api/v1/validation-suite-runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function cancelValidationSuiteRun(
  suiteRunId: string,
): Promise<ValidationSuiteRun> {
  const { data } = await request<
    JsonResponse<ValidationSuiteRunCancelOperation, 200>
  >(`/api/v1/validation-suite-runs/${encodeURIComponent(suiteRunId)}/cancel`, {
    method: "POST",
    headers: { "X-Request-ID": crypto.randomUUID() },
  });
  return data;
}

export async function retryValidationSuiteRun(
  suiteRunId: string,
  input: RetryValidationSuiteRunInput,
  idempotencyKey: string,
): Promise<ValidationSuiteRun> {
  const { data } = await request<
    JsonResponse<ValidationSuiteRunRetryOperation, 201>
  >(`/api/v1/validation-suite-runs/${encodeURIComponent(suiteRunId)}/retry`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function listReviewPackages(): Promise<ReviewPackage[]> {
  const { data } = await request<ReviewPackageListPayload>(
    "/api/v1/review-packages",
    { cache: "no-store" },
  );
  return data.items;
}

export async function createReviewPackage(
  input: CreateReviewPackageInput,
  idempotencyKey: string,
): Promise<ReviewPackage> {
  const { data } = await request<
    JsonResponse<ReviewPackageCreateOperation, 201>
  >("/api/v1/review-packages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function refreshReviewPackage(
  packageId: string,
): Promise<ReviewPackage> {
  const { data } = await request<
    JsonResponse<ReviewPackageFreshnessOperation, 200>
  >(`/api/v1/review-packages/${encodeURIComponent(packageId)}/freshness`, {
    method: "POST",
    headers: { "X-Request-ID": crypto.randomUUID() },
  });
  return data;
}

export async function decideReviewPackage(
  packageId: string,
  input: ReviewDecisionInput,
  idempotencyKey = `review-decision-${packageId}-${crypto.randomUUID()}`,
): Promise<ReviewPackage> {
  const { data } = await request<JsonResponse<ReviewDecisionOperation, 200>>(
    `/api/v1/review-packages/${encodeURIComponent(packageId)}/decisions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function evaluateReleaseReadiness(
  packageId: string,
): Promise<ReviewPackage> {
  const { data } = await request<JsonResponse<ReleaseReadinessOperation, 200>>(
    `/api/v1/review-packages/${encodeURIComponent(packageId)}/readiness`,
    {
      method: "POST",
      headers: { "X-Request-ID": crypto.randomUUID() },
    },
  );
  return data;
}

export async function listDeliveryAuthorizations(): Promise<
  DeliveryAuthorization[]
> {
  const { data } = await request<DeliveryAuthorizationListPayload>(
    "/api/v1/delivery-authorizations",
    { cache: "no-store" },
  );
  return data.items;
}

export async function createDeliveryAuthorization(
  input: CreateDeliveryAuthorizationInput,
  idempotencyKey: string,
): Promise<DeliveryAuthorization> {
  const { data } = await request<
    JsonResponse<DeliveryAuthorizationCreateOperation, 201>
  >("/api/v1/delivery-authorizations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify(input),
  });
  return data;
}

export async function decideDeliveryAuthorization(
  authorizationId: string,
  input: DeliveryAuthorizationDecisionInput,
  idempotencyKey: string,
): Promise<DeliveryAuthorization> {
  const { data } = await request<
    JsonResponse<DeliveryAuthorizationDecisionOperation, 200>
  >(
    `/api/v1/delivery-authorizations/${encodeURIComponent(authorizationId)}/decisions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function dispatchLocalDelivery(
  authorizationId: string,
  input: DeliveryDispatchInput,
  idempotencyKey: string,
): Promise<DeliveryAuthorization> {
  const { data } = await request<
    JsonResponse<DeliveryAuthorizationDispatchOperation, 200>
  >(
    `/api/v1/delivery-authorizations/${encodeURIComponent(authorizationId)}/dispatch`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(input),
    },
  );
  return data;
}

export async function getDeliveryPreview(
  authorizationId: string,
): Promise<DeliveryPreview> {
  const { data } = await request<DeliveryPreview>(
    `/api/v1/delivery-authorizations/${encodeURIComponent(authorizationId)}/preview`,
    { cache: "no-store" },
  );
  return data;
}
