import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createExecutionGrant,
  createValidationRun,
  decideExecutionGrant,
  listExecutionGrants,
  listValidationProfiles,
  listValidationRuns,
  listWorkspaceCheckpoints,
  listWorkspaces,
  type ExecutionGrant,
  type ValidationProfile,
  type ValidationRun,
  type Workspace,
  type WorkspaceCheckpoint,
} from "@/lib/api";

import { ValidationConsole } from "./validation-console";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    cancelValidationRun: vi.fn(),
    createExecutionGrant: vi.fn(),
    createValidationRun: vi.fn(),
    decideExecutionGrant: vi.fn(),
    listExecutionGrants: vi.fn(),
    listValidationProfiles: vi.fn(),
    listValidationRuns: vi.fn(),
    listWorkspaceCheckpoints: vi.fn(),
    listWorkspaces: vi.fn(),
  };
});

const profile: ValidationProfile = {
  profile_id: "fixture-python-stdlib-v1",
  version: 1,
  display_name: "Trusted fixture Python contract",
  description: "Runs one system-owned exact-Checkpoint contract check.",
  step_id: "fixture-contract",
  safe_argv: ["python", "-I", "-S", "<system-owned-fixture-validator>"],
  timeout_seconds: 10,
  max_output_bytes: 8192,
  max_artifact_bytes: 0,
  max_artifact_count: 0,
  network_policy: "none",
  shell_access: false,
  user_command_input: false,
};

const implementationGrant: ExecutionGrant = {
  id: "10000000-0000-4000-8000-000000000001",
  grant_version: 1,
  task_id: "10000000-0000-4000-8000-000000000002",
  run_id: "10000000-0000-4000-8000-000000000003",
  plan_id: "10000000-0000-4000-8000-000000000004",
  repository_handle_id: "10000000-0000-4000-8000-000000000005",
  repository_display_name: "Fixture repository",
  runner_id: "10000000-0000-4000-8000-000000000006",
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
  denied_paths: [".git/**", ".env", "**/*.pem"],
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
  max_validation_runs: 0,
  validation_timeout_seconds: 0,
  validation_cpu_seconds: 0,
  validation_memory_bytes: 0,
  validation_pid_limit: 0,
  validation_fd_limit: 0,
  validation_output_bytes: 0,
  validation_artifact_bytes: 0,
  validation_artifact_count: 0,
  status: "approved",
  in_flight_permit_count: 0,
  policy_hash: "c".repeat(64),
  requested_at: "2026-07-29T01:00:00Z",
  decided_at: "2026-07-29T01:01:00Z",
  revocation_requested_at: null,
  revoked_at: null,
  expires_at: "2026-07-29T01:30:00Z",
  created_at: "2026-07-29T01:00:00Z",
  decision: null,
};

const workspace: Workspace = {
  id: "20000000-0000-4000-8000-000000000001",
  grant_id: implementationGrant.id,
  runner_id: implementationGrant.runner_id,
  runner_display_name: "Fixture Runner",
  repository_handle_id: implementationGrant.repository_handle_id,
  repository_display_name: implementationGrant.repository_display_name,
  source_revision: implementationGrant.source_revision,
  state: "ready",
  workspace_fingerprint: "d".repeat(64),
  initial_tree_hash: "e".repeat(64),
  current_tree_hash: "f".repeat(64),
  changed_file_count: 1,
  total_written_bytes: 24,
  max_files_changed: 8,
  max_total_write_bytes: 131072,
  max_single_file_bytes: 32768,
  max_diff_bytes: 32768,
  created_paths: [],
  active_attempt_id: null,
  latest_job_id: null,
  latest_job_kind: null,
  latest_job_state: null,
  sealed_at: null,
  discarded_at: null,
  error_code: null,
  error_message: null,
  expires_at: "2026-07-29T01:20:00Z",
  created_at: "2026-07-29T01:00:00Z",
  updated_at: "2026-07-29T01:00:00Z",
};

const checkpoint: WorkspaceCheckpoint = {
  id: "30000000-0000-4000-8000-000000000001",
  workspace_id: workspace.id,
  sequence: 1,
  source_revision: workspace.source_revision,
  tree_fingerprint: workspace.current_tree_hash!,
  diff_hash: "1".repeat(64),
  changed_paths: ["sandbox/original.txt"],
  changed_file_count: 1,
  total_diff_bytes: 42,
  diff_artifact: "bounded diff",
  side_effect_permit_id: null,
  created_at: "2026-07-29T01:02:00Z",
};

const validationGrant: ExecutionGrant = {
  ...implementationGrant,
  id: "40000000-0000-4000-8000-000000000001",
  allowed_operations: ["validate"],
  max_files_changed: 1,
  max_total_write_bytes: 4096,
  max_single_file_bytes: 4096,
  max_diff_bytes: 1,
  validation_workspace_id: workspace.id,
  validation_checkpoint_id: checkpoint.id,
  allowed_validation_profiles: ["fixture-python-stdlib-v1:v1"],
  max_validation_runs: 3,
  validation_timeout_seconds: 10,
  validation_cpu_seconds: 5,
  validation_memory_bytes: 134217728,
  validation_pid_limit: 8,
  validation_fd_limit: 64,
  validation_output_bytes: 8192,
  status: "pending",
  decided_at: null,
};

const validationRun: ValidationRun = {
  id: "50000000-0000-4000-8000-000000000001",
  run_id: implementationGrant.run_id!,
  plan_id: implementationGrant.plan_id,
  source_revision: workspace.source_revision,
  workspace_id: workspace.id,
  checkpoint_id: checkpoint.id,
  checkpoint_fingerprint: checkpoint.tree_fingerprint,
  execution_grant_id: validationGrant.id,
  runner_job_id: "60000000-0000-4000-8000-000000000001",
  runner_id: workspace.runner_id,
  attempt_id: "60000000-0000-4000-8000-000000000002",
  lease_id: "60000000-0000-4000-8000-000000000003",
  profile_id: "fixture-python-stdlib-v1",
  profile_version: 1,
  policy_digest: "2".repeat(64),
  state: "succeeded",
  timeout_seconds: 10,
  max_output_bytes: 8192,
  max_artifact_bytes: 0,
  max_artifact_count: 0,
  requested_at: "2026-07-29T01:03:00Z",
  claimed_at: "2026-07-29T01:03:01Z",
  started_at: "2026-07-29T01:03:02Z",
  cancel_requested_at: null,
  completed_at: "2026-07-29T01:03:03Z",
  error_code: null,
  error_message: null,
  version: 4,
  created_at: "2026-07-29T01:03:00Z",
  updated_at: "2026-07-29T01:03:03Z",
  step: {
    id: "70000000-0000-4000-8000-000000000001",
    sequence: 1,
    step_id: "fixture-contract",
    state: "succeeded",
    started_at: "2026-07-29T01:03:02Z",
    completed_at: "2026-07-29T01:03:03Z",
    duration_ms: 50,
    exit_code: 0,
    failure_code: null,
  },
  evidence: {
    id: "80000000-0000-4000-8000-000000000001",
    runner_id: workspace.runner_id,
    attempt_id: "60000000-0000-4000-8000-000000000002",
    lease_id: "60000000-0000-4000-8000-000000000003",
    fixed_argv: profile.safe_argv,
    started_at: "2026-07-29T01:03:02Z",
    completed_at: "2026-07-29T01:03:03Z",
    duration_ms: 50,
    exit_code: 0,
    stdout: "VE_VALIDATION_PROFILE_PASS\n",
    stderr: "",
    stdout_truncated: false,
    stderr_truncated: false,
    redaction_count: 0,
    timed_out: false,
    cancelled: false,
    network_isolated: true,
    filesystem_isolated: true,
    sandbox_cleaned: true,
    artifact_count: 0,
    artifact_bytes: 0,
    artifact_summary: { files: [] },
    side_effect_permit_id: "90000000-0000-4000-8000-000000000001",
    created_at: "2026-07-29T01:03:03Z",
  },
  job: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listValidationProfiles).mockResolvedValue([profile]);
  vi.mocked(listValidationRuns).mockResolvedValue([]);
  vi.mocked(listExecutionGrants).mockResolvedValue([implementationGrant]);
  vi.mocked(listWorkspaces).mockResolvedValue([workspace]);
  vi.mocked(listWorkspaceCheckpoints).mockResolvedValue([checkpoint]);
  vi.mocked(createExecutionGrant).mockResolvedValue(validationGrant);
  vi.mocked(decideExecutionGrant).mockResolvedValue({
    ...validationGrant,
    status: "approved",
  });
  vi.mocked(createValidationRun).mockResolvedValue(validationRun);
});

describe("ValidationConsole", () => {
  it("shows the closed Profile and requests an exact Checkpoint Grant", async () => {
    render(<ValidationConsole />);

    expect(
      await screen.findByText("Trusted fixture Python contract"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/python -I -S <system-owned-fixture-validator>/),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "创建 pending Validation Grant",
      }),
    );

    await waitFor(() =>
      expect(createExecutionGrant).toHaveBeenCalledWith({
        plan_id: implementationGrant.plan_id,
        repository_handle_id: implementationGrant.repository_handle_id,
        validation_checkpoint_id: checkpoint.id,
        validation_profile_id: profile.profile_id,
      }),
    );
  });

  it("requires explicit approval before starting the fixed Profile", async () => {
    vi.mocked(listExecutionGrants).mockResolvedValue([
      implementationGrant,
      validationGrant,
    ]);
    render(<ValidationConsole />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Approve exact Validation Grant",
      }),
    );

    await waitFor(() =>
      expect(decideExecutionGrant).toHaveBeenCalledWith(validationGrant.id, {
        decision: "approve",
        reason:
          "Reviewed exact Checkpoint, fixed Profile, and validation-only budgets.",
      }),
    );
  });

  it("renders bounded structured evidence", async () => {
    vi.mocked(listValidationRuns).mockResolvedValue([validationRun]);
    vi.mocked(listExecutionGrants).mockResolvedValue([
      implementationGrant,
      { ...validationGrant, status: "approved" },
    ]);
    render(<ValidationConsole />);

    expect(
      await screen.findByText("VE_VALIDATION_PROFILE_PASS"),
    ).toBeInTheDocument();
    expect(screen.getByText(/network true/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Run fixed Profile" }));
    await waitFor(() => expect(createValidationRun).toHaveBeenCalledTimes(1));
    expect(createValidationRun).toHaveBeenCalledWith(
      {
        execution_grant_id: validationGrant.id,
        profile_id: profile.profile_id,
      },
      expect.stringMatching(`^validation-${validationGrant.id}-`),
    );
  });
});
