import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createTask, getHealth, listTasks } from "@/lib/api";
import { taskFixture } from "@/test/fixtures";

import { Dashboard } from "./dashboard";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    createTask: vi.fn(),
    getHealth: vi.fn(),
    listTasks: vi.fn(),
  };
});

const mockedCreateTask = vi.mocked(createTask);
const mockedGetHealth = vi.mocked(getHealth);
const mockedListTasks = vi.mocked(listTasks);

beforeEach(() => {
  vi.clearAllMocks();
  mockedGetHealth.mockResolvedValue(true);
});

describe("Dashboard", () => {
  it("renders the Foundation console and its loading state", () => {
    mockedListTasks.mockReturnValue(new Promise(() => undefined));

    render(<Dashboard />);

    expect(
      screen.getByRole("heading", {
        name: "受治理的前端交付任务控制台",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "创建任务" }),
    ).toBeInTheDocument();
    expect(screen.getByText("正在加载任务…")).toBeInTheDocument();
  });

  it("shows the empty state after loading", async () => {
    mockedListTasks.mockResolvedValue([]);

    render(<Dashboard />);

    expect(await screen.findByText("还没有任务")).toBeInTheDocument();
    expect(screen.getAllByText("正常")).toHaveLength(2);
  });

  it("shows an API error and retries the task list", async () => {
    mockedListTasks
      .mockRejectedValueOnce(
        new ApiError("Database unavailable", {
          status: 503,
          code: "not_ready",
          requestId: "req-test",
        }),
      )
      .mockResolvedValueOnce([]);

    const user = userEvent.setup();
    render(<Dashboard />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Database unavailable");
    expect(alert).toHaveTextContent("req-test");

    await user.click(within(alert).getByRole("button", { name: "重试" }));

    expect(await screen.findByText("还没有任务")).toBeInTheDocument();
    expect(mockedListTasks).toHaveBeenCalledTimes(2);
  });

  it("validates required fields before making a request", async () => {
    mockedListTasks.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<Dashboard />);

    await user.click(screen.getByRole("button", { name: "创建任务" }));

    expect(screen.getByText("请输入任务标题。")).toBeInTheDocument();
    expect(screen.getByText("请输入任务目标。")).toBeInTheDocument();
    expect(screen.getByText("请输入仓库显示名称。")).toBeInTheDocument();
    expect(screen.getByText("请输入仓库位置。")).toBeInTheDocument();
    expect(mockedCreateTask).not.toHaveBeenCalled();
  });

  it("rejects NUL characters before making a request", async () => {
    mockedListTasks.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<Dashboard />);

    await user.type(screen.getByLabelText("任务标题"), "Safe title");
    await user.type(screen.getByLabelText("任务目标"), "Safe objective");
    await user.type(screen.getByLabelText("显示名称"), "Safe repository");
    fireEvent.change(screen.getByLabelText("仓库位置"), {
      target: { value: "/workspace/unsafe\u0000locator" },
    });
    await user.click(screen.getByRole("button", { name: "创建任务" }));

    expect(screen.getByText("字段不能包含 NUL 字符。")).toBeInTheDocument();
    expect(mockedCreateTask).not.toHaveBeenCalled();
  });

  it("creates a task with an idempotency key and displays the result", async () => {
    const task = taskFixture({ title: "Keyboard-ready task" });
    mockedListTasks.mockResolvedValue([]);
    mockedCreateTask.mockResolvedValue({ task, replayed: false });
    const user = userEvent.setup();
    render(<Dashboard />);

    await screen.findByText("还没有任务");
    await user.type(screen.getByLabelText("任务标题"), task.title);
    await user.type(screen.getByLabelText("任务目标"), task.objective);
    await user.type(
      screen.getByLabelText("显示名称"),
      task.repository_display_name,
    );
    await user.type(screen.getByLabelText("仓库位置"), task.repository_locator);
    await user.click(screen.getByRole("button", { name: "创建任务" }));

    await waitFor(() => expect(mockedCreateTask).toHaveBeenCalledTimes(1));
    expect(mockedCreateTask.mock.calls[0]?.[0]).toEqual({
      title: task.title,
      objective: task.objective,
      repository_kind: "local_path",
      repository_display_name: task.repository_display_name,
      repository_locator: task.repository_locator,
    });
    expect(mockedCreateTask.mock.calls[0]?.[1]).toEqual(expect.any(String));
    expect(await screen.findByText("任务创建成功")).toBeInTheDocument();
    expect(screen.getAllByText(task.title).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /查看详情/ })).toHaveAttribute(
      "href",
      `/tasks/${task.id}`,
    );
  });
});
