import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  cancelRun,
  createPlan,
  createSnapshot,
  createTask,
  decidePlan,
  getHealth,
  getRun,
  getSnapshot,
  listAuditEvents,
  listPlans,
  listRuns,
  listTasks,
  revisePlan,
  startRun,
  submitPlan,
  type CreateTaskInput,
} from "./api";
import {
  auditFixture,
  planFixture,
  runFixture,
  snapshotFixture,
  taskFixture,
} from "@/test/fixtures";

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

  it("loads Run, Snapshot, Plan, and Audit resources from typed endpoints", async () => {
    const run = runFixture();
    const snapshot = snapshotFixture();
    const plan = planFixture();
    const event = auditFixture();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ items: [run], total: 1 }))
      .mockResolvedValueOnce(response(run))
      .mockResolvedValueOnce(response(snapshot))
      .mockResolvedValueOnce(response({ items: [plan], total: 1 }))
      .mockResolvedValueOnce(response({ items: [event], total: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listRuns(run.task_id)).resolves.toEqual([run]);
    await expect(getRun(run.id)).resolves.toEqual(run);
    await expect(getSnapshot(run.id)).resolves.toEqual(snapshot);
    await expect(listPlans(run.id)).resolves.toEqual([plan]);
    await expect(listAuditEvents(run.id)).resolves.toEqual([event]);
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      expect.stringContaining(`/api/v1/tasks/${run.task_id}/runs`),
      expect.stringContaining(`/api/v1/runs/${run.id}`),
      expect.stringContaining(`/api/v1/runs/${run.id}/snapshot`),
      expect.stringContaining(`/api/v1/runs/${run.id}/plans`),
      expect.stringContaining(`/api/v1/runs/${run.id}/audit-events`),
    ]);
  });

  it("sends only typed Phase 2 mutations", async () => {
    const run = runFixture();
    const snapshot = snapshotFixture();
    const plan = planFixture();
    const decision = {
      id: "a7604849-fce9-44ad-88ea-07a8d3e2e753",
      run_id: run.id,
      plan_id: plan.id,
      decision: "approve" as const,
      comment: null,
      actor_type: "local_user" as const,
      request_id: "decision-request",
      created_at: "2026-07-26T04:03:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(run, { status: 201 }))
      .mockResolvedValueOnce(response(snapshot, { status: 201 }))
      .mockResolvedValueOnce(response(plan, { status: 201 }))
      .mockResolvedValueOnce(response(plan, { status: 201 }))
      .mockResolvedValueOnce(response({ ...plan, status: "awaiting_approval" }))
      .mockResolvedValueOnce(response(decision, { status: 201 }))
      .mockResolvedValueOnce(response({ ...run, status: "cancelled" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(startRun(run.task_id, "run-idempotency")).resolves.toEqual({
      run,
      replayed: false,
    });
    await expect(createSnapshot(run.id)).resolves.toEqual(snapshot);
    await expect(
      createPlan(run.id, {
        delivery_package: "frontend_quality_remediation",
      }),
    ).resolves.toEqual(plan);
    await expect(
      revisePlan(run.id, 1, {
        objective_summary: "A bounded revision.",
      }),
    ).resolves.toEqual(plan);
    await expect(submitPlan(run.id, 1)).resolves.toMatchObject({
      status: "awaiting_approval",
    });
    await expect(
      decidePlan(run.id, 1, { decision: "approve" }),
    ).resolves.toEqual(decision);
    await expect(cancelRun(run.id, "Stopped locally.")).resolves.toMatchObject({
      status: "cancelled",
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining(`/api/v1/tasks/${run.task_id}/runs`),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Idempotency-Key": "run-idempotency",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      expect.stringContaining("/decisions"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ decision: "approve" }),
      }),
    );
  });
});
