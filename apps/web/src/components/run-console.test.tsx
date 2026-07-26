import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createPlan,
  createSnapshot,
  decidePlan,
  getRun,
  getSnapshot,
  listAuditEvents,
  listPlans,
  revisePlan,
  submitPlan,
} from "@/lib/api";
import {
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
    createPlan: vi.fn(),
    createSnapshot: vi.fn(),
    decidePlan: vi.fn(),
    getRun: vi.fn(),
    getSnapshot: vi.fn(),
    listAuditEvents: vi.fn(),
    listPlans: vi.fn(),
    revisePlan: vi.fn(),
    submitPlan: vi.fn(),
  };
});

const mockedCreatePlan = vi.mocked(createPlan);
const mockedCreateSnapshot = vi.mocked(createSnapshot);
const mockedDecidePlan = vi.mocked(decidePlan);
const mockedGetRun = vi.mocked(getRun);
const mockedGetSnapshot = vi.mocked(getSnapshot);
const mockedListAuditEvents = vi.mocked(listAuditEvents);
const mockedListPlans = vi.mocked(listPlans);
const mockedRevisePlan = vi.mocked(revisePlan);
const mockedSubmitPlan = vi.mocked(submitPlan);

beforeEach(() => {
  vi.clearAllMocks();
  mockedGetRun.mockResolvedValue(runFixture({ status: "plan_ready" }));
  mockedGetSnapshot.mockResolvedValue(snapshotFixture());
  mockedListPlans.mockResolvedValue([planFixture()]);
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
});
