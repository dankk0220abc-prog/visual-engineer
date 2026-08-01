import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  cancelAIPlanRequest,
  createAIPlanRequest,
  createPlan,
  createSnapshot,
  decideAIPlanRequest,
  decidePlan,
  getRun,
  getSnapshot,
  listAuditEvents,
  listAIPlanRequests,
  listPlans,
  refreshAIPlanFreshness,
  revisePlan,
  submitPlan,
} from "@/lib/api";
import {
  aiPlanRequestFixture,
  auditFixture,
  planFixture,
  runFixture,
  snapshotFixture,
} from "@/test/fixtures";

import { RunConsole } from "./run-console";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    cancelAIPlanRequest: vi.fn(),
    createAIPlanRequest: vi.fn(),
    createPlan: vi.fn(),
    createSnapshot: vi.fn(),
    decideAIPlanRequest: vi.fn(),
    decidePlan: vi.fn(),
    getRun: vi.fn(),
    getSnapshot: vi.fn(),
    listAuditEvents: vi.fn(),
    listAIPlanRequests: vi.fn(),
    listPlans: vi.fn(),
    refreshAIPlanFreshness: vi.fn(),
    revisePlan: vi.fn(),
    submitPlan: vi.fn(),
  };
});

const mockedCreatePlan = vi.mocked(createPlan);
const mockedCreateAIPlanRequest = vi.mocked(createAIPlanRequest);
const mockedCancelAIPlanRequest = vi.mocked(cancelAIPlanRequest);
const mockedCreateSnapshot = vi.mocked(createSnapshot);
const mockedDecidePlan = vi.mocked(decidePlan);
const mockedDecideAIPlanRequest = vi.mocked(decideAIPlanRequest);
const mockedGetRun = vi.mocked(getRun);
const mockedGetSnapshot = vi.mocked(getSnapshot);
const mockedListAuditEvents = vi.mocked(listAuditEvents);
const mockedListAIPlanRequests = vi.mocked(listAIPlanRequests);
const mockedListPlans = vi.mocked(listPlans);
const mockedRevisePlan = vi.mocked(revisePlan);
const mockedSubmitPlan = vi.mocked(submitPlan);
const mockedRefreshAIPlanFreshness = vi.mocked(refreshAIPlanFreshness);

beforeEach(() => {
  vi.clearAllMocks();
  mockedGetRun.mockResolvedValue(runFixture({ status: "plan_ready" }));
  mockedGetSnapshot.mockResolvedValue(snapshotFixture());
  mockedListPlans.mockResolvedValue([planFixture()]);
  mockedListAIPlanRequests.mockResolvedValue([]);
  mockedListAuditEvents.mockResolvedValue([
    auditFixture(),
    auditFixture({
      id: "6f1cffdd-eb0f-4366-b222-b2a83ff7eb25",
      event_type: "snapshot_completed",
      actor_type: "system",
    }),
  ]);
  mockedCreateSnapshot.mockResolvedValue(snapshotFixture());
  mockedCreatePlan.mockResolvedValue(planFixture());
  mockedCreateAIPlanRequest.mockResolvedValue(aiPlanRequestFixture());
  mockedCancelAIPlanRequest.mockResolvedValue(
    aiPlanRequestFixture({ status: "cancelled" }),
  );
  mockedRefreshAIPlanFreshness.mockResolvedValue(aiPlanRequestFixture());
  mockedDecideAIPlanRequest.mockResolvedValue({
    id: "68ce4fc4-7102-4c19-97a9-c65804297ddf",
    ai_plan_request_id: aiPlanRequestFixture().id,
    run_id: runFixture().id,
    decision: "approve",
    comment: null,
    actor_type: "local_user",
    request_id: "ai-decision-request",
    handoff_plan_id: planFixture().id,
    created_at: "2026-08-01T10:01:00Z",
  });
  mockedRevisePlan.mockResolvedValue(planFixture({ version: 2 }));
  mockedSubmitPlan.mockResolvedValue(
    planFixture({ status: "awaiting_approval" }),
  );
  mockedDecidePlan.mockResolvedValue({
    id: "a7604849-fce9-44ad-88ea-07a8d3e2e753",
    run_id: runFixture().id,
    plan_id: planFixture().id,
    decision: "approve",
    comment: null,
    actor_type: "local_user",
    request_id: "decision-request",
    created_at: "2026-07-26T04:03:00Z",
  });
});

describe("RunConsole", () => {
  it("shows loading, Run state, dirty warning, safety, deterministic Plan, and audit", async () => {
    render(<RunConsole runId={runFixture().id} />);

    expect(
      screen.getByText("Loading Run and Repository Intelligence…"),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", {
        name: "Governed Repository Investigation",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("plan_ready")).toBeInTheDocument();
    expect(screen.getByText("Dirty working tree detected")).toBeInTheDocument();
    expect(screen.getByText(/environment_file · \.env/)).toBeInTheDocument();
    expect(
      screen.getByText(/prompt_injection_secret_access_request/),
    ).toBeInTheDocument();
    expect(screen.getByText(/deterministic plan · v1/i)).toBeInTheDocument();
    expect(
      screen.getByText("Plan approval does not execute code."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Execution is not available in Phase 2."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Audit Timeline" }),
    ).toBeInTheDocument();
    expect(screen.getByText("snapshot_completed")).toBeInTheDocument();
  });

  it("renders the Snapshot empty state and creates a committed-HEAD Snapshot", async () => {
    const createdRun = runFixture({ status: "created" });
    const readyRun = runFixture({ status: "snapshot_ready", version: 3 });
    mockedGetRun.mockResolvedValueOnce(createdRun).mockResolvedValue(readyRun);
    mockedGetSnapshot
      .mockRejectedValueOnce(
        new ApiError("Snapshot was not found", {
          status: 404,
          code: "snapshot_not_found",
        }),
      )
      .mockResolvedValue(snapshotFixture());
    mockedListPlans.mockResolvedValue([]);
    const user = userEvent.setup();

    render(<RunConsole runId={createdRun.id} />);

    expect(
      await screen.findByRole("heading", {
        name: "Repository Intelligence is empty",
      }),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: "Create committed-HEAD Snapshot",
      }),
    );

    await waitFor(() =>
      expect(mockedCreateSnapshot).toHaveBeenCalledWith(createdRun.id),
    );
    expect(
      await screen.findByRole("heading", { name: "Repository Intelligence" }),
    ).toBeInTheDocument();
  });

  it("renders a Snapshot load error and retries", async () => {
    mockedGetSnapshot
      .mockRejectedValueOnce(
        new ApiError("Snapshot temporarily unavailable", {
          status: 503,
          code: "snapshot_unavailable",
        }),
      )
      .mockResolvedValue(snapshotFixture());
    const user = userEvent.setup();

    render(<RunConsole runId={runFixture().id} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Snapshot temporarily unavailable");
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByRole("heading", { name: "Repository Intelligence" }),
    ).toBeInTheDocument();
  });

  it("creates a bounded revision and submits the latest draft", async () => {
    const run = runFixture({ status: "plan_ready" });
    const plan = planFixture();
    mockedGetRun.mockResolvedValue(run);
    mockedListPlans.mockResolvedValue([plan]);
    const user = userEvent.setup();

    render(<RunConsole runId={run.id} />);

    const objective = await screen.findByLabelText("Objective summary");
    await user.clear(objective);
    await user.type(objective, "Revised governed objective.");
    const scope = screen.getByLabelText("Scope, one item per line");
    await user.clear(scope);
    await user.type(scope, "First approved path\nSecond approved path");
    await user.click(screen.getByRole("button", { name: "Create revision" }));

    await waitFor(() =>
      expect(mockedRevisePlan).toHaveBeenCalledWith(run.id, 1, {
        objective_summary: "Revised governed objective.",
        proposed_change_scope: ["First approved path", "Second approved path"],
      }),
    );

    await user.click(
      await screen.findByRole("button", { name: "Submit latest Plan" }),
    );
    await waitFor(() =>
      expect(mockedSubmitPlan).toHaveBeenCalledWith(run.id, 1),
    );
  });

  it("requires a rejection reason and exposes approve and reject actions", async () => {
    const run = runFixture({ status: "awaiting_plan_approval" });
    const plan = planFixture({ status: "awaiting_approval" });
    mockedGetRun.mockResolvedValue(run);
    mockedListPlans.mockResolvedValue([plan]);
    const user = userEvent.setup();

    render(<RunConsole runId={run.id} />);

    await user.click(
      await screen.findByRole("button", { name: "Reject Plan" }),
    );
    expect(screen.getByText("Reject 必须填写非空理由。")).toBeInTheDocument();
    expect(mockedDecidePlan).not.toHaveBeenCalled();

    await user.type(
      screen.getByLabelText("Rejection reason"),
      "The scope requires revision.",
    );
    await user.click(screen.getByRole("button", { name: "Reject Plan" }));
    await waitFor(() =>
      expect(mockedDecidePlan).toHaveBeenCalledWith(run.id, 1, {
        decision: "reject",
        comment: "The scope requires revision.",
      }),
    );

    await user.click(
      await screen.findByRole("button", { name: "Approve Plan" }),
    );
    await waitFor(() =>
      expect(mockedDecidePlan).toHaveBeenCalledWith(run.id, 1, {
        decision: "approve",
        comment: undefined,
      }),
    );
  });

  it("shows a stable conflict message without hiding the current Plan", async () => {
    const run = runFixture({ status: "plan_ready" });
    mockedGetRun.mockResolvedValue(run);
    mockedSubmitPlan.mockRejectedValue(
      new ApiError("Only the latest Plan can be submitted", {
        status: 409,
        code: "stale_plan_version",
        requestId: "conflict-request",
      }),
    );
    const user = userEvent.setup();

    render(<RunConsole runId={run.id} />);
    await user.click(
      await screen.findByRole("button", { name: "Submit latest Plan" }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("状态冲突");
    expect(alert).toHaveTextContent("conflict-request");
    expect(
      screen.getByText("Plan approval does not execute code."),
    ).toBeInTheDocument();
  });

  it("generates, inspects, and approves a governed AI Plan handoff", async () => {
    const snapshotReady = runFixture({ status: "snapshot_ready" });
    const planReady = runFixture({ status: "plan_ready", version: 4 });
    mockedGetRun
      .mockResolvedValueOnce(snapshotReady)
      .mockResolvedValue(planReady);
    mockedListPlans.mockResolvedValue([]);
    mockedListAIPlanRequests
      .mockResolvedValueOnce([])
      .mockResolvedValue([aiPlanRequestFixture()]);
    const user = userEvent.setup();

    render(<RunConsole runId={snapshotReady.id} />);

    await user.click(
      await screen.findByRole("button", { name: "Generate governed AI Plan" }),
    );
    await waitFor(() =>
      expect(mockedCreateAIPlanRequest).toHaveBeenCalledWith(
        snapshotReady.id,
        { delivery_package: "frontend_quality_remediation" },
        expect.any(String),
      ),
    );
    expect(
      await screen.findByRole("heading", { name: "Structured AI Plan" }),
    ).toBeInTheDocument();
    expect(screen.getByText("System-owned Eval evidence")).toBeInTheDocument();
    expect(screen.getByText("schema_validity")).toBeInTheDocument();
    expect(screen.getByText("Provider Trace")).toBeInTheDocument();
    expect(
      screen.getByText(
        /AI Plan approval does not execute code or issue authority/,
      ),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Revalidate freshness" }),
    );
    await waitFor(() =>
      expect(mockedRefreshAIPlanFreshness).toHaveBeenCalledWith(
        aiPlanRequestFixture().id,
      ),
    );

    await user.click(screen.getByRole("button", { name: "Reject AI Plan" }));
    expect(screen.getByText("Reject 必须填写非空理由。")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Rejection reason"),
      "The typed scope needs revision.",
    );
    await user.click(screen.getByRole("button", { name: "Reject AI Plan" }));
    await waitFor(() =>
      expect(mockedDecideAIPlanRequest).toHaveBeenCalledWith(
        aiPlanRequestFixture().id,
        {
          decision: "reject",
          comment: "The typed scope needs revision.",
        },
      ),
    );

    await user.click(screen.getByRole("button", { name: "Cancel AI Plan" }));
    await waitFor(() =>
      expect(mockedCancelAIPlanRequest).toHaveBeenCalledWith(
        aiPlanRequestFixture().id,
      ),
    );

    await user.click(
      screen.getByRole("button", { name: "Approve AI Plan handoff" }),
    );
    await waitFor(() =>
      expect(mockedDecideAIPlanRequest).toHaveBeenCalledWith(
        aiPlanRequestFixture().id,
        { decision: "approve", comment: undefined },
      ),
    );
  });

  it.each(["stale", "failed", "cancelled"] as const)(
    "renders the governed AI %s terminal state and blocks decisions",
    async (status) => {
      mockedGetRun.mockResolvedValue(
        runFixture({ status: status === "cancelled" ? "cancelled" : "failed" }),
      );
      mockedListPlans.mockResolvedValue([]);
      mockedListAIPlanRequests.mockResolvedValue([
        aiPlanRequestFixture({
          status,
          error_category: status === "stale" ? "freshness" : "provider",
          error_code: `ai_plan_${status}`,
          error_message: `Governed AI Plan is ${status}.`,
        }),
      ]);

      render(<RunConsole runId={runFixture().id} />);

      expect(
        await screen.findByRole("heading", { name: "Structured AI Plan" }),
      ).toBeInTheDocument();
      expect(
        screen.getByText(`Governed AI Plan is ${status}.`),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Approve AI Plan handoff" }),
      ).not.toBeInTheDocument();
      expect(mockedDecideAIPlanRequest).not.toHaveBeenCalled();
    },
  );

  it("keeps an Eval-failed Plan inspectable and explicitly blocks approval", async () => {
    const fixture = aiPlanRequestFixture();
    mockedGetRun.mockResolvedValue(runFixture({ status: "failed" }));
    mockedListPlans.mockResolvedValue([]);
    mockedListAIPlanRequests.mockResolvedValue([
      aiPlanRequestFixture({
        status: "failed",
        error_category: "evaluation",
        error_code: "ai_plan_eval_failed",
        error_message: "One or more mandatory AI Plan Evals failed",
        eval_results: [
          {
            ...fixture.eval_results[0],
            eval_id: "generation_binding_integrity",
            passed: false,
            summary:
              "The response does not match the system-owned generation binding.",
          },
        ],
      }),
    ]);

    render(<RunConsole runId={runFixture().id} />);

    expect(
      await screen.findByText("System-owned Eval failed · approval blocked"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Improve the bounded fixture frontend surface."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("generation_binding_integrity"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Approve AI Plan handoff" }),
    ).not.toBeInTheDocument();
    expect(mockedDecideAIPlanRequest).not.toHaveBeenCalled();
  });

  it("shows generating Provider metadata and exposes cancellation", async () => {
    mockedGetRun.mockResolvedValue(runFixture({ status: "snapshot_ready" }));
    mockedListPlans.mockResolvedValue([]);
    mockedListAIPlanRequests.mockResolvedValue([
      aiPlanRequestFixture({
        status: "generating",
        plan: null,
        deterministic_digest: null,
        traces: [],
        eval_results: [],
      }),
    ]);
    const user = userEvent.setup();

    render(<RunConsole runId={runFixture().id} />);

    expect(
      await screen.findByRole("heading", {
        name: "Provider capability metadata",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("synthetic_not_billable")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Cancel AI Plan generation" }),
    );
    await waitFor(() =>
      expect(mockedCancelAIPlanRequest).toHaveBeenCalledWith(
        aiPlanRequestFixture().id,
      ),
    );
  });
});
