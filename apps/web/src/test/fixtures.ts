import type {
  AIPlanRequest,
  AuditEvent,
  Plan,
  Run,
  Runner,
  RunnerJob,
  RunnerJobEvent,
  Snapshot,
  Task,
} from "@/lib/api";

export function aiPlanRequestFixture(
  overrides: Partial<AIPlanRequest> = {},
): AIPlanRequest {
  const provider = {
    provider_id: "deterministic-fixture",
    implementation_version: "fixture-v1",
    model_label: "fixture-planner-v1",
    deterministic: true as const,
    fixture_replay: true as const,
    structured_output: true as const,
    network_access: false as const,
    credentials_required: false as const,
    billing_basis: "synthetic_not_billable" as const,
    max_context_bytes: 16384,
    max_output_bytes: 65536,
  };
  const prompt = {
    template_id: "governed-ai-plan",
    version: "v1",
    digest: "d".repeat(64),
    context_manifest_digest: "8".repeat(64),
    source_revision: "a".repeat(40),
    snapshot_fingerprint: "b".repeat(64),
  };
  return {
    id: "2a1f170d-a5ce-4d8a-b9f5-5c47ba8c1bda",
    run_id: "d8788052-d6d0-4c48-a5e6-b31ab3258341",
    status: "generated",
    delivery_package: "frontend_quality_remediation",
    source_revision: "a".repeat(40),
    snapshot_fingerprint: "b".repeat(64),
    prompt_template_id: "governed-ai-plan",
    prompt_version: "v1",
    prompt_digest: "d".repeat(64),
    prompt_payload: { template_id: "governed-ai-plan", version: "v1" },
    provider_id: "deterministic-fixture",
    provider_metadata: provider,
    request_payload: {
      protocol_version: 1,
      authority_ceiling: "plan_proposal_only",
    },
    request_digest: "e".repeat(64),
    plan: {
      schema_version: 1,
      requirement_summary: "Improve the bounded fixture frontend surface.",
      repository_findings: [
        {
          finding_id: "finding-1",
          kind: "framework",
          summary: "Framework: React",
          context_reference_ids: ["ctx-0001"],
          fact_bindings: [
            {
              reference_id: "ctx-0001",
              semantic_kind: "framework",
              canonical_value: "Framework: React",
              source_path: null,
              fact_digest: "7".repeat(64),
            },
          ],
        },
      ],
      assumptions: ["Committed HEAD remains the exact planning baseline."],
      expected_changes: [
        {
          relative_path: "src/button.tsx",
          component: "Button",
          change_type: "modify",
          rationale: "Implement the bounded visual requirement.",
        },
      ],
      proposed_operations: [
        {
          kind: "workspace_text_replace_v1",
          relative_path: "src/button.tsx",
          intent: "Apply an approved compare-and-swap text replacement.",
          expected_content_sha256: "f".repeat(64),
        },
        {
          kind: "validation_suite_v1",
          suite_id: "governed-frontend-plan-v1",
          suite_version: 1,
        },
      ],
      validation_suites: [
        {
          suite_id: "governed-frontend-plan-v1",
          name: "Governed frontend validation",
          required: true,
          checks: [
            { kind: "browser_check", check: "accessibility", viewport: "both" },
            {
              kind: "repository_status_check",
              expected: "approved_scope_only",
            },
          ],
        },
      ],
      risks: [
        {
          risk_id: "revision-drift",
          severity: "high",
          summary: "The revision may change before approval.",
          mitigation: "Revalidate the exact revision before the decision.",
        },
      ],
      acceptance_criteria: [
        {
          criterion_id: "accessible",
          statement: "The approved surface passes accessibility validation.",
          validation_suite_ids: ["governed-frontend-plan-v1"],
        },
      ],
      unresolved_questions: [
        "Which approved visual reference is authoritative?",
      ],
      context_references: ["ctx-0001"],
      prompt,
      provider,
      authority_boundary: {
        provider_can_approve: false,
        execution_grant_issued: false,
        review_approval_issued: false,
        delivery_authorization_issued: false,
        git_or_deployment_authority: false,
      },
      deterministic_digest: "9".repeat(64),
    },
    deterministic_digest: "9".repeat(64),
    context_manifest: [
      {
        reference_id: "ctx-0001",
        kind: "framework",
        summary: "Framework: React",
      },
    ],
    context_digest: "8".repeat(64),
    context_bytes: 512,
    context_reference_count: 1,
    context_excluded_count: 2,
    redaction_record: [{ rule: "sensitive_path", replacement_count: 1 }],
    retry_count: 0,
    error_category: null,
    error_code: null,
    error_message: null,
    handoff_plan_id: null,
    traces: [
      {
        id: "7222f428-0b2c-4771-8f09-a8da0db4bda8",
        ai_plan_request_id: "2a1f170d-a5ce-4d8a-b9f5-5c47ba8c1bda",
        attempt_number: 1,
        status: "succeeded",
        provider_id: "deterministic-fixture",
        provider_metadata: provider,
        request_digest: "e".repeat(64),
        response_digest: "9".repeat(64),
        latency_ms: 7,
        input_tokens: 100,
        output_tokens: 200,
        total_tokens: 300,
        cost_estimate_microunits: 0,
        cost_basis: "synthetic_not_billable",
        error_category: null,
        error_code: null,
        retryable: false,
        redactions: [],
        created_at: "2026-08-01T10:00:00Z",
        completed_at: "2026-08-01T10:00:00Z",
      },
    ],
    eval_results: [
      {
        id: "9af2f04a-b2e1-44cd-a0d8-8406828a4873",
        ai_plan_request_id: "2a1f170d-a5ce-4d8a-b9f5-5c47ba8c1bda",
        eval_id: "schema_validity",
        passed: true,
        severity: "blocking",
        summary: "Provider response satisfies the closed AI Plan schema.",
        evidence: { schema_version: 1 },
        evaluator_version: "governed-ai-eval-v2",
        evaluator_trust: "system_policy",
        created_at: "2026-08-01T10:00:00Z",
      },
    ],
    decision: null,
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    ...overrides,
  } as AIPlanRequest;
}

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
