from datetime import UTC, datetime

from visual_engineer_runner_protocol import (
    RUNNER_PROTOCOL_VERSION,
    Capability,
    JobAssignment,
    NetworkPolicy,
    RepositoryAccess,
    permission_policy_hash_matches,
)


class PermissionEnvelopeDeniedError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def validate_assignment(assignment: JobAssignment) -> None:
    envelope = assignment.permission_envelope
    expected_capability = Capability(assignment.job.kind.value)
    if envelope.envelope_version != RUNNER_PROTOCOL_VERSION:
        raise PermissionEnvelopeDeniedError("unsupported_protocol_version")
    if envelope.job_id != assignment.job_id:
        raise PermissionEnvelopeDeniedError("envelope_job_mismatch")
    if not permission_policy_hash_matches(envelope, envelope.policy_hash):
        raise PermissionEnvelopeDeniedError("envelope_hash_mismatch")
    if envelope.expires_at <= datetime.now(UTC):
        raise PermissionEnvelopeDeniedError("envelope_expired")
    if expected_capability not in envelope.allowed_capabilities:
        raise PermissionEnvelopeDeniedError("unsupported_capability")
    if envelope.repository_access != RepositoryAccess.NONE:
        raise PermissionEnvelopeDeniedError("repository_access_denied")
    if envelope.shell_access:
        raise PermissionEnvelopeDeniedError("shell_access_denied")
    if envelope.network_policy != NetworkPolicy.CONTROL_PLANE_ONLY:
        raise PermissionEnvelopeDeniedError("network_policy_denied")
    if assignment.attempt_number > envelope.max_attempts:
        raise PermissionEnvelopeDeniedError("attempt_budget_exceeded")
