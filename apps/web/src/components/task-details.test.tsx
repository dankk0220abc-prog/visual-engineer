import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getTask } from "@/lib/api";
import { taskFixture } from "@/test/fixtures";

import { TaskDetails } from "./task-details";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getTask: vi.fn(),
  };
});

const mockedGetTask = vi.mocked(getTask);

beforeEach(() => {
  vi.clearAllMocks();
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
});
