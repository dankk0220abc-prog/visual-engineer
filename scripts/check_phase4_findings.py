from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FINDINGS = {
    "VE-P4-AUD-001": "Critical",
    "VE-P4-AUD-002": "Critical",
    "VE-P4-AUD-003": "High",
    "VE-P4-AUD-004": "Critical",
    "VE-P4-AUD-005": "Medium",
    "VE-P4-AUD-006": "Low",
}


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def _require_markers(relative_path: str, markers: tuple[str, ...]) -> None:
    source = _read(relative_path)
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise SystemExit(f"{relative_path} is missing Phase 4 controls: {missing}")


def _method_source(relative_path: str, class_name: str, method_name: str) -> str:
    path = REPOSITORY_ROOT / relative_path
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if child.name == method_name:
                        segment = ast.get_source_segment(source, child)
                        if segment is None:
                            break
                        return segment
    raise SystemExit(f"{relative_path} is missing {class_name}.{method_name}")


def _check_audit_is_preserved() -> None:
    audit = _read("docs/security/audits/phase-4-workspace-security-audit.md")
    if "Security Gate: FAIL" not in audit:
        raise SystemExit("The independent audit Security Gate FAIL must remain preserved")
    for finding_id, severity in FINDINGS.items():
        row = re.search(
            rf"^\|\s*{re.escape(finding_id)}\s*\|\s*{severity}\s*\|",
            audit,
            flags=re.MULTILINE,
        )
        if row is None:
            raise SystemExit(f"Independent audit finding is missing or changed: {finding_id}")
    repair = _read("docs/exec-plans/phase-4-security-repair.md")
    for finding_id in FINDINGS:
        if finding_id not in repair:
            raise SystemExit(f"Repair ExecPlan has no disposition for {finding_id}")
    if "READY FOR INDEPENDENT RE-AUDIT" not in repair:
        raise SystemExit("Repair ExecPlan must retain the independent re-audit boundary")
    if "Phase 4 Independent Security Re-Audit" not in repair:
        raise SystemExit("Repair ExecPlan must name the only next milestone")


def _check_source_adapter() -> None:
    inspect_source = _method_source(
        "apps/runner/src/visual_engineer_runner/git_ops.py",
        "GitOperations",
        "inspect_source",
    )
    if "self._run(" in inspect_source or "subprocess" in inspect_source:
        raise SystemExit("GitOperations.inspect_source must not invoke Git or another subprocess")
    _require_markers(
        "apps/runner/src/visual_engineer_runner/git_ops.py",
        (
            "SourceStatus.UNKNOWN",
            "_read_source_reference",
            "_copy_source_objects",
            "SourceObjectClosure",
            "core.hooksPath=/dev/null",
            "core.fsmonitor=false",
            "credential.helper=",
            "diff.external=",
            "filter.lfs.smudge=",
            "protocol.allow=never",
            "GIT_LFS_SKIP_SMUDGE",
            "GIT_SSH_COMMAND",
            "start_new_session=True",
            "GIT_OUTPUT_LIMIT_EXCEEDED",
        ),
    )
    _require_markers(
        "apps/runner/src/visual_engineer_runner/git_object_store.py",
        (
            "class SourceObjectClosure",
            '"alternates"',
            '"http-alternates"',
            '"grafts"',
            '"replace"',
            "_parse_pack_index",
            "_read_packed_object",
            "_apply_delta",
            '"gitlink"',
            "_validate_destination",
            "_write_new_object",
            "max_tree_depth",
            "max_delta_depth",
            "max_references",
            "MIRROR_BUDGET_EXCEEDED",
            "st_nlink",
            "os.link",
        ),
    )
    _require_markers(
        "scripts/check_source_invariance.py",
        (
            "post-checkout",
            "fsmonitor",
            "filter-smudge",
            "lfs-smudge",
            "submodule-update",
            "_assert_independent_objects",
            "Source manifest changed",
            '"status": "PASS"',
        ),
    )


def _check_permit_and_ownership() -> None:
    _require_markers(
        "packages/runner-protocol/src/visual_engineer_runner_protocol/models.py",
        (
            "class SideEffectPermit(",
            "class SideEffectPermitAcquireRequest(",
            "side_effect_job_binding",
            "SIDE_EFFECT_PERMIT_REQUIRED",
            "WORKSPACE_RECOVERY_REQUIRED",
            "WORKSPACE_QUARANTINED",
        ),
    )
    _require_markers(
        "apps/api/src/visual_engineer_api/services/runner.py",
        (
            "def acquire_side_effect_permit(",
            "in_flight_permits_for_workspace",
            "operation_digest_mismatch",
            "side_effect_permit_expired",
            "revoke_requested",
        ),
    )
    _require_markers(
        "apps/runner/src/visual_engineer_runner/workspace_manager.py",
        (
            "_require_side_effect_permit",
            "pending_permit_id",
            "before_commit=lambda: self._ensure_permit_fresh(permit)",
            "_validate_ownership_record",
            "WorkspaceOwnershipStore",
            "registry_signature_matches",
            "_validate_discard_proof",
            "_require_discarded_inode_absent",
            "WORKSPACE_RECOVERY_REQUIRED",
            "WORKSPACE_QUARANTINED",
            "WorkspaceStatusCode.IGNORED",
        ),
    )
    _require_markers(
        "apps/runner/src/visual_engineer_runner/ownership.py",
        (
            "hmac.new",
            "canonical_json_bytes",
            "workspace-registry-v2",
            "creation_nonce",
            "workspace_device",
            "workspace_inode",
            "WorkspaceDiscardProof",
            "workspace-discard-proof-v1",
            "os.O_NOFOLLOW",
            "st_nlink",
            "0o600",
        ),
    )
    migration = REPOSITORY_ROOT / (
        "apps/api/alembic/versions/20260728_0005_close_phase4_security_findings.py"
    )
    if not migration.is_file():
        raise SystemExit("The reversible Phase 4 security migration is missing")
    _require_markers(
        migration.relative_to(REPOSITORY_ROOT).as_posix(),
        (
            "side_effect_permits",
            "revoke_requested",
            "recovery_required",
            "quarantined",
            "def downgrade()",
        ),
    )


def _check_resources_and_immutable_refs() -> None:
    compose = _read("compose.yaml")
    for marker in (
        "cpus: 1.0",
        "mem_limit: 512m",
        "pids_limit: 128",
        "nofile:",
        "RUNNER_GIT_TIMEOUT_SECONDS",
        "RUNNER_GIT_MAX_OUTPUT_BYTES",
        "RUNNER_MIRROR_MAX_OBJECT_FILES",
        "RUNNER_MIRROR_MAX_OBJECT_BYTES",
        "RUNNER_MIRROR_MAX_SINGLE_OBJECT_BYTES",
        "RUNNER_MIRROR_MAX_DELTA_DEPTH",
        "RUNNER_MIRROR_MAX_TREE_DEPTH",
        "RUNNER_GIT_TERMINATION_GRACE_SECONDS",
    ):
        if marker not in compose:
            raise SystemExit(f"Runner resource boundary is missing: {marker}")
    if "RUNNER_GIT_MIRROR_MAX_OBJECT" in compose:
        raise SystemExit("Compose uses a stale Runner mirror budget environment name")
    for relative_path in ("compose.yaml", ".github/workflows/ci.yml"):
        source = _read(relative_path)
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("image:") and "@sha256:" not in stripped:
                raise SystemExit(f"{relative_path} contains a mutable image reference: {stripped}")
    workflow = _read(".github/workflows/ci.yml")
    for match in re.finditer(r"^\s*uses:\s*([^@\s]+)@([^\s#]+)", workflow, re.MULTILINE):
        action, reference = match.groups()
        if action.startswith("./"):
            continue
        if re.fullmatch(r"[0-9a-f]{40}", reference) is None:
            raise SystemExit(f"CI action is not pinned to a commit SHA: {action}@{reference}")


def _check_regressions() -> None:
    _require_markers(
        "apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py",
        (
            "test_source_local_fsmonitor_is_not_executed",
            "test_source_local_clean_filter_is_not_executed",
            "test_revocation_between_start_and_permit_denies_file_side_effect",
            "test_registry_missing_discard_requires_recovery",
        ),
    )
    _require_markers(
        "apps/runner/tests/test_workspace_tools.py",
        (
            "test_side_effect_permit_is_required_fresh_and_exactly_bound",
            "test_side_effect_permit_expiry_before_atomic_commit_preserves_content",
            "test_registry_and_signed_ownership_fail_closed_on_loss_or_tamper",
            "test_discard_quarantines_unowned_inventory_and_preserves_sibling",
            "test_interrupted_discard_reconciles_only_signed_owned_workspace",
            "test_git_output_and_mirror_object_budgets_fail_closed",
            "test_reachable_packed_delta_closure_is_materialized_without_unreachable_object",
            "test_existing_mirror_rejects_valid_but_unauthorized_object",
            "test_registry_loss_reconciles_only_exact_signed_pending_discard_proof",
            "test_git_deadline_monitors_group_after_pipes_close",
        ),
    )
    _require_markers(
        "apps/api/tests/test_workspace_api.py",
        (
            "test_side_effect_permit_endpoint_rejects_stale_or_wrong_binding_and_replays",
            "test_permit_acquire_and_grant_revoke_serialize_without_deadlock",
            "test_revocation_waits_for_consumed_permit_then_cancel_ack_finalizes",
            "test_expired_lease_cannot_acquire_side_effect_permit",
            "test_concurrent_permit_acquire_has_one_postgresql_consumer",
            "test_real_postgresql_permit_crash_windows_retry_and_disk_db_ordering",
            "test_permit_identity_and_expired_grant_denials_leave_zero_disk_side_effects",
            "test_permit_last_moment_budget_recheck_prevents_disk_write",
        ),
    )


def main() -> None:
    _check_audit_is_preserved()
    _check_source_adapter()
    _check_permit_and_ownership()
    _check_resources_and_immutable_refs()
    _check_regressions()
    print(
        json.dumps(
            {
                "findings_checked": len(FINDINGS),
                "independent_gate": "FAIL_PRESERVED",
                "status": "REPAIR_CONTROLS_PRESENT",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
