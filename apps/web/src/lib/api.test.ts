import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createTask,
  getHealth,
  listTasks,
  type CreateTaskInput,
} from "./api";
import { taskFixture } from "@/test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
});

function response(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("API client", () => {
  it("reports network failures with a stable error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await expect(getHealth("ready")).rejects.toMatchObject({
      name: "ApiError",
      code: "network_error",
      status: 0,
    });
  });

  it("uses the structured API error and request ID", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(
          {
            error: {
              code: "not_ready",
              message: "Database unavailable",
              request_id: "req-body",
            },
          },
          { status: 503 },
        ),
      ),
    );

    const promise = listTasks();
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({
      code: "not_ready",
      message: "Database unavailable",
      requestId: "req-body",
      status: 503,
    });
  });

  it("normalizes a paginated task list", async () => {
    const task = taskFixture();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          response({ items: [task], total: 1, limit: 50, offset: 0 }),
        ),
    );

    await expect(listTasks()).resolves.toEqual([task]);
  });

  it("sends the generated idempotency key when creating a task", async () => {
    const task = taskFixture();
    const fetchMock = vi.fn().mockResolvedValue(
      response(task, {
        status: 201,
        headers: { "Idempotent-Replay": "false" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const input = {
      title: task.title,
      objective: task.objective,
      repository_kind: task.repository_kind,
      repository_display_name: task.repository_display_name,
      repository_locator: task.repository_locator,
    } as CreateTaskInput;

    await expect(createTask(input, "idem-test-123")).resolves.toEqual({
      task,
      replayed: false,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/tasks"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Idempotency-Key": "idem-test-123",
        }),
      }),
    );
  });
});
