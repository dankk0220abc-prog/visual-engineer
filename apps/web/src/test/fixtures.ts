import type {
  AuditEvent,
  Plan,
  Run,
  Runner,
  RunnerJob,
  RunnerJobEvent,
  Snapshot,
  Task,
} from "@/lib/api";

export function taskFixture(overrides: Partial<Task> = {}): Task {
  return {
    id: "9dbe3a52-3db5-4d10-bbfb-94f15f6fe4bc",
    title: "Improve navigation",
    objective: "Make primary navigation easier to understand.",
    repository_kind: "local_path",
    repository_display_name: "design-system",
    repository_locator: "/workspace/design-system",
    status: "draft",
    version: 1,
    created_at: "2026-07-26T03:00:00Z",
    updated_at: "2026-07-26T03:00:00Z",
    ...overrides,
  } as Task;
}

export function runFixture(overrides: Partial<Run> = {}): Run {
  return {
    id: "d8788052-d6d0-4c48-a5e6-b31ab3258341",
    task_id: "9dbe3a52-3db5-4d10-bbfb-94f15f6fe4bc",
    status: "created",
    permission_level: "read_only",
    snapshot_mode: "git_head",
    version: 1,
    trace_id: "14ac4e04-5dbf-440e-b01c-7b47ca2a963e",
    current_plan_version: null,
    error_code: null,
    error_message: null,
    created_at: "2026-07-26T04:00:00Z",
    updated_at: "2026-07-26T04:00:00Z",
    ...overrides,
  } as Run;
}

export function snapshotFixture(overrides: Partial<Snapshot> = {}): Snapshot {
  return {
    id: "fc0d5b84-614b-4c1c-994c-50aa284123e8",
    run_id: "d8788052-d6d0-4c48-a5e6-b31ab3258341",
    source_revision: "a".repeat(40),
    branch_name: "main",
    repository_is_dirty: true,
    dirty_path_count: 2,
    dirty_paths: [
      { relative_path: "src/local.ts", status: " M", untracked: false },
      { relative_path: "notes.txt", status: "??", untracked: true },
    ],
    scanner_version: "1.0.0",
    scan_policy_version: "phase2-v1",
    fingerprint: "b".repeat(64),
    tracked_file_count: 120,
    selected_file_count: 14,
    skipped_file_count: 106,
    total_selected_bytes: 8192,
    tech_stack: {
      frameworks: ["Next.js", "React", "Vitest"],
      languages: ["TypeScript", "CSS"],
      provenance: "committed_head_structured_extraction",
    },
    package_manager: "pnpm",
    available_scripts: [
      { kind: "package_script", workspace: ".", script: "test" },
    ],
    test_surfaces: [
      { kind: "test_path", relative_path: "src/example.test.tsx" },
    ],
    design_system_signals: [
      {
        kind: "ui_component_library",
        relative_path: "src/components/ui/button.tsx",
      },
    ],
    repository_instructions: [
      {
        relative_path: "AGENTS.md",
        risk_label: "prompt_injection_risk",
        provenance: "untrusted_repository_content",
      },
    ],
    safety_findings: [
      {
        relative_path: ".env",
        rule_type: "environment_file",
        blocked: true,
        summary: "Sensitive file path detected; content was not read",
      },
      {
        relative_path: "AGENTS.md",
        rule_type: "prompt_injection_secret_access_request",
        blocked: true,
        summary:
          "Untrusted repository instruction was classified but not followed",
      },
    ],
    manifest: [],
    created_at: "2026-07-26T04:01:00Z",
    ...overrides,
  } as Snapshot;
}

export function planFixture(overrides: Partial<Plan> = {}): Plan {
  return {
    id: "610f6ff2-7afb-48f6-a070-8c41ac29e8f6",
    run_id: "d8788052-d6d0-4c48-a5e6-b31ab3258341",
    version: 1,
    status: "draft",
    source: "deterministic_policy",
    snapshot_fingerprint: "b".repeat(64),
    delivery_package: "frontend_quality_remediation",
    objective_summary: "Remediate the approved frontend quality surface.",
    repository_context_summary:
      "Committed HEAD with Next.js, React, and Vitest.",
    assumptions: ["Committed HEAD remains the planning baseline."],
    proposed_change_scope: ["Remediate the approved responsive surface."],
    explicit_non_goals: ["No code execution in Phase 2."],
    risk_items: ["Dirty work remains outside the plan."],
    acceptance_criteria: ["Verify desktop and narrow viewports."],
    evidence_requirements: ["Bound snapshot fingerprint."],
    stop_conditions: ["Stop if the fingerprint changes."],
    validation_steps: [
      { kind: "package_script", workspace: ".", script: "test" },
      { kind: "browser_check", check: "accessibility", viewport: "both" },
    ],
    required_future_permission_level: "level_2_controlled_validation",
    execution_available: false,
    content_hash: "c".repeat(64),
    created_at: "2026-07-26T04:02:00Z",
    ...overrides,
  } as Plan;
}

export function auditFixture(overrides: Partial<AuditEvent> = {}): AuditEvent {
  return {
    id: "28bcaa68-a447-4d07-a0d2-76f25df29fb0",
    run_id: "d8788052-d6d0-4c48-a5e6-b31ab3258341",
    event_type: "run_created",
    actor_type: "local_user",
    request_id: "request-fixture",
    metadata: { permission_level: "read_only" },
    created_at: "2026-07-26T04:00:00Z",
    ...overrides,
  } as AuditEvent;
}

export function runnerFixture(overrides: Partial<Runner> = {}): Runner {
  return {
    id: "271ad4e1-4bc2-41db-a954-973b14dcf008",
    display_name: "Local Docker Runner",
    protocol_version: 1,
    software_version: "0.3.0",
    capabilities: ["controlled_wait_v1", "system_diagnostic_v1"],
    status: "online",
    last_seen_at: "2026-07-26T16:00:00Z",
    registered_at: "2026-07-26T15:59:00Z",
    revoked_at: null,
    version: 2,
    created_at: "2026-07-26T15:59:00Z",
    updated_at: "2026-07-26T16:00:00Z",
    active_job: null,
    ...overrides,
  } as Runner;
}

export function runnerJobFixture(
  overrides: Partial<RunnerJob> = {},
): RunnerJob {
  return {
    id: "a4993354-a21a-4c68-af85-286390e6bda2",
    kind: "system_diagnostic_v1",
    state: "queued",
    requested_by: "local_user",
    parameters: {},
    active_attempt_id: null,
    attempt_count: 0,
    max_attempts: 2,
    result: null,
    error_code: null,
    error_message: null,
    version: 1,
    created_at: "2026-07-26T16:01:00Z",
    updated_at: "2026-07-26T16:01:00Z",
    completed_at: null,
    permission_envelope: {
      id: "890cb53b-54e0-4dcc-8349-1b7e423257ba",
      envelope_version: 1,
      job_id: "a4993354-a21a-4c68-af85-286390e6bda2",
      authorization_source: "local_user_job_dispatch",
      allowed_capabilities: ["system_diagnostic_v1"],
      repository_access: "none",
      shell_access: false,
      network_policy: "control_plane_only",
      max_runtime_seconds: 10,
      lease_seconds: 6,
      max_attempts: 2,
      max_result_bytes: 8192,
      issued_at: "2026-07-26T16:01:00Z",
      expires_at: "2026-07-26T16:06:00Z",
      policy_hash: "d".repeat(64),
      created_at: "2026-07-26T16:01:00Z",
    },
    active_attempt: null,
    attempts: [],
    ...overrides,
  } as RunnerJob;
}

export function runnerJobEventFixture(
  overrides: Partial<RunnerJobEvent> = {},
): RunnerJobEvent {
  return {
    id: "671c2cd6-ac7f-4369-b8a5-2fa8c6ea71c4",
    runner_id: null,
    job_id: "a4993354-a21a-4c68-af85-286390e6bda2",
    attempt_id: null,
    event_type: "job_created",
    sequence: 1,
    request_id: "runner-event-fixture",
    metadata: { kind: "system_diagnostic_v1" },
    created_at: "2026-07-26T16:01:00Z",
    ...overrides,
  } as RunnerJobEvent;
}
