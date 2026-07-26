import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  cancelRunnerJob,
  getRunnerJob,
  listRunnerJobEvents,
} from "@/lib/api";
import { runnerJobEventFixture, runnerJobFixture } from "@/test/fixtures";

import { RunnerJobConsole } from "./runner-job-console";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    cancelRunnerJob: vi.fn(),
    getRunnerJob: vi.fn(),
    listRunnerJobEvents: vi.fn(),
  };
});

const mockedCancelRunnerJob = vi.mocked(cancelRunnerJob);
const mockedGetRunnerJob = vi.mocked(getRunnerJob);
const mockedListRunnerJobEvents = vi.mocked(listRunnerJobEvents);

const attempt = {
  id: "40def94c-5c3b-46f7-9950-7e23b7d13b58",
  job_id: runnerJobFixture().id,
  runner_id: "271ad4e1-4bc2-41db-a954-973b14dcf008",
  attempt_number: 1,
  lease_id_hint: "a91d…30c4",
  state: "running",
  leased_until: "2026-07-26T16:01:10Z",
  last_heartbeat_at: "2026-07-26T16:01:04Z",
  started_at: "2026-07-26T16:01:01Z",
  completed_at: null,
  error_code: null,
  error_message: null,
  created_at: "2026-07-26T16:01:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  const job = runnerJobFixture({
    state: "running",
    active_attempt_id: attempt.id,
    attempt_count: 1,
    active_attempt: attempt,
    attempts: [attempt],
  });
  mockedGetRunnerJob.mockResolvedValue(job);
  mockedListRunnerJobEvents.mockResolvedValue([
    runnerJobEventFixture(),
    runnerJobEventFixture({
      id: "00d192e8-2542-444a-9081-19188fc73aef",
      runner_id: attempt.runner_id,
      attempt_id: attempt.id,
      event_type: "job_started",
      sequence: 2,
      metadata: { attempt_number: 1 },
    }),
  ]);
  mockedCancelRunnerJob.mockResolvedValue(
    runnerJobFixture({
      state: "cancel_requested",
      active_attempt_id: attempt.id,
      attempt_count: 1,
      active_attempt: attempt,
      attempts: [attempt],
    }),
  );
});

describe("RunnerJobConsole", () => {
  it("renders running state, fenced attempt, immutable envelope, and timeline", async () => {
    render(<RunnerJobConsole jobId={runnerJobFixture().id} />);

    expect(screen.getByText("正在加载 Runner Job…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Permission Envelope" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("running")).toHaveLength(2);
    expect(screen.getByText("Attempt 1")).toBeInTheDocument();
    expect(screen.getByText("a91d…30c4")).toBeInTheDocument();
    expect(screen.getByText("none")).toBeInTheDocument();
    expect(screen.getByText("control_plane_only")).toBeInTheDocument();
    expect(screen.getByText("d".repeat(64))).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Timeline" }),
    ).toBeInTheDocument();
    expect(screen.getByText("job_started")).toBeInTheDocument();
  });

  it("requests cancellation and distinguishes requested from cancelled", async () => {
    const requested = runnerJobFixture({
      state: "cancel_requested",
      active_attempt_id: attempt.id,
      attempt_count: 1,
      active_attempt: attempt,
      attempts: [attempt],
    });
    mockedCancelRunnerJob.mockResolvedValue(requested);
    mockedGetRunnerJob
      .mockResolvedValueOnce(
        runnerJobFixture({
          state: "running",
          active_attempt_id: attempt.id,
          attempt_count: 1,
          active_attempt: attempt,
          attempts: [attempt],
        }),
      )
      .mockResolvedValue(requested);
    const user = userEvent.setup();

    render(<RunnerJobConsole jobId={runnerJobFixture().id} />);
    await user.click(await screen.findByRole("button", { name: "Cancel Job" }));

    await waitFor(() =>
      expect(mockedCancelRunnerJob).toHaveBeenCalledWith(runnerJobFixture().id),
    );
    expect(
      await screen.findByText(/已请求取消，正在等待 Runner 确认/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消已请求" })).toBeDisabled();
    expect(screen.queryByText("cancelled")).not.toBeInTheDocument();
  });

  it("shows lease expiry, requeue evidence, retry, and typed result", async () => {
    const expired = {
      ...attempt,
      state: "lease_expired",
      completed_at: "2026-07-26T16:01:12Z",
      error_code: "lease_expired",
      error_message: "Lease expired before completion.",
    };
    const succeeded = {
      ...attempt,
      id: "98bb89c7-205f-449f-813b-388b698d638c",
      attempt_number: 2,
      lease_id_hint: "b82e…41d5",
      state: "succeeded",
      completed_at: "2026-07-26T16:01:20Z",
    };
    mockedGetRunnerJob.mockResolvedValue(
      runnerJobFixture({
        state: "succeeded",
        attempt_count: 2,
        active_attempt_id: null,
        active_attempt: null,
        attempts: [expired, succeeded],
        completed_at: "2026-07-26T16:01:20Z",
        result: {
          kind: "system_diagnostic_v1",
          runner_software_version: "0.3.0",
          protocol_version: 1,
          python_version: "3.13.5",
          os_family: "linux",
          architecture: "aarch64",
          capability_list: ["system_diagnostic_v1", "controlled_wait_v1"],
          started_at: "2026-07-26T16:01:13Z",
          completed_at: "2026-07-26T16:01:20Z",
          duration_ms: 7000,
        },
      }),
    );

    render(<RunnerJobConsole jobId={runnerJobFixture().id} />);

    expect(await screen.findByText("Attempt 2")).toBeInTheDocument();
    expect(screen.getByText("lease_expired")).toBeInTheDocument();
    expect(screen.getByText("Attempt 1").closest("li")).toHaveTextContent(
      "Job 已恢复到后续状态。",
    );
    expect(screen.getAllByText("succeeded")).toHaveLength(2);
    expect(screen.getByText("runner_software_version")).toBeInTheDocument();
    expect(screen.getByText("3.13.5")).toBeInTheDocument();
  });

  it("renders a completed cancellation without a success result", async () => {
    mockedGetRunnerJob.mockResolvedValue(
      runnerJobFixture({
        state: "cancelled",
        attempt_count: 1,
        active_attempt_id: null,
        active_attempt: null,
        attempts: [{ ...attempt, state: "cancelled" }],
        completed_at: "2026-07-26T16:01:08Z",
      }),
    );

    render(<RunnerJobConsole jobId={runnerJobFixture().id} />);

    expect(await screen.findAllByText("cancelled")).not.toHaveLength(0);
    expect(screen.getByText("此终态没有成功结果。")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancel Job" }),
    ).not.toBeInTheDocument();
  });

  it("shows a load conflict/error and retries on a narrow viewport", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });
    mockedGetRunnerJob
      .mockRejectedValueOnce(
        new ApiError("Runner Job temporarily unavailable", {
          status: 409,
          code: "stale_lease",
          requestId: "job-request",
        }),
      )
      .mockResolvedValueOnce(runnerJobFixture());
    mockedListRunnerJobEvents.mockResolvedValue([]);
    const user = userEvent.setup();

    render(<RunnerJobConsole jobId={runnerJobFixture().id} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Runner Job temporarily unavailable");
    expect(alert).toHaveTextContent("job-request");
    await user.click(within(alert).getByRole("button", { name: "重试" }));

    expect(
      await screen.findByRole("heading", { name: "Permission Envelope" }),
    ).toBeInTheDocument();
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth,
    );
  });
});
