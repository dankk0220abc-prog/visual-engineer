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
  "destroyed",
  "dispatched",
  "discard_requested",
  "discarded",
  "expired",
  "failed",
  "fresh",
  "generated",
  "generating",
  "healthy",
  "leased",
  "lease_expired",
  "offline",
  "online",
  "pending",
  "plan_ready",
  "preparing",
  "queued",
  "ready",
  "blocked",
  "registered",
  "recovery_required",
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
  "sealing",
  "quarantined",
  "stale",
  "succeeded",
  "timed_out",
  "timeout",
  "unavailable",
] as const;

export type LocalizedStatusKey = (typeof localizedStatusKeys)[number];

export function isLocalizedStatus(value: string): value is LocalizedStatusKey {
  return localizedStatusKeys.includes(value as LocalizedStatusKey);
}

type Translator = (
  key: string,
  values?: Record<string, string | number>,
) => string;

const stableErrorKeys = new Set([
  "conflict",
  "envelope_expired",
  "execution_grant_inactive",
  "internal_error",
  "invalid_response",
  "network_error",
  "operation_digest_mismatch",
  "plan_revision_policy_violation",
  "plan_submission_policy_violation",
  "protocol_payload_too_large",
  "repository_head_unavailable",
  "repository_kind_not_supported",
  "repository_revision_changed",
  "repository_scan_failed",
  "retry_exhausted",
  "side_effect_permit_expired",
  "validation_error",
  "validation_suite_output_limit_exceeded",
  "validation_suite_timed_out",
  "workspace_cancelled",
  "workspace_side_effect_in_flight",
]);

export function localizeApiError(error: unknown, t: Translator): string {
  if (!(error instanceof ApiError)) return t("unexpected");

  const key = error.status === 409 ? "conflict" : error.code;
  const localized = stableErrorKeys.has(key)
    ? t(key)
    : t("unknownWithCode", { code: error.code });
  const diagnosticCode = stableErrorKeys.has(key)
    ? t("diagnosticCode", { code: error.code })
    : "";
  const requestReference = error.requestId
    ? t("requestReference", { requestId: error.requestId })
    : "";

  return [localized, diagnosticCode, requestReference]
    .filter(Boolean)
    .join(" ");
}
