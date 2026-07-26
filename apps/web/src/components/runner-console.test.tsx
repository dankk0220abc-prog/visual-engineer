import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createRunnerJob,
  listRunnerJobs,
  listRunners,
  revokeRunner,
} from "@/lib/api";
import { runnerFixture, runnerJobFixture } from "@/test/fixtures";

import { RunnerConsole } from "./runner-console";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    createRunnerJob: vi.fn(),
    listRunnerJobs: vi.fn(),
    listRunners: vi.fn(),
    revokeRunner: vi.fn(),
  };
});

const mockedCreateRunnerJob = vi.mocked(createRunnerJob);
const mockedListRunnerJobs = vi.mocked(listRunnerJobs);
const mockedListRunners = vi.mocked(listRunners);
const mockedRevokeRunner = vi.mocked(revokeRunner);

beforeEach(() => {
  vi.clearAllMocks();
  mockedListRunners.mockResolvedValue([runnerFixture()]);
  mockedListRunnerJobs.mockResolvedValue([runnerJobFixture()]);
  mockedCreateRunnerJob.mockResolvedValue(runnerJobFixture());
  mockedRevokeRunner.mockResolvedValue(
    runnerFixture({
      status: "revoked",
      revoked_at: "2026-07-26T16:02:00Z",
    }),
  );
});

describe("RunnerConsole", () => {
  it("shows online, offline, and revoked registry states without credentials", async () => {
    mockedListRunners.mockResolvedValue([
      runnerFixture(),
      runnerFixture({
        id: "89f54866-f45f-43c4-81e1-7a77fbc67466",
        display_name: "Offline Runner",
        status: "offline",
      }),
      runnerFixture({
        id: "0114c0e3-3a30-4d55-ac69-6b30930519ee",
        display_name: "Revoked Runner",
        status: "revoked",
        revoked_at: "2026-07-26T16:02:00Z",
      }),
    ]);

    render(<RunnerConsole />);

    expect(screen.getByText("正在加载 Runner Registry…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "已注册 Runner" }),
    ).toBeInTheDocument();
    expect(screen.getByText("online")).toBeInTheDocument();
    expect(screen.getByText("offline")).toBeInTheDocument();
    expect(screen.getByText("revoked")).toBeInTheDocument();
    expect(
      screen.queryByText(/bearer|bootstrap token/i),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "已撤销" })).toBeDisabled();
  });

  it("renders registry and job empty states and disables dispatch offline", async () => {
    mockedListRunners.mockResolvedValue([runnerFixture({ status: "offline" })]);
    mockedListRunnerJobs.mockResolvedValue([]);

    render(<RunnerConsole />);

    expect(await screen.findByText("尚无 Runner Job")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "创建并查看 Job" }),
    ).toBeDisabled();
    expect(
      screen.getByText("当前没有 Online Runner，Dispatch 已禁用。"),
    ).toBeInTheDocument();
  });

  it("shows an API error with request ID and retries", async () => {
    mockedListRunners
      .mockRejectedValueOnce(
        new ApiError("Runner registry unavailable", {
          status: 503,
          code: "not_ready",
          requestId: "runner-request",
        }),
      )
      .mockResolvedValueOnce([]);
    mockedListRunnerJobs.mockResolvedValue([]);
    const user = userEvent.setup();

    render(<RunnerConsole />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Runner registry unavailable");
    expect(alert).toHaveTextContent("runner-request");
    await user.click(within(alert).getByRole("button", { name: "重试" }));

    expect(await screen.findByText("尚无已注册 Runner")).toBeInTheDocument();
  });

  it("previews the immutable envelope and dispatches a diagnostic", async () => {
    const job = runnerJobFixture();
    mockedCreateRunnerJob.mockResolvedValue(job);
    const user = userEvent.setup();

    render(<RunnerConsole />);
    await screen.findByRole("heading", { name: "创建受限 Job" });

    const preview = screen.getByLabelText("Permission Envelope 预览");
    expect(preview).toHaveTextContent("system_diagnostic_v1");
    expect(preview).toHaveTextContent("none");
    expect(preview).toHaveTextContent("false");
    expect(preview).toHaveTextContent("control-plane only");
    expect(preview).toHaveTextContent("not accessed");

    await user.click(screen.getByRole("button", { name: "创建并查看 Job" }));

    await waitFor(() =>
      expect(mockedCreateRunnerJob).toHaveBeenCalledWith({
        kind: "system_diagnostic_v1",
      }),
    );
    expect(push).toHaveBeenCalledWith(`/runners/jobs/${job.id}`);
  });

  it("dispatches only the bounded controlled-wait parameters", async () => {
    const job = runnerJobFixture({
      kind: "controlled_wait_v1",
      parameters: { duration_ms: 4200 },
    });
    mockedCreateRunnerJob.mockResolvedValue(job);
    const user = userEvent.setup();

    render(<RunnerConsole />);
    await user.click(
      await screen.findByRole("radio", { name: /Controlled Wait/ }),
    );
    const duration = screen.getByLabelText("Duration（毫秒）");
    await user.clear(duration);
    await user.type(duration, "4200");
    await user.click(screen.getByRole("button", { name: "创建并查看 Job" }));

    await waitFor(() =>
      expect(mockedCreateRunnerJob).toHaveBeenCalledWith({
        kind: "controlled_wait_v1",
        duration_ms: 4200,
      }),
    );
    expect(push).toHaveBeenCalledWith(`/runners/jobs/${job.id}`);
  });

  it("revokes a runner and renders the terminal registry state", async () => {
    const user = userEvent.setup();

    render(<RunnerConsole />);
    await user.click(
      await screen.findByRole("button", { name: "撤销 Runner" }),
    );

    await waitFor(() =>
      expect(mockedRevokeRunner).toHaveBeenCalledWith(runnerFixture().id),
    );
    expect(
      await screen.findByRole("button", { name: "已撤销" }),
    ).toBeDisabled();
  });
});
