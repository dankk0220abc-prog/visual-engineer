import { ApiError } from "./api";

export const localizedStatusKeys = [
  "approved",
  "active",
  "available",
  "awaiting_approval",
  "awaiting_plan_approval",
  "cancel_requested",
  "cancelled",
  "checking",
  "claimed",
  "created",
  "completed",
  "confirmable",
  "cancelled_before_dispatch",
  "destroyed",
  "dispatched",
  "dispatching",
  "discard_requested",
  "discarded",
  "expired",
  "failed",
  "fixture_validated",
  "fresh",
  "generated",
  "generating",
  "healthy",
  "leased",
  "lease_expired",
  "legacy_unavailable",
  "live_billing_unknown",
  "live_cost_reported",
  "mock_not_billable",
  "not_billable_fixture",
  "not_dispatched",
  "offline",
  "online",
  "outcome_unknown",
  "pending",
  "plan_ready",
  "preparing",
  "prepared",
  "process_memory_only",
  "queued",
  "ready",
  "blocked",
  "registered",
  "recovery_required",
  "reported",
  "reported_complete",
  "reported_invalid",
  "reported_partial",
  "supported",
  "requested",
  "rejected",
  "revoke_requested",
  "revoked",
  "running",
  "snapshot_ready",
  "snapshotting",
  "draft",
  "rollback_requested",
  "rolled_back",
  "sealed",
  "sealing",
  "skipped",
  "quarantined",
  "stale",
  "succeeded",
  "synthetic_complete",
  "superseded",
  "timed_out",
  "timeout",
  "unavailable",
  "unknown",
  "not_ready",
  "not_performed",
  "live_verified",
  "not_required",
  "not_connected",
  "connected",
] as const;

export type LocalizedStatusKey = (typeof localizedStatusKeys)[number];

export function isLocalizedStatus(value: string): value is LocalizedStatusKey {
  return localizedStatusKeys.includes(value as LocalizedStatusKey);
}

type Translator = (
  key: string,
  values?: Record<string, string | number>,
) => string;

export const localizedErrorKeys = [
  "atomic_write_failed",
  "binary_denied",
  "conflict",
  "content_conflict",
  "control_plane_unavailable",
  "delivery_authorization_conflict",
  "delivery_authorization_expired",
  "delivery_authorization_idempotency_conflict",
  "delivery_authorization_invalid",
  "delivery_authorization_missing",
  "delivery_authorization_not_approved",
  "delivery_authorization_not_dispatchable",
  "delivery_authorization_not_found",
  "delivery_authorization_not_pending",
  "delivery_authorization_stale",
  "delivery_baseline_mismatch",
  "delivery_checkpoint_missing",
  "delivery_confirmation_mismatch",
  "delivery_decision_conflict",
  "delivery_decision_idempotency_conflict",
  "delivery_dispatch_budget_exhausted",
  "delivery_dispatch_conflict",
  "delivery_dispatch_idempotency_conflict",
  "delivery_empty_diff",
  "delivery_execution_authority_inactive",
  "delivery_manifest_invalid",
  "delivery_readiness_required",
  "delivery_retry_lineage_invalid",
  "diff_budget_exceeded",
  "envelope_expired",
  "envelope_hash_mismatch",
  "execution_grant_hash_mismatch",
  "execution_grant_inactive",
  "expected_absent_conflict",
  "file_count_budget_exceeded",
  "file_too_large",
  "git_output_limit_exceeded",
  "hardlink_denied",
  "internal_error",
  "invalid_idempotency_key",
  "invalid_response",
  "invalid_utf8",
  "lease_lost",
  "local_delivery_already_succeeded",
  "local_delivery_result_binding_mismatch",
  "mirror_budget_exceeded",
  "network_error",
  "not_regular_file",
  "operation_digest_mismatch",
  "path_denied",
  "path_invalid",
  "plan_revision_policy_violation",
  "plan_submission_policy_violation",
  "policy_denied",
  "protocol_payload_too_large",
  "provider_disabled",
  "provider_not_configured",
  "repository_head_unavailable",
  "repository_kind_not_supported",
  "repository_revision_changed",
  "repository_scan_failed",
  "repository_unavailable",
  "result_rejected",
  "retry_exhausted",
  "review_package_not_found",
  "runner_internal_error",
  "sensitive_path_denied",
  "side_effect_permit_invalid",
  "side_effect_permit_required",
  "side_effect_permit_expired",
  "source_not_read_only",
  "source_revision_mismatch",
  "stale_review_package",
  "symlink_denied",
  "total_write_budget_exceeded",
  "unsupported_capability",
  "validation_error",
  "validation_artifact_limit_exceeded",
  "validation_checkpoint_mismatch",
  "validation_cleanup_failed",
  "validation_command_failed",
  "validation_output_limit_exceeded",
  "validation_process_remained",
  "validation_profile_denied",
  "validation_sandbox_denied",
  "validation_sandbox_unavailable",
  "validation_suite_output_limit_exceeded",
  "validation_suite_timed_out",
  "validation_timed_out",
  "workspace_cancelled",
  "workspace_identity_mismatch",
  "workspace_not_found",
  "workspace_quarantined",
  "workspace_recovery_required",
  "workspace_side_effect_in_flight",
  "workspace_state_invalid",
] as const;

export type LocalizedErrorKey = (typeof localizedErrorKeys)[number];

const stableErrorKeys = new Set<string>(localizedErrorKeys);

export const localizedActionKeys = {
  validation_suite_v1: "validationSuiteOperation",
  workspace_text_create_v1: "createText",
  workspace_text_replace_v1: "replaceText",
} as const;

export type LocalizedActionKey = keyof typeof localizedActionKeys;

export const localizedEvalKeys = {
  approval_boundary_bypass: "approvalBoundaryBypass",
  deterministic_replay: "deterministicReplay",
  forbidden_operation: "forbiddenOperation",
  generation_binding_integrity: "generationBindingIntegrity",
  hallucinated_repository_fact: "hallucinatedRepositoryFact",
  malicious_requirement_prompt_injection: "maliciousRequirementPromptInjection",
  missing_acceptance_criteria: "missingAcceptanceCriteria",
  over_budget_context: "overBudgetContext",
  schema_validity: "schemaValidity",
  secret_context_leakage: "secretContextLeakage",
  stale_revision: "staleRevision",
  unsupported_file_reference: "unsupportedFileReference",
} as const;

export type LocalizedEvalKey = keyof typeof localizedEvalKeys;

export function localizeAction(
  action: LocalizedActionKey,
  t: Translator,
  values?: Record<string, string | number>,
): string {
  return t(localizedActionKeys[action], values);
}

export function localizeEval(evalId: string, t: Translator): string {
  const key = localizedEvalKeys[evalId as LocalizedEvalKey] ?? "unknown";
  return t(`eval.${key}`);
}

export function localizeStatus(value: string, t: Translator): string {
  return isLocalizedStatus(value)
    ? t(value)
    : t("unknownWithCode", { code: value });
}

export function localizeErrorCode(
  code: string,
  t: Translator,
  requestId?: string | null,
  rawDiagnosticCode = code,
): string {
  const localized = stableErrorKeys.has(code)
    ? t(code)
    : t("unknownWithCode", { code });
  const diagnosticCode = stableErrorKeys.has(code)
    ? t("diagnosticCode", { code: rawDiagnosticCode })
    : "";
  const requestReference = requestId
    ? t("requestReference", { requestId })
    : "";

  return [localized, diagnosticCode, requestReference]
    .filter(Boolean)
    .join(" ");
}

export function localizeApiError(error: unknown, t: Translator): string {
  if (!(error instanceof ApiError)) return t("unexpected");

  const key = stableErrorKeys.has(error.code)
    ? error.code
    : error.status === 409
      ? "conflict"
      : error.code;
  return localizeErrorCode(key, t, error.requestId, error.code);
}
