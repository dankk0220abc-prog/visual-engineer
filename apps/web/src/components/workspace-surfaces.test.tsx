import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createExecutionGrant,
  createWorkspace,
  decideExecutionGrant,
  getWorkspaceDiff,
  getRunnerJob,
  getWorkspace,
  getWorkspaceStatus,
  listEligibleExecutionContexts,
  listExecutionGrants,
  listRepositories,
  listWorkspaceCheckpoints,
  listWorkspaceDirectory,
  listWorkspaceEvents,
  listWorkspaces,
  readWorkspaceText,
  rollbackWorkspace,
  writeWorkspaceText,
  type ExecutionGrant,
  type RepositoryHandle,
  type Workspace,
} from "@/lib/api";
import { runnerJobFixture } from "@/test/fixtures";

import { ExecutionGrantConsole } from "./execution-grant-console";
import { RepositoryConsole } from "./repository-console";
import { WorkspaceConsole } from "./workspace-console";
import { WorkspaceDetailConsole } from "./workspace-detail-console";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    createExecutionGrant: vi.fn(),
    createWorkspace: vi.fn(),
    decideExecutionGrant: vi.fn(),
    discardWorkspace: vi.fn(),
    getRunnerJob: vi.fn(),
    getWorkspace: vi.fn(),
    getWorkspaceDiff: vi.fn(),
    getWorkspaceStatus: vi.fn(),
    listEligibleExecutionContexts: vi.fn(),
    listExecutionGrants: vi.fn(),
    listRepositories: vi.fn(),
    listWorkspaceCheckpoints: vi.fn(),
    listWorkspaceDirectory: vi.fn(),
    listWorkspaceEvents: vi.fn(),
    listWorkspaces: vi.fn(),
    readWorkspaceText: vi.fn(),
    revokeExecutionGrant: vi.fn(),
    rollbackWorkspace: vi.fn(),
    writeWorkspaceText: vi.fn(),
  };
});

const repository: RepositoryHandle = {
  id: "10000000-0000-4000-8000-000000000001",
  runner_id: "10000000-0000-4000-8000-000000000002",
  runner_display_name: "Phase 4 Runner",
  opaque_handle: "fixture-repository-v1",
  display_name: "Phase 4 Adversarial Fixture",
  vcs_kind: "git",
  status: "available",
  capabilities: ["committed_head_read", "isolated_workspace"],
  current_revision: "a".repeat(40),
  current_branch: "main",
  source_status: "unknown",
  source_is_dirty: true,
  dirty_path_count: 10000,
  last_verified_at: "2026-07-27T01:00:00Z",
  metadata_version: 1,
  created_at: "2026-07-27T01:00:00Z",
  updated_at: "2026-07-27T01:00:00Z",
};

const grant: ExecutionGrant = {
  id: "20000000-0000-4000-8000-000000000001",
  grant_version: 1,
  task_id: "20000000-0000-4000-8000-000000000002",
  run_id: "20000000-0000-4000-8000-000000000003",
  plan_id: "20000000-0000-4000-8000-000000000004",
  repository_handle_id: repository.id,
  repository_display_name: repository.display_name,
  runner_id: repository.runner_id,
  source_revision: "a".repeat(40),
  snapshot_fingerprint: "b".repeat(64),
  allowed_operations: [
    "prepare",
    "list",
    "read_text",
    "write_text",
    "status",
    "diff",
    "rollback",
    "discard",
  ],
  allowed_paths: ["sandbox/**"],
  denied_paths: [".git/**", ".env", ".env.*", "**/*.pem"],
  max_files_changed: 8,
  max_total_write_bytes: 131072,
  max_single_file_bytes: 32768,
  max_diff_bytes: 32768,
  workspace_ttl_seconds: 1200,
  network_policy: "none",
  shell_access: false,
  git_delivery_access: false,
  source_repository_write_access: false,
  validation_workspace_id: null,
  validation_checkpoint_id: null,
  allowed_validation_profiles: [],
  allowed_validation_suites: [],
  max_validation_runs: 0,
  validation_timeout_seconds: 0,
  validation_cpu_seconds: 0,
  validation_memory_bytes: 0,
  validation_pid_limit: 0,
  validation_fd_limit: 0,
  validation_output_bytes: 0,
  validation_artifact_bytes: 0,
  validation_artifact_count: 0,
  status: "pending",
  in_flight_permit_count: 0,
  policy_hash: "c".repeat(64),
  requested_at: "2026-07-27T01:00:00Z",
  decided_at: null,
  revocation_requested_at: null,
  revoked_at: null,
  expires_at: "2026-07-27T01:30:00Z",
  created_at: "2026-07-27T01:00:00Z",
  decision: null,
};

const workspace: Workspace = {
  id: "30000000-0000-4000-8000-000000000001",
  grant_id: grant.id,
  runner_id: repository.runner_id,
  runner_display_name: repository.runner_display_name,
  repository_handle_id: repository.id,
  repository_display_name: repository.display_name,
  source_revision: "a".repeat(40),
  state: "ready",
  workspace_fingerprint: "d".repeat(64),
  initial_tree_hash: "e".repeat(64),
  current_tree_hash: "e".repeat(64),
  changed_file_count: 0,
  total_written_bytes: 0,
  max_files_changed: 8,
  max_total_write_bytes: 131072,
  max_single_file_bytes: 32768,
  max_diff_bytes: 32768,
  created_paths: [],
  active_attempt_id: null,
  expires_at: "2026-07-27T01:20:00Z",
  created_at: "2026-07-27T01:00:00Z",
  updated_at: "2026-07-27T01:00:00Z",
  sealed_at: null,
  discarded_at: null,
  error_code: null,
  error_message: null,
  latest_job_id: null,
  latest_job_kind: null,
  latest_job_state: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listRepositories).mockResolvedValue([repository]);
  vi.mocked(listEligibleExecutionContexts).mockResolvedValue([
    {
      plan_id: grant.plan_id,
      run_id: grant.run_id!,
      task_id: grant.task_id!,
      plan_version: 1,
      task_title: "Phase 4 fixture",
      repository_handle_id: repository.id,
      repository_display_name: repository.display_name,
      source_revision: grant.source_revision,
      snapshot_fingerprint: grant.snapshot_fingerprint,
    },
  ]);
  vi.mocked(listExecutionGrants).mockResolvedValue([grant]);
  vi.mocked(createExecutionGrant).mockResolvedValue(grant);
  vi.mocked(decideExecutionGrant).mockResolvedValue({
    ...grant,
    status: "approved",
    decided_at: "2026-07-27T01:01:00Z",
  });
  vi.mocked(listWorkspaces).mockResolvedValue([workspace]);
  vi.mocked(createWorkspace).mockResolvedValue({
    workspace,
    job: runnerJobFixture({ kind: "workspace_prepare_v1" }),
  });
  vi.mocked(getWorkspace).mockResolvedValue(workspace);
  vi.mocked(listWorkspaceEvents).mockResolvedValue([]);
  vi.mocked(listWorkspaceCheckpoints).mockResolvedValue([]);
  vi.mocked(readWorkspaceText).mockResolvedValue({
    workspace,
    job: runnerJobFixture({ kind: "workspace_read_text_v1" }),
  });
  vi.mocked(getRunnerJob).mockResolvedValue(
    runnerJobFixture({
      kind: "workspace_read_text_v1",
      state: "succeeded",
      result: {
        kind: "workspace_read_text_v1",
        workspace_id: workspace.id,
        relative_path: "sandbox/original.txt",
        content: "Original fixture text.\n",
        sha256: "f".repeat(64),
        size: 23,
      },
    }),
  );
});

describe("Phase 4 browser surfaces", () => {
  it("renders the opaque repository without a host path", async () => {
    render(<RepositoryConsole />);
    expect(
      await screen.findByRole("heading", {
        name: "Phase 4 Adversarial Fixture",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("available")).toBeInTheDocument();
    expect(
      screen.getByText(/Source working-tree status is intentionally unknown/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/\/Users\/|\/repositories\/fixture/)).toBeNull();
  });

  it("requires a separate Grant decision and shows closed policy fields", async () => {
    const user = userEvent.setup();
    render(<ExecutionGrantConsole />);
    expect(
      await screen.findByText(
        "Plan approval does not authorize execution. This Execution Grant is a separate human decision.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("sandbox/**")).toBeInTheDocument();
    expect(screen.getByText(/network none/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Approve Grant" }));
    await waitFor(() =>
      expect(decideExecutionGrant).toHaveBeenCalledWith(
        grant.id,
        expect.objectContaining({ decision: "approve" }),
      ),
    );
  });

  it("shows requested versus effective Grant revocation", async () => {
    vi.mocked(listExecutionGrants).mockResolvedValue([
      {
        ...grant,
        status: "revoke_requested",
        in_flight_permit_count: 1,
        revocation_requested_at: "2026-07-27T01:02:00Z",
      },
    ]);
    render(<ExecutionGrantConsole />);
    expect(await screen.findByText("revoke_requested")).toBeInTheDocument();
    expect(
      screen.getByText(
        /effective revocation waits for 1 bounded in-flight permit/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revoke" })).toBeNull();
  });

  it("creates a workspace only from an approved Grant", async () => {
    vi.mocked(listExecutionGrants).mockResolvedValue([
      { ...grant, status: "approved" },
    ]);
    const user = userEvent.setup();
    render(<WorkspaceConsole />);
    await user.click(
      await screen.findByRole("button", { name: "Prepare Workspace" }),
    );
    await waitFor(() => expect(createWorkspace).toHaveBeenCalledWith(grant.id));
    expect(push).toHaveBeenCalledWith(`/workspaces/${workspace.id}`);
  });

  it("shows typed read output, hash preflight, and no free-form shell", async () => {
    const user = userEvent.setup();
    render(<WorkspaceDetailConsole workspaceId={workspace.id} />);
    const tools = await screen.findByRole("heading", {
      name: "Typed Tool Console",
    });
    expect(tools).toBeInTheDocument();
    expect(screen.queryByLabelText(/shell/i)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Read text" }));
    expect(
      await screen.findByText("Original fixture text."),
    ).toBeInTheDocument();
    const preflight = screen.getByLabelText("Write preflight");
    expect(within(preflight).getAllByText("f".repeat(64))).toHaveLength(2);
    expect(within(preflight).getByText("Remaining budget")).toBeInTheDocument();
  });

  it("runs bounded list and lifecycle actions through typed controls", async () => {
    vi.mocked(listWorkspaceDirectory).mockResolvedValue({
      workspace,
      job: runnerJobFixture({ kind: "workspace_list_v1" }),
    });
    vi.mocked(getWorkspaceStatus).mockResolvedValue({
      workspace,
      job: runnerJobFixture({ kind: "workspace_status_v1" }),
    });
    vi.mocked(getWorkspaceDiff).mockResolvedValue({
      workspace,
      job: runnerJobFixture({ kind: "workspace_diff_v1" }),
    });
    vi.mocked(rollbackWorkspace).mockResolvedValue({
      workspace,
      job: runnerJobFixture({ kind: "workspace_rollback_v1" }),
    });
    vi.mocked(getRunnerJob)
      .mockResolvedValueOnce(
        runnerJobFixture({
          kind: "workspace_list_v1",
          state: "succeeded",
          result: {
            kind: "workspace_list_v1",
            workspace_id: workspace.id,
            relative_directory: "sandbox",
            entries: [
              {
                relative_path: "sandbox/original.txt",
                entry_type: "text",
                size: 23,
                sha256: "f".repeat(64),
              },
            ],
            truncated: false,
          },
        }),
      )
      .mockResolvedValue(
        runnerJobFixture({
          kind: "workspace_status_v1",
          state: "succeeded",
        }),
      );

    const user = userEvent.setup();
    render(<WorkspaceDetailConsole workspaceId={workspace.id} />);
    await screen.findByRole("heading", { name: "Typed Tool Console" });

    await user.click(screen.getByRole("button", { name: "List" }));
    expect(await screen.findAllByText("sandbox/original.txt")).toHaveLength(2);
    expect(listWorkspaceDirectory).toHaveBeenCalledWith(workspace.id, {
      relative_directory: "sandbox",
      depth: 3,
      max_entries: 200,
    });

    for (const [label, action] of [
      ["Status", getWorkspaceStatus],
      ["Diff + Seal", getWorkspaceDiff],
      ["Rollback to initial", rollbackWorkspace],
    ] as const) {
      const button = screen.getByRole("button", { name: label });
      await waitFor(() => expect(button).toBeEnabled());
      await user.click(button);
      await waitFor(() => expect(action).toHaveBeenCalledWith(workspace.id));
    }
  });

  it("renders structured policy conflict feedback", async () => {
    vi.mocked(getWorkspace).mockRejectedValueOnce(
      new ApiError("Grant has been revoked", {
        status: 409,
        code: "execution_grant_inactive",
      }),
    );
    render(<WorkspaceDetailConsole workspaceId={workspace.id} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("execution_grant_inactive");
    expect(within(alert).getByRole("button", { name: "重试" })).toBeVisible();
  });

  it("blocks every destructive control for ownership recovery states", async () => {
    vi.mocked(getWorkspace).mockResolvedValue({
      ...workspace,
      state: "recovery_required",
      error_code: "workspace_recovery_required",
      error_message: "Signed ownership proof is missing.",
    });
    render(<WorkspaceDetailConsole workspaceId={workspace.id} />);
    expect(
      await screen.findByText("Workspace ownership proof is missing."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discard" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Rollback to initial" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Replace text" })).toBeDisabled();
  });

  it("keeps a typed action denial visible after refreshing durable state", async () => {
    vi.mocked(writeWorkspaceText).mockRejectedValue(
      new ApiError("Sensitive Workspace path is denied", {
        status: 403,
        code: "sensitive_path_denied",
      }),
    );
    const user = userEvent.setup();
    render(<WorkspaceDetailConsole workspaceId={workspace.id} />);
    await screen.findByRole("heading", { name: "Typed Tool Console" });
    await user.click(screen.getByRole("radio", { name: "create" }));
    await user.clear(screen.getByLabelText("Relative path"));
    await user.type(screen.getByLabelText("Relative path"), "sandbox/.env");
    await user.click(screen.getByRole("button", { name: "Create text" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("sensitive_path_denied");
    await waitFor(() => expect(getWorkspace).toHaveBeenCalledTimes(2));
    expect(alert).toHaveTextContent("sensitive_path_denied");
  });
});
