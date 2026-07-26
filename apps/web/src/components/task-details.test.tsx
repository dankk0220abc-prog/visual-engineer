import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getTask, listRuns, startRun } from "@/lib/api";
import { runFixture, taskFixture } from "@/test/fixtures";

import { TaskDetails } from "./task-details";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getTask: vi.fn(),
    listRuns: vi.fn(),
    startRun: vi.fn(),
  };
});

const mockedGetTask = vi.mocked(getTask);
const mockedListRuns = vi.mocked(listRuns);
const mockedStartRun = vi.mocked(startRun);

beforeEach(() => {
  vi.clearAllMocks();
  mockedListRuns.mockResolvedValue([]);
});

describe("TaskDetails", () => {
  it("renders task data returned by the API", async () => {
    const task = taskFixture();
    mockedGetTask.mockResolvedValue(task);

    render(<TaskDetails taskId={task.id} />);

    expect(screen.getByText("正在加载任务详情…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: task.title }),
    ).toBeInTheDocument();
    expect(screen.getByText(task.objective)).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Start read-only investigation" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/不会读取未提交文件内容/)).toBeInTheDocument();
  });

  it("provides a retry after an error", async () => {
    const task = taskFixture();
    mockedGetTask
      .mockRejectedValueOnce(
        new ApiError("Task temporarily unavailable", {
          status: 503,
        }),
      )
      .mockResolvedValueOnce(task);
    const user = userEvent.setup();

    render(<TaskDetails taskId={task.id} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Task temporarily unavailable");
    await user.click(within(alert).getByRole("button", { name: "重试" }));

    expect(
      await screen.findByRole("heading", { name: task.title }),
    ).toBeInTheDocument();
    expect(mockedGetTask).toHaveBeenCalledTimes(2);
  });

  it("starts a Level 0 Run and adds it to history", async () => {
    const task = taskFixture();
    const run = runFixture({ task_id: task.id });
    mockedGetTask.mockResolvedValue(task);
    mockedStartRun.mockResolvedValue({ run, replayed: false });
    const user = userEvent.setup();

    render(<TaskDetails taskId={task.id} />);

    await user.click(
      await screen.findByRole("button", {
        name: "Start read-only investigation",
      }),
    );

    expect(
      await screen.findByText("Read-only Run 已创建。"),
    ).toBeInTheDocument();
    expect(screen.getByText(run.id)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开 Run" })).toHaveAttribute(
      "href",
      `/runs/${run.id}`,
    );
    expect(mockedStartRun).toHaveBeenCalledWith(task.id, expect.any(String));
  });
});
