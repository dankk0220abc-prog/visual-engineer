import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  cancelValidationSuiteRun,
  createExecutionGrant,
  createValidationSuiteRun,
  createValidationRun,
  decideExecutionGrant,
  listExecutionGrants,
  listValidationProfiles,
  listValidationRuns,
  listValidationSuiteRuns,
  listValidationSuites,
  listWorkspaceCheckpoints,
  listWorkspaces,
  retryValidationSuiteRun,
  type ExecutionGrant,
  type ValidationProfile,
  type ValidationRun,
  type ValidationSuite,
  type ValidationSuiteRun,
  type Workspace,
  type WorkspaceCheckpoint,
} from "@/lib/api";

import { ValidationConsole } from "./validation-console";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    cancelValidationRun: vi.fn(),
    cancelValidationSuiteRun: vi.fn(),
    createExecutionGrant: vi.fn(),
    createValidationSuiteRun: vi.fn(),
    createValidationRun: vi.fn(),
    decideExecutionGrant: vi.fn(),
    listExecutionGrants: vi.fn(),
    listValidationProfiles: vi.fn(),
    listValidationRuns: vi.fn(),
    listValidationSuiteRuns: vi.fn(),
    listValidationSuites: vi.fn(),
    listWorkspaceCheckpoints: vi.fn(),
    listWorkspaces: vi.fn(),
    retryValidationSuiteRun: vi.fn(),
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

const suite: ValidationSuite = {
  suite_id: "fixture-integrity-suite-v1",
  suite_version: 1,
  name: "Trusted fixture integrity suite",
  purpose: "Runs two fixed Profiles in deterministic order.",
  steps: [
    {
      sequence: 1,
      step_id: "fixture-contract",
      profile_id: "fixture-python-stdlib-v1",
      profile_version: 1,
      timeout_seconds: 10,
      max_output_bytes: 8192,
      max_artifact_bytes: 0,
      max_artifact_count: 0,
    },
    {
      sequence: 2,
      step_id: "fixture-manifest",
      profile_id: "fixture-python-manifest-v1",
      profile_version: 1,
      timeout_seconds: 10,
      max_output_bytes: 4096,
      max_artifact_bytes: 0,
      max_artifact_count: 0,
    },
  ],
  failure_policy: "fail_fast",
  total_timeout_seconds: 30,
  total_output_bytes: 10000,
  max_attempts: 2,
  policy_digest: "a".repeat(64),
  network_policy: "none",
  shell_access: false,
  user_command_input: false,
  artifact_content_transfer: false,
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
  allowed_validation_suites: [],
  validation_suite_definition_digest: null,
  validation_suite_root_run_id: null,
  validation_suite_retry_of_run_id: null,
  validation_suite_attempt_number: 0,
  validation_suite_allowed_run_count: 0,
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
  allowed_validation_suites: [],
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
    result_schema_version: 1,
    validation_step_id: "fixture-contract",
    source_revision: workspace.source_revision,
    policy_digest: "2".repeat(64),
    fixed_argv: profile.safe_argv,
    fixed_argv_digest: "3".repeat(64),
    fixed_cwd: "<validation-input-root>",
    fixed_environment_digest: "4".repeat(64),
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
    artifact_manifest_digest: "5".repeat(64),
    side_effect_permit_id: "90000000-0000-4000-8000-000000000001",
    side_effect_permit_sequence: 1,
    side_effect_permit_digest: "6".repeat(64),
    fencing_token: "7".repeat(64),
    execution_envelope_digest: "8".repeat(64),
    evidence_digest: "9".repeat(64),
    created_at: "2026-07-29T01:03:03Z",
  },
  job: null,
};

const suiteGrant: ExecutionGrant = {
  ...validationGrant,
  id: "40000000-0000-4000-8000-000000000002",
  allowed_validation_profiles: [
    "fixture-python-stdlib-v1:v1",
    "fixture-python-manifest-v1:v1",
  ],
  allowed_validation_suites: ["fixture-integrity-suite-v1:v1"],
  validation_suite_definition_digest: suite.policy_digest,
  validation_suite_root_run_id: null,
  validation_suite_retry_of_run_id: null,
  validation_suite_attempt_number: 1,
  validation_suite_allowed_run_count: 1,
  max_validation_runs: 2,
  validation_timeout_seconds: 30,
  validation_output_bytes: 10000,
  status: "approved",
  decided_at: "2026-07-29T01:02:00Z",
};

const suiteRun: ValidationSuiteRun = {
  id: "51000000-0000-4000-8000-000000000001",
  run_id: implementationGrant.run_id!,
  plan_id: implementationGrant.plan_id,
  source_revision: workspace.source_revision,
  workspace_id: workspace.id,
  checkpoint_id: checkpoint.id,
  checkpoint_fingerprint: checkpoint.tree_fingerprint,
  execution_grant_id: suiteGrant.id,
  suite_id: "fixture-integrity-suite-v1",
  suite_version: 1,
  policy_digest: "a".repeat(64),
  failure_policy: "fail_fast",
  state: "queued",
  step_count: 2,
  completed_step_count: 0,
  total_timeout_seconds: 30,
  total_output_bytes: 10000,
  combined_output_bytes: 0,
  max_attempts: 2,
  attempt_number: 1,
  retry_of_suite_run_id: null,
  root_suite_run_id: "51000000-0000-4000-8000-000000000001",
  requested_at: "2026-07-29T01:03:00Z",
  started_at: "2026-07-29T01:03:00Z",
  deadline_at: "2026-07-29T01:03:30Z",
  cancel_requested_at: null,
  completed_at: null,
  error_code: null,
  error_message: null,
  version: 2,
  created_at: "2026-07-29T01:03:00Z",
  updated_at: "2026-07-29T01:03:00Z",
  steps: [
    {
      id: "71000000-0000-4000-8000-000000000001",
      sequence: 1,
      step_id: "fixture-contract",
      profile_id: "fixture-python-stdlib-v1",
      profile_version: 1,
      timeout_seconds: 10,
      max_output_bytes: 8192,
      state: "queued",
      validation_run_id: validationRun.id,
      runner_job_id: validationRun.runner_job_id,
      runner_id: null,
      attempt_id: null,
      lease_id: null,
      evidence_id: null,
      reused_from_step_run_id: null,
      started_at: null,
      completed_at: null,
      duration_ms: null,
      exit_code: null,
      output_bytes: 0,
      redaction_count: 0,
      output_truncated: false,
      cleanup_succeeded: null,
      failure_code: null,
      evidence: null,
    },
    {
      id: "71000000-0000-4000-8000-000000000002",
      sequence: 2,
      step_id: "fixture-manifest",
      profile_id: "fixture-python-manifest-v1",
      profile_version: 1,
      timeout_seconds: 10,
      max_output_bytes: 4096,
      state: "pending",
      validation_run_id: null,
      runner_job_id: null,
      runner_id: null,
      attempt_id: null,
      lease_id: null,
      evidence_id: null,
      reused_from_step_run_id: null,
      started_at: null,
      completed_at: null,
      duration_ms: null,
      exit_code: null,
      output_bytes: 0,
      redaction_count: 0,
      output_truncated: false,
      cleanup_succeeded: null,
      failure_code: null,
      evidence: null,
    },
  ],
  result: null,
};

const failedSuiteRun: ValidationSuiteRun = {
  ...suiteRun,
  state: "failed",
  completed_step_count: 2,
  combined_output_bytes: 64,
  completed_at: "2026-07-29T01:03:05Z",
  error_code: "validation_profile_failed",
  error_message: "Validation Suite stopped at step 2",
  steps: [
    {
      ...suiteRun.steps[0],
      state: "succeeded",
      evidence_id: validationRun.evidence!.id,
      evidence: validationRun.evidence,
      started_at: validationRun.started_at,
      completed_at: validationRun.completed_at,
      duration_ms: 50,
      exit_code: 0,
      output_bytes: 32,
      cleanup_succeeded: true,
    },
    {
      ...suiteRun.steps[1],
      state: "failed",
      validation_run_id: "51000000-0000-4000-8000-000000000002",
      runner_job_id: "61000000-0000-4000-8000-000000000002",
      started_at: "2026-07-29T01:03:04Z",
      completed_at: "2026-07-29T01:03:05Z",
      duration_ms: 50,
      exit_code: 1,
      output_bytes: 32,
      cleanup_succeeded: true,
      failure_code: "validation_profile_failed",
    },
  ],
  result: {
    id: "81000000-0000-4000-8000-000000000001",
    suite_run_id: "51000000-0000-4000-8000-000000000001",
    root_suite_run_id: "51000000-0000-4000-8000-000000000001",
    run_id: implementationGrant.run_id!,
    execution_grant_id: suiteGrant.id,
    suite_id: "fixture-integrity-suite-v1",
    suite_version: 1,
    source_revision: workspace.source_revision,
    checkpoint_id: checkpoint.id,
    policy_digest: "a".repeat(64),
    attempt_number: 1,
    total_timeout_seconds: 30,
    total_output_bytes: 10000,
    max_attempts: 2,
    verdict: "failed",
    profile_references: [
      "fixture-python-stdlib-v1:v1",
      "fixture-python-manifest-v1:v1",
    ],
    started_at: "2026-07-29T01:03:00Z",
    completed_at: "2026-07-29T01:03:05Z",
    duration_ms: 5000,
    combined_output_bytes: 64,
    redaction_count: 0,
    output_truncated: false,
    artifact_count: 0,
    artifact_bytes: 0,
    cancelled: false,
    timed_out: false,
    recovery_required: false,
    cleanup_succeeded: true,
    source_invariant: true,
    canonical_workspace_invariant: true,
    evidence_references: [{ sequence: 1 }],
    runner_references: [workspace.runner_id],
    audit_event_references: ["82000000-0000-4000-8000-000000000001"],
    aggregate_digest: "b".repeat(64),
    created_at: "2026-07-29T01:03:05Z",
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listValidationProfiles).mockResolvedValue([profile]);
  vi.mocked(listValidationRuns).mockResolvedValue([]);
  vi.mocked(listValidationSuites).mockResolvedValue([suite]);
  vi.mocked(listValidationSuiteRuns).mockResolvedValue([]);
  vi.mocked(listExecutionGrants).mockResolvedValue([implementationGrant]);
  vi.mocked(listWorkspaces).mockResolvedValue([workspace]);
  vi.mocked(listWorkspaceCheckpoints).mockResolvedValue([checkpoint]);
  vi.mocked(createExecutionGrant).mockResolvedValue(validationGrant);
  vi.mocked(decideExecutionGrant).mockResolvedValue({
    ...validationGrant,
    status: "approved",
  });
  vi.mocked(createValidationRun).mockResolvedValue(validationRun);
  vi.mocked(createValidationSuiteRun).mockResolvedValue(suiteRun);
  vi.mocked(cancelValidationSuiteRun).mockResolvedValue({
    ...suiteRun,
    state: "cancelled",
  });
  vi.mocked(retryValidationSuiteRun).mockResolvedValue({
    ...suiteRun,
    attempt_number: 2,
    retry_of_suite_run_id: suiteRun.id,
  });
});

describe("ValidationConsole", () => {
  it("shows the closed Suite and requests an exact Checkpoint Suite Grant", async () => {
    render(<ValidationConsole />);

    expect(
      await screen.findByText("Trusted fixture integrity suite"),
    ).toBeInTheDocument();
    expect(screen.getByText(/fixture-manifest/)).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "创建 pending Suite Grant",
      }),
    );

    await waitFor(() =>
      expect(createExecutionGrant).toHaveBeenCalledWith({
        plan_id: implementationGrant.plan_id,
        repository_handle_id: implementationGrant.repository_handle_id,
        validation_checkpoint_id: checkpoint.id,
        validation_suite_id: suite.suite_id,
        validation_suite_version: suite.suite_version,
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

    fireEvent.click(
      screen.getByRole("button", { name: "Run sealed first-slice Profile" }),
    );
    await waitFor(() => expect(createValidationRun).toHaveBeenCalledTimes(1));
    expect(createValidationRun).toHaveBeenCalledWith(
      {
        execution_grant_id: validationGrant.id,
        profile_id: profile.profile_id,
      },
      expect.stringMatching(`^validation-${validationGrant.id}-`),
    );
  });

  it("approves and starts only the fixed Suite from a Suite Grant", async () => {
    vi.mocked(listExecutionGrants)
      .mockResolvedValueOnce([
        implementationGrant,
        { ...suiteGrant, status: "pending", decided_at: null },
      ])
      .mockResolvedValue([implementationGrant, suiteGrant]);
    render(<ValidationConsole />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Approve exact Validation Grant",
      }),
    );
    await waitFor(() =>
      expect(decideExecutionGrant).toHaveBeenCalledWith(suiteGrant.id, {
        decision: "approve",
        reason:
          "Reviewed exact Checkpoint, fixed Suite, and validation-only budgets.",
      }),
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Run fixed Suite" }),
    );
    await waitFor(() => expect(createValidationSuiteRun).toHaveBeenCalled());
    expect(createValidationSuiteRun).toHaveBeenCalledWith(
      {
        execution_grant_id: suiteGrant.id,
        suite_id: suite.suite_id,
        suite_version: suite.suite_version,
      },
      expect.stringMatching(`^validation-suite-${suiteGrant.id}-`),
    );
  });

  it("cancels an active Suite and never exposes retry as a normal start", async () => {
    vi.mocked(listValidationSuiteRuns).mockResolvedValue([suiteRun]);
    vi.mocked(listExecutionGrants).mockResolvedValue([
      implementationGrant,
      suiteGrant,
    ]);
    render(<ValidationConsole />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Cancel Suite" }),
    );
    await waitFor(() =>
      expect(cancelValidationSuiteRun).toHaveBeenCalledWith(suiteRun.id),
    );
    expect(
      screen.queryByRole("button", { name: "Retry failed steps" }),
    ).not.toBeInTheDocument();
  });

  it("renders aggregate failure and retries only with a fresh approved Grant", async () => {
    const retryGrant = {
      ...suiteGrant,
      id: "40000000-0000-4000-8000-000000000003",
      validation_suite_root_run_id: failedSuiteRun.root_suite_run_id,
      validation_suite_retry_of_run_id: failedSuiteRun.id,
      validation_suite_attempt_number: 2,
    };
    vi.mocked(listValidationSuiteRuns).mockResolvedValue([failedSuiteRun]);
    vi.mocked(listExecutionGrants).mockResolvedValue([
      implementationGrant,
      suiteGrant,
      retryGrant,
    ]);
    render(<ValidationConsole />);

    expect(
      await screen.findByText("Aggregate Result: failed"),
    ).toBeInTheDocument();
    expect(screen.getByText(/validation_profile_failed/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry failed steps" }));
    await waitFor(() => expect(retryValidationSuiteRun).toHaveBeenCalled());
    expect(retryValidationSuiteRun).toHaveBeenCalledWith(
      failedSuiteRun.id,
      { execution_grant_id: retryGrant.id },
      expect.stringMatching(`^validation-suite-retry-${failedSuiteRun.id}-`),
    );
  });
});
