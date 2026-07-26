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

export type Task = JsonResponse<TaskDetailOperation, 200>;
export type CreateTaskInput = JsonRequest<TaskCreateOperation>;
type TaskListPayload = JsonResponse<TaskListOperation, 200>;
type CreatedTask = JsonResponse<TaskCreateOperation, 201>;

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
