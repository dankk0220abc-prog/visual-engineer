import hashlib
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner.evidence import PermissionEnvelopeDeniedError, validate_assignment
from visual_engineer_runner.git_ops import GitOperationError, GitOperations
from visual_engineer_runner.safe_fs import (
    SafeFilesystemError,
    SafeWorkspaceFilesystem,
    parse_relative_path,
)
from visual_engineer_runner.workspace_manager import WorkspaceExecutionError, WorkspaceManager
from visual_engineer_runner_protocol import (
    Capability,
    ExecutionGrantPolicy,
    FailureCode,
    JobAssignment,
    PermissionEnvelope,
    RepositoryAccess,
    ResultPayload,
    SideEffectPermit,
    SourceStatus,
    WorkspaceDiffJobSpec,
    WorkspaceDiffResult,
    WorkspaceDiscardJobSpec,
    WorkspaceDiscardResult,
    WorkspaceJobSpec,
    WorkspaceListJobSpec,
    WorkspaceListResult,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspacePrepareResult,
    WorkspaceReadTextJobSpec,
    WorkspaceReadTextResult,
    WorkspaceRollbackJobSpec,
    WorkspaceRollbackResult,
    WorkspaceStatusJobSpec,
    WorkspaceStatusResult,
    WorkspaceWriteMode,
    WorkspaceWriteTextJobSpec,
    WorkspaceWriteTextResult,
    compute_execution_grant_policy_hash,
    compute_permission_policy_hash,
    compute_side_effect_job_digest,
    compute_side_effect_permit_digest,
    side_effect_job_binding,
)

HANDLE = "fixture-repository-v1"
RUNNER_ID = uuid.UUID("5a2aa04b-6801-52ad-995d-cf4e829b96cb")


def git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def repository_fixture(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@example.invalid")
    sandbox = source / "sandbox"
    sandbox.mkdir()
    (sandbox / "tracked.txt").write_text("original\n", encoding="utf-8")
    (source / "outside.txt").write_text("committed outside scope\n", encoding="utf-8")
    git(source, "add", "sandbox/tracked.txt", "outside.txt")
    git(source, "commit", "-m", "fixture")
    revision = git(source, "rev-parse", "HEAD")
    (sandbox / "tracked.txt").write_text("dirty source content\n", encoding="utf-8")
    (sandbox / "source-untracked.txt").write_text("not committed\n", encoding="utf-8")
    return source, revision


def runner_settings(
    tmp_path: Path,
    source: Path,
    *,
    require_source_read_only: bool = False,
) -> RunnerSettings:
    return RunnerSettings(
        credential_path=tmp_path / "state" / "credential.json",
        repository_handles={
            HANDLE: LocalRepositoryConfig(path=source, display_name="Adversarial Fixture")
        },
        mirror_root=tmp_path / "state" / "mirrors",
        workspace_root=tmp_path / "state" / "workspaces",
        registry_root=tmp_path / "state" / "registry",
        require_source_read_only=require_source_read_only,
    )


def execution_grant(revision: str, **updates: object) -> ExecutionGrantPolicy:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "repository_handle_id": uuid.uuid4(),
        "repository_opaque_handle": HANDLE,
        "source_revision": revision,
        "snapshot_fingerprint": hashlib.sha256(b"snapshot").hexdigest(),
        "allowed_operations": list(WorkspaceOperation),
        "allowed_paths": ["sandbox/**"],
        "denied_paths": [
            ".git",
            ".git/**",
            ".env",
            ".env.*",
            "**/.env",
            "**/.env.*",
            "**/*credential*",
            "**/*secret*",
            "**/*token*",
            "**/*.key",
            "**/*.pem",
        ],
        "max_files_changed": 8,
        "max_total_write_bytes": 128 * 1024,
        "max_single_file_bytes": 32 * 1024,
        "max_diff_bytes": 32 * 1024,
        "workspace_ttl_seconds": 20 * 60,
        "expires_at": datetime.now(UTC) + timedelta(minutes=30),
        "policy_hash": "0" * 64,
    }
    values.update(updates)
    draft = ExecutionGrantPolicy.model_validate(values)
    values["policy_hash"] = compute_execution_grant_policy_hash(draft)
    return ExecutionGrantPolicy.model_validate(values)


def execute(
    manager: WorkspaceManager,
    spec: WorkspaceJobSpec,
    *,
    operation_id: uuid.UUID | None = None,
    cancel_event: threading.Event | None = None,
) -> ResultPayload:
    resolved_operation_id = operation_id or uuid.uuid4()
    permit: SideEffectPermit | None = None
    if isinstance(
        spec,
        (
            WorkspacePrepareJobSpec,
            WorkspaceWriteTextJobSpec,
            WorkspaceRollbackJobSpec,
            WorkspaceDiscardJobSpec,
        ),
    ):
        permit = side_effect_permit(manager, spec, resolved_operation_id)
    return manager.execute(
        spec,
        operation_id=resolved_operation_id,
        cancel_event=cancel_event or threading.Event(),
        side_effect_permit=permit,
    )


def side_effect_permit(
    manager: WorkspaceManager,
    spec: WorkspaceJobSpec,
    operation_id: uuid.UUID,
    *,
    expires_at: datetime | None = None,
    expected_current: str | None = None,
) -> SideEffectPermit:
    binding = side_effect_job_binding(spec)
    resolved_current = expected_current or binding["expected_current"]
    if resolved_current is None:
        registry = manager._load_registry(spec.workspace_id)
        assert registry is not None
        resolved_current = registry.current_tree_hash
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": uuid.uuid5(operation_id, "side-effect-permit"),
        "sequence": 1,
        "runner_id": RUNNER_ID,
        "job_id": operation_id,
        "attempt_id": uuid.uuid5(operation_id, "attempt"),
        "lease_id": uuid.uuid5(operation_id, "lease"),
        "grant_id": spec.execution_grant.id,
        "workspace_id": spec.workspace_id,
        "repository_handle_id": spec.execution_grant.repository_handle_id,
        "operation": binding["operation"],
        "relative_path": binding["relative_path"],
        "expected_current": resolved_current,
        "proposed_digest": binding["proposed_digest"],
        "job_digest": compute_side_effect_job_digest(spec),
        "operation_digest": "0" * 64,
        "policy_hash": spec.execution_grant.policy_hash,
        "source_revision": spec.execution_grant.source_revision,
        "issued_at": now,
        "consumed_at": now,
        "expires_at": expires_at or now + timedelta(minutes=1),
        "state": "consumed",
    }
    values["operation_digest"] = compute_side_effect_permit_digest(values)
    return SideEffectPermit.model_validate(values)


def test_workspace_assignment_requires_exact_isolated_repository_access() -> None:
    grant = execution_grant("a" * 40)
    job = WorkspacePrepareJobSpec(workspace_id=uuid.uuid4(), execution_grant=grant)
    job_id = uuid.uuid4()
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "job_id": job_id,
        "allowed_capabilities": [Capability.WORKSPACE_PREPARE_V1],
        "repository_access": RepositoryAccess.ISOLATED_WORKSPACE,
        "max_runtime_seconds": 30,
        "lease_seconds": 6,
        "max_attempts": 2,
        "max_result_bytes": 64 * 1024,
        "issued_at": now,
        "expires_at": now + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = PermissionEnvelope.model_validate(values)
    values["policy_hash"] = compute_permission_policy_hash(draft)
    envelope = PermissionEnvelope.model_validate(values)
    assignment = JobAssignment(
        job_id=job_id,
        attempt_id=uuid.uuid4(),
        lease_id=uuid.uuid4(),
        attempt_number=1,
        job=job,
        permission_envelope=envelope,
        leased_until=now + timedelta(seconds=6),
    )

    validate_assignment(assignment)

    denied = envelope.model_copy(update={"repository_access": RepositoryAccess.NONE})
    denied = denied.model_copy(update={"policy_hash": compute_permission_policy_hash(denied)})
    with pytest.raises(PermissionEnvelopeDeniedError) as error:
        validate_assignment(assignment.model_copy(update={"permission_envelope": denied}))
    assert error.value.code == "repository_access_denied"


def test_runner_owned_workspace_end_to_end_and_restart_recovery(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()

    registrations = manager.registration_requests(uuid.uuid4())
    assert len(registrations) == 1
    assert registrations[0].source_is_dirty is True
    assert registrations[0].source_status == SourceStatus.UNKNOWN
    assert registrations[0].dirty_path_count == 10_000
    assert str(source) not in registrations[0].model_dump_json()

    prepared = cast(
        WorkspacePrepareResult,
        execute(
            manager,
            WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
        ),
    )
    assert prepared.initial_tree_hash == prepared.current_tree_hash
    workspace = settings.workspace_root / f"workspace-{workspace_id.hex}"
    assert git(workspace, "rev-parse", "HEAD") == revision
    assert git(workspace, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert (workspace / "sandbox" / "tracked.txt").read_text() == "original\n"
    assert not (workspace / "sandbox" / "source-untracked.txt").exists()
    source_status_before = git(source, "status", "--porcelain=v1")

    listed = cast(
        WorkspaceListResult,
        execute(
            manager,
            WorkspaceListJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                relative_directory="sandbox",
                depth=2,
                max_entries=20,
            ),
        ),
    )
    assert [item.relative_path for item in listed.entries] == ["sandbox/tracked.txt"]
    read = cast(
        WorkspaceReadTextResult,
        execute(
            manager,
            WorkspaceReadTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                relative_path="sandbox/tracked.txt",
                max_bytes=1024,
            ),
        ),
    )
    assert read.content == "original\n"

    write_id = uuid.uuid4()
    replaced = execute(
        manager,
        WorkspaceWriteTextJobSpec(
            workspace_id=workspace_id,
            execution_grant=grant,
            mode=WorkspaceWriteMode.REPLACE,
            relative_path="sandbox/tracked.txt",
            content="replacement\n",
            expected_sha256=read.sha256,
        ),
        operation_id=write_id,
    )
    replayed = execute(
        WorkspaceManager(settings),
        WorkspaceWriteTextJobSpec(
            workspace_id=workspace_id,
            execution_grant=grant,
            mode=WorkspaceWriteMode.REPLACE,
            relative_path="sandbox/tracked.txt",
            content="replacement\n",
            expected_sha256=read.sha256,
        ),
        operation_id=write_id,
    )
    assert replayed == replaced
    with pytest.raises(WorkspaceExecutionError) as stale_hash:
        execute(
            manager,
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content="stale\n",
                expected_sha256=read.sha256,
            ),
        )
    assert stale_hash.value.code == FailureCode.CONTENT_CONFLICT

    execute(
        manager,
        WorkspaceWriteTextJobSpec(
            workspace_id=workspace_id,
            execution_grant=grant,
            mode=WorkspaceWriteMode.CREATE,
            relative_path="sandbox/created.txt",
            content="created\n",
            expected_absent=True,
        ),
    )
    status = cast(
        WorkspaceStatusResult,
        execute(
            manager,
            WorkspaceStatusJobSpec(workspace_id=workspace_id, execution_grant=grant),
        ),
    )
    assert {item.relative_path for item in status.entries} == {
        "sandbox/created.txt",
        "sandbox/tracked.txt",
    }
    diff = cast(
        WorkspaceDiffResult,
        execute(
            manager,
            WorkspaceDiffJobSpec(workspace_id=workspace_id, execution_grant=grant),
        ),
    )
    assert "replacement" in diff.diff
    assert "created" in diff.diff
    assert diff.diff_hash == hashlib.sha256(diff.diff.encode()).hexdigest()

    rollback = cast(
        WorkspaceRollbackResult,
        execute(
            manager,
            WorkspaceRollbackJobSpec(workspace_id=workspace_id, execution_grant=grant),
        ),
    )
    assert rollback.clean is True
    assert (workspace / "sandbox" / "tracked.txt").read_text() == "original\n"
    assert not (workspace / "sandbox" / "created.txt").exists()
    assert git(workspace, "status", "--porcelain=v1") == ""

    second_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=second_id, execution_grant=grant),
    )
    second_workspace = settings.workspace_root / f"workspace-{second_id.hex}"
    discarded = cast(
        WorkspaceDiscardResult,
        execute(
            manager,
            WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant),
        ),
    )
    assert discarded.discarded is True
    assert not workspace.exists()
    assert second_workspace.is_dir()
    assert git(source, "status", "--porcelain=v1") == source_status_before
    assert git(source, "rev-parse", "HEAD") == revision


def test_interrupted_write_recovery_cleans_temp_and_reconciles_commit(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    workspace = settings.workspace_root / f"workspace-{workspace_id.hex}"
    operation_id = uuid.uuid4()
    desired = "recovered\n"
    desired_sha256 = hashlib.sha256(desired.encode()).hexdigest()
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    registry.pending_operation = {
        "operation_id": str(operation_id),
        "relative_path": "sandbox/tracked.txt",
        "mode": "replace",
        "desired_sha256": desired_sha256,
        "size": len(desired.encode()),
    }
    manager._save_registry(registry)
    interrupted_temp = workspace / "sandbox" / f".visual-engineer-write-{operation_id.hex}.tmp"
    interrupted_temp.write_text("partial", encoding="utf-8")

    recovered = cast(
        WorkspaceWriteTextResult,
        execute(
            WorkspaceManager(settings),
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content=desired,
                expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
            ),
            operation_id=operation_id,
        ),
    )
    assert recovered.sha256 == desired_sha256
    assert not interrupted_temp.exists()

    committed_operation = uuid.uuid4()
    committed = "committed before lease loss\n"
    committed_sha256 = hashlib.sha256(committed.encode()).hexdigest()
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    registry.pending_operation = {
        "operation_id": str(committed_operation),
        "relative_path": "sandbox/tracked.txt",
        "mode": "replace",
        "desired_sha256": committed_sha256,
        "size": len(committed.encode()),
    }
    manager._save_registry(registry)
    (workspace / "sandbox" / "tracked.txt").write_text(committed, encoding="utf-8")
    reconciled = cast(
        WorkspaceWriteTextResult,
        execute(
            WorkspaceManager(settings),
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content=committed,
                expected_sha256=desired_sha256,
            ),
            operation_id=committed_operation,
        ),
    )
    assert reconciled.sha256 == committed_sha256
    assert git(workspace, "status", "--porcelain=v1") == "M sandbox/tracked.txt"


def test_registry_evicts_old_results_before_its_read_limit(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    content = "x" * (32 * 1024)
    final_operation_id = uuid.uuid4()
    for index in range(40):
        operation_id = final_operation_id if index == 39 else uuid.uuid4()
        manager._cache_result(
            registry,
            operation_id,
            WorkspaceReadTextResult(
                workspace_id=workspace_id,
                relative_path="sandbox/tracked.txt",
                content=content,
                sha256=hashlib.sha256(content.encode()).hexdigest(),
                size=len(content.encode()),
            ),
        )

    registry_path = settings.registry_root / f"workspace-{workspace_id.hex}.json"
    assert registry_path.stat().st_size <= 1024 * 1024
    reloaded = WorkspaceManager(settings)._load_registry(workspace_id)
    assert reloaded is not None
    assert str(final_operation_id) in reloaded.completed_operations
    assert len(reloaded.completed_operations) < 40


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("", FailureCode.PATH_INVALID),
        ("/absolute", FailureCode.PATH_INVALID),
        ("sandbox/../outside", FailureCode.PATH_INVALID),
        ("sandbox/\x00bad", FailureCode.PATH_INVALID),
        ("sandbox/" + "a/" * 33 + "file", FailureCode.PATH_INVALID),
        ("sandbox/" + "a" * 600, FailureCode.PATH_INVALID),
    ],
)
def test_relative_path_parser_rejects_unsafe_values(value: str, code: FailureCode) -> None:
    with pytest.raises(SafeFilesystemError) as error:
        parse_relative_path(value)
    assert error.value.code == code


@pytest.mark.parametrize(
    "relative_path",
    [
        ".git/config",
        "sandbox/.git/config",
        "sandbox/.env",
        "sandbox/.env.local",
        "sandbox/service-token.txt",
        "sandbox/client.pem",
        "outside.txt",
    ],
)
def test_policy_denies_git_sensitive_and_out_of_scope_paths(
    tmp_path: Path,
    relative_path: str,
) -> None:
    root = tmp_path / "workspace"
    (root / "sandbox").mkdir(parents=True)
    filesystem = SafeWorkspaceFilesystem(root, execution_grant("a" * 40))
    with pytest.raises(SafeFilesystemError):
        filesystem.authorize(relative_path)


def test_safe_filesystem_rejects_links_special_binary_and_races(tmp_path: Path) -> None:
    root = Path(tempfile.mkdtemp(prefix="ve-fs-", dir="/tmp"))
    sandbox = root / "sandbox"
    sandbox.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n")
    (sandbox / "text.txt").write_text("before\n")
    (sandbox / "binary.bin").write_bytes(b"\x00binary")
    (sandbox / "invalid.txt").write_bytes(b"\xff")
    os.symlink(outside, sandbox / "leaf-link")
    os.symlink(tmp_path, sandbox / "directory-link")
    os.link(sandbox / "text.txt", sandbox / "hard-link")
    fifo = sandbox / "pipe"
    os.mkfifo(fifo)
    unix_socket = socket.socket(socket.AF_UNIX)
    unix_socket.bind(str(sandbox / "socket"))

    try:
        filesystem = SafeWorkspaceFilesystem(root, execution_grant("a" * 40))
        expected_codes = {
            "sandbox/leaf-link": FailureCode.SYMLINK_DENIED,
            "sandbox/directory-link/child": FailureCode.SYMLINK_DENIED,
            "sandbox/hard-link": FailureCode.HARDLINK_DENIED,
            "sandbox/pipe": FailureCode.NOT_REGULAR_FILE,
            "sandbox/socket": FailureCode.NOT_REGULAR_FILE,
            "sandbox/binary.bin": FailureCode.BINARY_DENIED,
            "sandbox/invalid.txt": FailureCode.INVALID_UTF8,
        }
        for path, code in expected_codes.items():
            with pytest.raises(SafeFilesystemError) as error:
                filesystem.read_text(path, 1024)
            assert error.value.code == code
        os.unlink(sandbox / "hard-link")

        def race_create() -> None:
            os.symlink(outside, sandbox / "create-race.txt")

        with pytest.raises(SafeFilesystemError) as create_error:
            filesystem.write_text(
                "sandbox/create-race.txt",
                "safe\n",
                mode=WorkspaceWriteMode.CREATE,
                expected_sha256=None,
                before_commit=race_create,
            )
        assert create_error.value.code == FailureCode.EXPECTED_ABSENT_CONFLICT
        assert outside.read_text() == "outside\n"

        original_hash = hashlib.sha256(b"before\n").hexdigest()

        def race_replace() -> None:
            os.unlink(sandbox / "text.txt")
            os.symlink(outside, sandbox / "text.txt")

        with pytest.raises(SafeFilesystemError) as replace_error:
            filesystem.write_text(
                "sandbox/text.txt",
                "after\n",
                mode=WorkspaceWriteMode.REPLACE,
                expected_sha256=original_hash,
                before_commit=race_replace,
            )
        assert replace_error.value.code == FailureCode.CONTENT_CONFLICT
        assert outside.read_text() == "outside\n"
        assert not list(sandbox.glob(".visual-engineer-write-*.tmp"))
    finally:
        unix_socket.close()
        shutil.rmtree(root)


def test_cancel_during_atomic_write_leaves_original_complete(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    sandbox = root / "sandbox"
    sandbox.mkdir(parents=True)
    target = sandbox / "target.txt"
    target.write_text("before\n")
    cancel = threading.Event()
    filesystem = SafeWorkspaceFilesystem(
        root,
        execution_grant("a" * 40),
        cancel_event=cancel,
        commit_delay_ms=200,
    )
    timer = threading.Timer(0.02, cancel.set)
    timer.start()
    try:
        with pytest.raises(SafeFilesystemError) as error:
            filesystem.write_text(
                "sandbox/target.txt",
                "after\n",
                mode=WorkspaceWriteMode.REPLACE,
                expected_sha256=hashlib.sha256(b"before\n").hexdigest(),
            )
    finally:
        timer.cancel()
    assert error.value.code == FailureCode.WORKSPACE_CANCELLED
    assert target.read_text() == "before\n"
    assert not list(sandbox.glob(".visual-engineer-write-*.tmp"))


def test_source_read_only_verification_fails_closed(tmp_path: Path) -> None:
    source, _ = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source, require_source_read_only=True)
    operations = GitOperations(settings)
    with pytest.raises(GitOperationError) as error:
        operations.inspect_source(settings.repository_handles[HANDLE])
    assert error.value.code == FailureCode.SOURCE_NOT_READ_ONLY


def test_source_loose_ref_symlink_cannot_fall_back_to_packed_ref(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    git(source, "pack-refs", "--all")
    loose_ref = source / ".git" / "refs" / "heads" / "main"
    loose_ref.parent.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside-ref"
    outside.write_text(f"{revision}\n", encoding="ascii")
    os.symlink(outside, loose_ref)
    settings = runner_settings(tmp_path, source)

    with pytest.raises(GitOperationError) as error:
        GitOperations(settings).inspect_source(settings.repository_handles[HANDLE])
    assert error.value.code == FailureCode.REPOSITORY_UNAVAILABLE
    assert outside.read_text(encoding="ascii") == f"{revision}\n"


def test_source_loose_ref_parent_symlink_is_rejected(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    git(source, "pack-refs", "--all")
    refs = source / ".git" / "refs"
    shutil.rmtree(refs)
    outside = tmp_path / "outside-refs"
    outside_head = outside / "heads" / "main"
    outside_head.parent.mkdir(parents=True)
    outside_head.write_text(f"{revision}\n", encoding="ascii")
    os.symlink(outside, refs)
    settings = runner_settings(tmp_path, source)

    with pytest.raises(GitOperationError) as error:
        GitOperations(settings).inspect_source(settings.repository_handles[HANDLE])
    assert error.value.code == FailureCode.REPOSITORY_UNAVAILABLE
    assert outside_head.read_text(encoding="ascii") == f"{revision}\n"


def test_grant_hash_expiry_and_write_budgets_are_enforced(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    workspace_id = uuid.uuid4()

    tampered = execution_grant(revision).model_copy(update={"policy_hash": "f" * 64})
    with pytest.raises(WorkspaceExecutionError) as hash_error:
        execute(
            manager,
            WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=tampered),
        )
    assert hash_error.value.code == FailureCode.ENVELOPE_HASH_MISMATCH

    expired = execution_grant(
        revision,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    with pytest.raises(WorkspaceExecutionError) as expiry_error:
        execute(
            manager,
            WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=expired),
        )
    assert expiry_error.value.code == FailureCode.ENVELOPE_EXPIRED

    grant = execution_grant(revision, max_total_write_bytes=10, max_single_file_bytes=10)
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    first = cast(
        WorkspaceWriteTextResult,
        execute(
            manager,
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content="123456",
                expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
            ),
        ),
    )
    with pytest.raises(WorkspaceExecutionError) as total_budget:
        execute(
            manager,
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content="12345",
                expected_sha256=first.sha256,
            ),
        )
    assert total_budget.value.code == FailureCode.TOTAL_WRITE_BUDGET_EXCEEDED

    file_count_workspace = uuid.uuid4()
    file_count_grant = execution_grant(revision, max_files_changed=1)
    execute(
        manager,
        WorkspacePrepareJobSpec(
            workspace_id=file_count_workspace,
            execution_grant=file_count_grant,
        ),
    )
    execute(
        manager,
        WorkspaceWriteTextJobSpec(
            workspace_id=file_count_workspace,
            execution_grant=file_count_grant,
            mode=WorkspaceWriteMode.CREATE,
            relative_path="sandbox/created.txt",
            content="created\n",
            expected_absent=True,
        ),
    )
    with pytest.raises(WorkspaceExecutionError) as file_count_budget:
        execute(
            manager,
            WorkspaceWriteTextJobSpec(
                workspace_id=file_count_workspace,
                execution_grant=file_count_grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content="changed\n",
                expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
            ),
        )
    assert file_count_budget.value.code == FailureCode.FILE_COUNT_BUDGET_EXCEEDED

    diff_workspace = uuid.uuid4()
    diff_grant = execution_grant(revision, max_diff_bytes=1)
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=diff_workspace, execution_grant=diff_grant),
    )
    with pytest.raises(WorkspaceExecutionError) as diff_budget:
        execute(
            manager,
            WorkspaceWriteTextJobSpec(
                workspace_id=diff_workspace,
                execution_grant=diff_grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content="changed\n",
                expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
            ),
        )
    assert diff_budget.value.code == FailureCode.DIFF_BUDGET_EXCEEDED


def test_side_effect_permit_is_required_fresh_and_exactly_bound(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    prepare = WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant)
    prepare_operation_id = uuid.uuid4()

    with pytest.raises(WorkspaceExecutionError) as missing:
        manager.execute(
            prepare,
            operation_id=prepare_operation_id,
            cancel_event=threading.Event(),
        )
    assert missing.value.code == FailureCode.SIDE_EFFECT_PERMIT_REQUIRED
    assert not manager._git.workspace_path(workspace_id).exists()

    valid_prepare_permit = side_effect_permit(manager, prepare, prepare_operation_id)
    tampered_expiry_permit = valid_prepare_permit.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(milliseconds=1)}
    )
    with pytest.raises(WorkspaceExecutionError) as tampered_expiry:
        manager.execute(
            prepare,
            operation_id=prepare_operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=tampered_expiry_permit,
        )
    assert tampered_expiry.value.code == FailureCode.SIDE_EFFECT_PERMIT_INVALID
    assert not manager._git.workspace_path(workspace_id).exists()

    expired_values = valid_prepare_permit.model_dump(mode="python")
    expired_values.update(
        issued_at=datetime.now(UTC) - timedelta(seconds=2),
        consumed_at=datetime.now(UTC) - timedelta(seconds=2),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        operation_digest="0" * 64,
    )
    expired_values["operation_digest"] = compute_side_effect_permit_digest(expired_values)
    expired_prepare_permit = SideEffectPermit.model_validate(expired_values)
    with pytest.raises(WorkspaceExecutionError) as expired:
        manager.execute(
            prepare,
            operation_id=prepare_operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=expired_prepare_permit,
        )
    assert expired.value.code == FailureCode.SIDE_EFFECT_PERMIT_EXPIRED
    assert not manager._git.workspace_path(workspace_id).exists()

    wrong_job_permit = valid_prepare_permit.model_copy(update={"job_id": uuid.uuid4()})
    with pytest.raises(WorkspaceExecutionError) as wrong_job:
        manager.execute(
            prepare,
            operation_id=prepare_operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=wrong_job_permit,
        )
    assert wrong_job.value.code == FailureCode.SIDE_EFFECT_PERMIT_INVALID
    assert not manager._git.workspace_path(workspace_id).exists()

    manager.execute(
        prepare,
        operation_id=prepare_operation_id,
        cancel_event=threading.Event(),
        side_effect_permit=valid_prepare_permit,
    )
    target = manager._git.workspace_path(workspace_id) / "sandbox" / "tracked.txt"
    write = WorkspaceWriteTextJobSpec(
        workspace_id=workspace_id,
        execution_grant=grant,
        mode=WorkspaceWriteMode.REPLACE,
        relative_path="sandbox/tracked.txt",
        content="permitted\n",
        expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
    )
    write_operation_id = uuid.uuid4()
    valid_write_permit = side_effect_permit(manager, write, write_operation_id)
    wrong_content_permit = valid_write_permit.model_copy(
        update={"proposed_digest": hashlib.sha256(b"different content").hexdigest()}
    )
    with pytest.raises(WorkspaceExecutionError) as wrong_content:
        manager.execute(
            write,
            operation_id=write_operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=wrong_content_permit,
        )
    assert wrong_content.value.code == FailureCode.SIDE_EFFECT_PERMIT_INVALID
    assert target.read_text() == "original\n"

    first = manager.execute(
        write,
        operation_id=write_operation_id,
        cancel_event=threading.Event(),
        side_effect_permit=valid_write_permit,
    )
    replay = manager.execute(
        write,
        operation_id=write_operation_id,
        cancel_event=threading.Event(),
        side_effect_permit=valid_write_permit,
    )
    assert replay == first
    assert target.read_text() == "permitted\n"


def test_side_effect_permit_expiry_before_atomic_commit_preserves_content(
    tmp_path: Path,
) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source).model_copy(
        update={"workspace_write_commit_delay_ms": 60}
    )
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    target = manager._git.workspace_path(workspace_id) / "sandbox" / "tracked.txt"
    write = WorkspaceWriteTextJobSpec(
        workspace_id=workspace_id,
        execution_grant=grant,
        mode=WorkspaceWriteMode.REPLACE,
        relative_path="sandbox/tracked.txt",
        content="must not commit\n",
        expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
    )
    operation_id = uuid.uuid4()
    permit = side_effect_permit(
        manager,
        write,
        operation_id,
        expires_at=datetime.now(UTC) + timedelta(milliseconds=10),
    )
    with pytest.raises(WorkspaceExecutionError) as expired:
        manager.execute(
            write,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        )
    assert expired.value.code == FailureCode.SIDE_EFFECT_PERMIT_EXPIRED
    assert target.read_text() == "original\n"
    assert not list(target.parent.glob(".visual-engineer-write-*.tmp"))


def test_registry_and_signed_ownership_fail_closed_on_loss_or_tamper(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)

    def prepare_workspace() -> tuple[uuid.UUID, WorkspaceStatusJobSpec]:
        workspace_id = uuid.uuid4()
        execute(
            manager,
            WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )
        return (
            workspace_id,
            WorkspaceStatusJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )

    missing_manifest_id, missing_manifest_status = prepare_workspace()
    manager._ownership.path(missing_manifest_id).unlink()
    with pytest.raises(WorkspaceExecutionError) as missing_manifest:
        execute(manager, missing_manifest_status)
    assert missing_manifest.value.code == FailureCode.WORKSPACE_RECOVERY_REQUIRED

    tampered_manifest_id, tampered_manifest_status = prepare_workspace()
    manifest_path = manager._ownership.path(tampered_manifest_id)
    manifest_path.write_text("{}", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    with pytest.raises(WorkspaceExecutionError) as tampered_manifest:
        execute(manager, tampered_manifest_status)
    assert tampered_manifest.value.code == FailureCode.WORKSPACE_QUARANTINED

    unsafe_mode_id, unsafe_mode_status = prepare_workspace()
    os.chmod(manager._ownership.path(unsafe_mode_id), 0o644)
    with pytest.raises(WorkspaceExecutionError) as unsafe_mode:
        execute(manager, unsafe_mode_status)
    assert unsafe_mode.value.code == FailureCode.WORKSPACE_QUARANTINED

    corrupt_registry_id, corrupt_registry_status = prepare_workspace()
    registry_path = manager._registry_path(corrupt_registry_id)
    registry_path.write_text("{", encoding="utf-8")
    os.chmod(registry_path, 0o600)
    with pytest.raises(WorkspaceExecutionError) as corrupt_registry:
        execute(manager, corrupt_registry_status)
    assert corrupt_registry.value.code == FailureCode.WORKSPACE_QUARANTINED

    valid_tamper_id, valid_tamper_status = prepare_workspace()
    valid_tamper_registry = manager._load_registry(valid_tamper_id)
    assert valid_tamper_registry is not None
    valid_tamper_registry.created_paths = ["sandbox/forged-owned-path.txt"]
    manager._registry_path(valid_tamper_id).write_text(
        valid_tamper_registry.model_dump_json(),
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceExecutionError) as valid_tamper:
        execute(manager, valid_tamper_status)
    assert valid_tamper.value.code == FailureCode.WORKSPACE_QUARANTINED

    wrong_inode_id, wrong_inode_status = prepare_workspace()
    wrong_inode_workspace = manager._git.workspace_path(wrong_inode_id)
    moved_workspace = wrong_inode_workspace.with_name(f"{wrong_inode_workspace.name}-moved")
    wrong_inode_workspace.rename(moved_workspace)
    wrong_inode_workspace.mkdir(mode=0o700)
    with pytest.raises(WorkspaceExecutionError) as wrong_inode:
        execute(manager, wrong_inode_status)
    assert wrong_inode.value.code == FailureCode.WORKSPACE_IDENTITY_MISMATCH
    assert moved_workspace.is_dir()

    missing_root_id, _ = prepare_workspace()
    missing_root_workspace = manager._git.workspace_path(missing_root_id)
    preserved_workspace = missing_root_workspace.with_name(
        f"{missing_root_workspace.name}-preserved"
    )
    missing_root_workspace.rename(preserved_workspace)
    with pytest.raises(WorkspaceExecutionError) as missing_root:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=missing_root_id,
                execution_grant=grant,
            ),
        )
    assert missing_root.value.code == FailureCode.WORKSPACE_RECOVERY_REQUIRED
    assert preserved_workspace.is_dir()


@pytest.mark.parametrize("inventory_kind", ["ignored", "unknown"])
def test_discard_quarantines_unowned_inventory_and_preserves_sibling(
    tmp_path: Path,
    inventory_kind: str,
) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    sibling_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=sibling_id, execution_grant=grant),
    )
    workspace = manager._git.workspace_path(workspace_id)
    sibling = manager._git.workspace_path(sibling_id)
    unknown = workspace / "sandbox" / "runner-unknown.txt"
    unknown.write_text("must be preserved\n", encoding="utf-8")
    if inventory_kind == "ignored":
        mirror = manager._git.mirror_path(HANDLE)
        (mirror / "info").mkdir()
        (mirror / "info" / "exclude").write_text(
            "sandbox/runner-unknown.txt\n",
            encoding="utf-8",
        )

    with pytest.raises(WorkspaceExecutionError) as discard:
        execute(
            manager,
            WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )
    assert discard.value.code == FailureCode.WORKSPACE_QUARANTINED
    assert unknown.read_text() == "must be preserved\n"
    assert workspace.is_dir()
    assert sibling.is_dir()


def test_interrupted_discard_reconciles_only_signed_owned_workspace(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    sibling_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=sibling_id, execution_grant=grant),
    )
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    operation_id = uuid.uuid4()
    permit = side_effect_permit(manager, spec, operation_id)
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    registry.pending_operation = {
        "operation_id": str(operation_id),
        "kind": "discard",
    }
    registry.pending_permit_id = permit.id
    manager._create_discard_proof(
        spec,
        registry,
        operation_id=operation_id,
        permit=permit,
    )
    manager._save_registry(registry)
    workspace = manager._git.workspace_path(workspace_id)
    manager._git.discard_worktree(
        manager._git.mirror_path(HANDLE),
        workspace,
        permit_expires_at=permit.expires_at,
    )

    recovered = cast(
        WorkspaceDiscardResult,
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        ),
    )
    assert recovered.discarded is True
    assert recovered.idempotent is True
    assert not workspace.exists()
    assert manager._git.workspace_path(sibling_id).is_dir()
    recovered_registry = manager._load_registry(workspace_id)
    assert recovered_registry is not None
    assert recovered_registry.local_state == "discarded"
    assert recovered_registry.pending_operation is None
    recovered_proof = manager._ownership.load_discard_proof(workspace_id)
    assert recovered_proof is not None
    assert recovered_proof.state == "completed"


def test_git_output_and_mirror_object_budgets_fail_closed(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    output_settings = runner_settings(tmp_path, source).model_copy(
        update={"git_max_output_bytes": 4096}
    )
    output_manager = WorkspaceManager(output_settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    execute(
        output_manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    sandbox = output_manager._git.workspace_path(workspace_id) / "sandbox"
    for index in range(80):
        (sandbox / f"{index:03d}-{'x' * 80}.txt").write_text("bounded\n", encoding="utf-8")
    with pytest.raises(GitOperationError) as output_limit:
        output_manager._git.status(
            output_manager._git.workspace_path(workspace_id),
            revision,
        )
    assert output_limit.value.code == FailureCode.GIT_OUTPUT_LIMIT_EXCEEDED

    random_object = source / "large-object.bin"
    random_object.write_bytes(os.urandom(32 * 1024))
    git(source, "add", "large-object.bin")
    git(source, "commit", "-m", "large synthetic object")
    large_revision = git(source, "rev-parse", "HEAD")
    source_before_budget_rejections = _filesystem_snapshot(source)
    mirror_settings = runner_settings(tmp_path / "mirror-budget", source).model_copy(
        update={"mirror_max_object_bytes": 1024}
    )
    mirror_manager = WorkspaceManager(mirror_settings)
    mirror_workspace_id = uuid.uuid4()
    with pytest.raises(WorkspaceExecutionError) as mirror_limit:
        execute(
            mirror_manager,
            WorkspacePrepareJobSpec(
                workspace_id=mirror_workspace_id,
                execution_grant=execution_grant(large_revision),
            ),
        )
    assert mirror_limit.value.code == FailureCode.MIRROR_BUDGET_EXCEEDED
    assert not mirror_manager._git.workspace_path(mirror_workspace_id).exists()
    assert mirror_manager._load_registry(mirror_workspace_id) is None

    count_settings = runner_settings(tmp_path / "mirror-count-budget", source).model_copy(
        update={"mirror_max_object_files": 2}
    )
    count_manager = WorkspaceManager(count_settings)
    with pytest.raises(WorkspaceExecutionError) as count_limit:
        execute(
            count_manager,
            WorkspacePrepareJobSpec(
                workspace_id=uuid.uuid4(),
                execution_grant=execution_grant(large_revision),
            ),
        )
    assert count_limit.value.code == FailureCode.MIRROR_BUDGET_EXCEEDED

    single_settings = runner_settings(tmp_path / "mirror-single-budget", source).model_copy(
        update={"mirror_max_single_object_bytes": 1024}
    )
    single_manager = WorkspaceManager(single_settings)
    with pytest.raises(WorkspaceExecutionError) as single_limit:
        execute(
            single_manager,
            WorkspacePrepareJobSpec(
                workspace_id=uuid.uuid4(),
                execution_grant=execution_grant(large_revision),
            ),
        )
    assert single_limit.value.code == FailureCode.MIRROR_BUDGET_EXCEEDED
    assert _filesystem_snapshot(source) == source_before_budget_rejections

    pack_directory = source / ".git" / "objects" / "pack"
    pack_directory.mkdir(exist_ok=True)
    for index in range(6):
        (pack_directory / f"pack-{index:040x}.keep").write_bytes(b"")
    source_before_pack_budget = _filesystem_snapshot(source)
    pack_settings = runner_settings(tmp_path / "mirror-pack-budget", source).model_copy(
        update={"mirror_max_pack_files": 1}
    )
    pack_manager = WorkspaceManager(pack_settings)
    with pytest.raises(WorkspaceExecutionError) as pack_limit:
        execute(
            pack_manager,
            WorkspacePrepareJobSpec(
                workspace_id=uuid.uuid4(),
                execution_grant=execution_grant(large_revision),
            ),
        )
    assert pack_limit.value.code == FailureCode.MIRROR_BUDGET_EXCEEDED
    assert _filesystem_snapshot(source) == source_before_pack_budget


def test_reachable_packed_delta_closure_is_materialized_without_unreachable_object(
    tmp_path: Path,
) -> None:
    source, _ = repository_fixture(tmp_path)
    git(source, "restore", "sandbox/tracked.txt")
    delta_file = source / "sandbox" / "delta.txt"
    for index in range(8):
        delta_file.write_text(
            ("shared-prefix-" * 4096) + f"\nversion-{index}\n",
            encoding="utf-8",
        )
        git(source, "add", "sandbox/delta.txt")
        git(source, "commit", "-m", f"delta fixture {index}")
    revision = git(source, "rev-parse", "HEAD")
    unauthorized_file = source / "unreachable-packed.txt"
    unauthorized_file.write_text("not authorized by the approved revision\n", encoding="utf-8")
    unauthorized_blob = git(source, "hash-object", "-w", "unreachable-packed.txt")
    unauthorized_tree = subprocess.run(
        ["git", "-C", str(source), "mktree"],
        input=f"100644 blob {unauthorized_blob}\textra-ref-only.txt\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    unauthorized_commit = subprocess.run(
        ["git", "-C", str(source), "commit-tree", unauthorized_tree, "-m", "unauthorized ref"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    git(source, "update-ref", "refs/heads/not-authorized", unauthorized_commit)
    authorized_ids = set(
        git(source, "rev-list", "--objects", "--no-object-names", revision).splitlines()
    )
    object_ids = git(source, "rev-list", "--objects", "--no-object-names", "--all").splitlines()
    assert {unauthorized_blob, unauthorized_tree, unauthorized_commit}.isdisjoint(authorized_ids)
    pack_prefix = source / ".git" / "objects" / "pack" / "pack"
    packed = subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "pack-objects",
            "--window=50",
            "--depth=50",
            str(pack_prefix),
        ],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    index_path = pack_prefix.with_name(f"pack-{packed}.idx")
    verify_output = git(source, "verify-pack", "-v", str(index_path))
    assert any(len(line.split()) >= 7 for line in verify_output.splitlines())
    for object_id in object_ids:
        loose = source / ".git" / "objects" / object_id[:2] / object_id[2:]
        try:
            loose.unlink()
        except FileNotFoundError:
            pass
    (source / "sandbox" / "tracked.txt").write_text("dirty after pack\n", encoding="utf-8")
    (source / "sandbox" / "untracked-after-pack.txt").write_text(
        "not in the object graph\n",
        encoding="utf-8",
    )
    before = _filesystem_snapshot(source)

    manager = WorkspaceManager(runner_settings(tmp_path, source))
    workspace_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(
            workspace_id=workspace_id,
            execution_grant=execution_grant(revision),
        ),
    )

    mirror = manager._git.mirror_path(HANDLE)
    mirror_ids = {
        directory.name + object_file.name
        for directory in (mirror / "objects").iterdir()
        if len(directory.name) == 2
        for object_file in directory.iterdir()
    }
    assert mirror_ids == authorized_ids
    for unauthorized_id in (
        unauthorized_blob,
        unauthorized_tree,
        unauthorized_commit,
    ):
        assert not (mirror / "objects" / unauthorized_id[:2] / unauthorized_id[2:]).exists()
    assert not any((mirror / "objects" / "pack").iterdir())
    assert not (manager._git.workspace_path(workspace_id) / "unreachable-packed.txt").exists()
    assert not (
        manager._git.workspace_path(workspace_id) / "sandbox" / "untracked-after-pack.txt"
    ).exists()
    assert _filesystem_snapshot(source) == before


def test_existing_mirror_rejects_valid_but_unauthorized_object_and_preserves_source(
    tmp_path: Path,
) -> None:
    source, revision = repository_fixture(tmp_path)
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    grant = execution_grant(revision)
    first_workspace = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=first_workspace, execution_grant=grant),
    )
    unauthorized = source / "unauthorized-object.txt"
    unauthorized.write_text("valid object outside the closure\n", encoding="utf-8")
    unauthorized_id = git(source, "hash-object", "-w", "unauthorized-object.txt")
    source_object = source / ".git" / "objects" / unauthorized_id[:2] / unauthorized_id[2:]
    destination_object = (
        manager._git.mirror_path(HANDLE) / "objects" / unauthorized_id[:2] / unauthorized_id[2:]
    )
    destination_object.parent.mkdir(mode=0o700, exist_ok=True)
    shutil.copyfile(source_object, destination_object)
    source_inode = source_object.stat().st_ino
    assert destination_object.stat().st_ino != source_inode
    before = _filesystem_snapshot(source)
    second_workspace = uuid.uuid4()

    with pytest.raises(WorkspaceExecutionError) as error:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=second_workspace,
                execution_grant=grant,
            ),
        )

    assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
    assert manager._git.workspace_path(first_workspace).is_dir()
    assert not manager._git.workspace_path(second_workspace).exists()
    assert _filesystem_snapshot(source) == before


def test_existing_mirror_config_is_validated_before_any_rewrite(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    grant = execution_grant(revision)
    first_workspace = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=first_workspace, execution_grant=grant),
    )
    config = manager._git.mirror_path(HANDLE) / "config"
    malicious = config.read_bytes() + b"[include]\n\tpath = /untrusted/config\n"
    config.write_bytes(malicious)
    source_before = _filesystem_snapshot(source)

    with pytest.raises(WorkspaceExecutionError) as error:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=uuid.uuid4(),
                execution_grant=grant,
            ),
        )

    assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
    assert config.read_bytes() == malicious
    assert manager._git.workspace_path(first_workspace).is_dir()
    assert _filesystem_snapshot(source) == source_before


@pytest.mark.parametrize(
    "reference_template",
    [
        "refs/replace/{approved_revision}",
        "refs/heads/unapproved",
    ],
)
def test_existing_mirror_rejects_every_loose_ref_and_preserves_source(
    tmp_path: Path,
    reference_template: str,
) -> None:
    source, replaced_revision = repository_fixture(tmp_path)
    tracked = source / "sandbox" / "tracked.txt"
    tracked.write_text("approved second revision\n", encoding="utf-8")
    git(source, "add", "sandbox/tracked.txt")
    git(source, "commit", "-m", "approved second revision")
    approved_revision = git(source, "rev-parse", "HEAD")
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    grant = execution_grant(approved_revision)
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=uuid.uuid4(), execution_grant=grant),
    )
    reference = reference_template.format(approved_revision=approved_revision)
    destination = manager._git.mirror_path(HANDLE) / reference
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(replaced_revision + "\n", encoding="ascii")
    source_before = _filesystem_snapshot(source)
    rejected_workspace_id = uuid.uuid4()

    with pytest.raises(WorkspaceExecutionError) as error:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=rejected_workspace_id,
                execution_grant=grant,
            ),
        )

    assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
    assert not manager._git.workspace_path(rejected_workspace_id).exists()
    assert destination.read_text(encoding="ascii") == replaced_revision + "\n"
    assert _filesystem_snapshot(source) == source_before


def test_source_packed_replacement_metadata_is_not_imported_into_mirror(
    tmp_path: Path,
) -> None:
    source, replaced_revision = repository_fixture(tmp_path)
    tracked = source / "sandbox" / "tracked.txt"
    tracked.write_text("approved second revision\n", encoding="utf-8")
    git(source, "add", "sandbox/tracked.txt")
    git(source, "commit", "-m", "approved second revision")
    approved_revision = git(source, "rev-parse", "HEAD")
    (source / ".git" / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted \n"
        f"{replaced_revision} refs/replace/{approved_revision}\n",
        encoding="ascii",
    )
    source_before = _filesystem_snapshot(source)
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    workspace_id = uuid.uuid4()

    execute(
        manager,
        WorkspacePrepareJobSpec(
            workspace_id=workspace_id,
            execution_grant=execution_grant(approved_revision),
        ),
    )

    mirror = manager._git.mirror_path(HANDLE)
    assert (mirror / "HEAD").read_text(encoding="ascii") == approved_revision + "\n"
    assert not (mirror / "packed-refs").exists()
    assert not any(path.is_file() or path.is_symlink() for path in (mirror / "refs").rglob("*"))
    assert (manager._git.workspace_path(workspace_id) / "sandbox" / "tracked.txt").read_text(
        encoding="utf-8"
    ) == "approved second revision\n"
    assert _filesystem_snapshot(source) == source_before


def test_runner_git_subprocess_does_not_interpret_loose_replacement_ref(
    tmp_path: Path,
) -> None:
    source, replaced_revision = repository_fixture(tmp_path)
    tracked = source / "sandbox" / "tracked.txt"
    tracked.write_text("approved second revision\n", encoding="utf-8")
    git(source, "add", "sandbox/tracked.txt")
    git(source, "commit", "-m", "approved second revision")
    approved_revision = git(source, "rev-parse", "HEAD")
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    execute(
        manager,
        WorkspacePrepareJobSpec(
            workspace_id=uuid.uuid4(),
            execution_grant=execution_grant(approved_revision),
        ),
    )
    mirror = manager._git.mirror_path(HANDLE)
    replacement = mirror / "refs" / "replace" / approved_revision
    replacement.parent.mkdir(parents=True)
    replacement.write_text(replaced_revision + "\n", encoding="ascii")

    output = manager._git._run(
        [
            "-C",
            os.fspath(mirror),
            "show",
            f"{approved_revision}:sandbox/tracked.txt",
        ],
        failure=FailureCode.WORKSPACE_STATE_INVALID,
    )

    assert output == b"approved second revision\n"


def test_checkout_manifest_proves_modes_symlink_gitlink_and_empty_ref_namespace(
    tmp_path: Path,
) -> None:
    source, _ = repository_fixture(tmp_path)
    git(source, "restore", "sandbox/tracked.txt")
    executable = source / "sandbox" / "script.sh"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    symlink = source / "sandbox" / "tracked-link"
    symlink.symlink_to("tracked.txt")
    git(source, "add", "sandbox/script.sh", "sandbox/tracked-link")
    missing_gitlink_target = "1" * 40
    git(
        source,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{missing_gitlink_target},sandbox/inert-module",
    )
    git(source, "commit", "-m", "checkout manifest fixture")
    revision = git(source, "rev-parse", "HEAD")
    source_before = _filesystem_snapshot(source)
    settings = runner_settings(tmp_path, source)
    operations = GitOperations(settings)
    permit_expires_at = datetime.now(UTC) + timedelta(minutes=1)
    prepared = operations.prepare_mirror(
        HANDLE,
        settings.repository_handles[HANDLE],
        revision,
        permit_expires_at=permit_expires_at,
    )
    mirror_entries = {entry.name for entry in prepared.path.iterdir()}
    assert mirror_entries == {"HEAD", "config", "objects", "refs"}
    assert not any(
        path.is_file() or path.is_symlink() for path in (prepared.path / "refs").rglob("*")
    )
    workspace_id = uuid.uuid4()

    proof = operations.create_detached_worktree(
        prepared,
        workspace_id,
        revision,
        permit_expires_at=permit_expires_at,
    )

    manifest = {entry.relative_path: entry for entry in prepared.checkout_manifest}
    assert proof.expected_manifest_digest == prepared.manifest_digest
    assert proof.actual_manifest_digest == prepared.manifest_digest
    assert proof.entry_count == len(prepared.checkout_manifest)
    assert manifest[b"sandbox/script.sh"].mode == 0o100755
    assert manifest[b"sandbox/tracked-link"].entry_type == "symlink"
    assert manifest[b"sandbox/tracked-link"].sha256 == hashlib.sha256(b"tracked.txt").hexdigest()
    assert manifest[b"sandbox/inert-module"].entry_type == "gitlink"
    assert (proof.workspace / "sandbox" / "inert-module").is_dir()
    assert not any((proof.workspace / "sandbox" / "inert-module").iterdir())
    assert _filesystem_snapshot(source) == source_before


def test_semantically_different_checkout_is_quarantined_before_registration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, revision = repository_fixture(tmp_path)
    source_before = _filesystem_snapshot(source)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    original_run = manager._git._run
    workspace_id = uuid.uuid4()

    def run_and_tamper(arguments: list[str], **kwargs: Any) -> bytes:
        output = original_run(arguments, **kwargs)
        if len(arguments) > 3 and arguments[2:4] == ["worktree", "add"]:
            (manager._git.workspace_path(workspace_id) / "sandbox" / "tracked.txt").write_text(
                "semantically different checkout\n",
                encoding="utf-8",
            )
        return output

    monkeypatch.setattr(manager._git, "_run", run_and_tamper)

    with pytest.raises(WorkspaceExecutionError) as error:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=workspace_id,
                execution_grant=execution_grant(revision),
            ),
        )

    assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
    assert not manager._git.workspace_path(workspace_id).exists()
    quarantines = list(settings.workspace_root.glob(f"quarantine-workspace-{workspace_id.hex}-*"))
    assert len(quarantines) == 1
    assert (quarantines[0] / "sandbox" / "tracked.txt").read_text(
        encoding="utf-8"
    ) == "semantically different checkout\n"
    assert manager._load_registry(workspace_id) is None
    assert _filesystem_snapshot(source) == source_before


@pytest.mark.parametrize(
    "indirection",
    ["objects/info/alternates", "objects/info/http-alternates", "info/grafts", "refs/replace"],
)
def test_source_object_indirection_is_rejected_without_source_mutation(
    tmp_path: Path,
    indirection: str,
) -> None:
    source, revision = repository_fixture(tmp_path)
    path = source / ".git" / indirection
    if indirection == "refs/replace":
        path.mkdir(parents=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("/untrusted/object-store\n", encoding="utf-8")
    before = _filesystem_snapshot(source)
    manager = WorkspaceManager(runner_settings(tmp_path, source))

    with pytest.raises(WorkspaceExecutionError) as error:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=uuid.uuid4(),
                execution_grant=execution_grant(revision),
            ),
        )

    assert error.value.code == FailureCode.REPOSITORY_UNAVAILABLE
    assert _filesystem_snapshot(source) == before


def test_gitlink_is_inert_and_does_not_import_its_target_commit(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    tree = subprocess.run(
        ["git", "-C", str(source), "mktree"],
        input=f"160000 commit {revision}\tsynthetic-submodule\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(source), "commit-tree", tree, "-m", "gitlink fixture"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    git(source, "update-ref", "refs/heads/main", commit)
    before = _filesystem_snapshot(source)
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    workspace_id = uuid.uuid4()

    execute(
        manager,
        WorkspacePrepareJobSpec(
            workspace_id=workspace_id,
            execution_grant=execution_grant(commit),
        ),
    )

    mirror = manager._git.mirror_path(HANDLE)
    assert not (mirror / "objects" / revision[:2] / revision[2:]).exists()
    assert manager._git.workspace_path(workspace_id).is_dir()
    assert _filesystem_snapshot(source) == before


def test_malformed_loose_object_declared_length_is_rejected(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    tree_id = git(source, "rev-parse", f"{revision}^{{tree}}")
    content = (
        f"tree {tree_id}\n"
        "author Fixture <fixture@example.invalid> 0 +0000\n"
        "committer Fixture <fixture@example.invalid> 0 +0000\n\n"
        "malformed declaration\n"
    ).encode()
    malformed = b"commit 999999\0" + content
    object_id = hashlib.sha1(malformed).hexdigest()
    object_path = source / ".git" / "objects" / object_id[:2] / object_id[2:]
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(zlib.compress(malformed))
    (source / ".git" / "HEAD").write_text(object_id + "\n", encoding="ascii")
    before = _filesystem_snapshot(source)
    manager = WorkspaceManager(runner_settings(tmp_path, source))

    with pytest.raises(WorkspaceExecutionError) as error:
        execute(
            manager,
            WorkspacePrepareJobSpec(
                workspace_id=uuid.uuid4(),
                execution_grant=execution_grant(object_id),
            ),
        )

    assert error.value.code == FailureCode.REPOSITORY_UNAVAILABLE
    assert _filesystem_snapshot(source) == before


def test_registry_loss_reconciles_only_exact_signed_pending_discard_proof(
    tmp_path: Path,
) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    sibling_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=sibling_id, execution_grant=grant),
    )
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    operation_id = uuid.uuid4()
    permit = side_effect_permit(manager, spec, operation_id)
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    registry.pending_operation = {"operation_id": str(operation_id), "kind": "discard"}
    registry.pending_permit_id = permit.id
    manager._create_discard_proof(
        spec,
        registry,
        operation_id=operation_id,
        permit=permit,
    )
    manager._save_registry(registry)
    source_before = _filesystem_snapshot(source)
    manager._git.discard_worktree(
        manager._git.mirror_path(HANDLE),
        manager._git.workspace_path(workspace_id),
        permit_expires_at=permit.expires_at,
    )
    mirror_before = _filesystem_snapshot(manager._git.mirror_path(HANDLE))
    manager._registry_path(workspace_id).unlink()

    result = cast(
        WorkspaceDiscardResult,
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        ),
    )

    assert result.discarded is True
    assert result.idempotent is True
    proof = manager._ownership.load_discard_proof(workspace_id)
    assert proof is not None
    assert proof.state == "completed"
    assert manager._git.workspace_path(sibling_id).is_dir()
    assert _filesystem_snapshot(source) == source_before
    assert _filesystem_snapshot(manager._git.mirror_path(HANDLE)) == mirror_before


def test_completed_discard_replay_requires_terminal_proof_and_absent_root(
    tmp_path: Path,
) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    sibling_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=sibling_id, execution_grant=grant),
    )
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    operation_id = uuid.uuid4()
    permit = side_effect_permit(manager, spec, operation_id)
    source_before = _filesystem_snapshot(source)

    first = cast(
        WorkspaceDiscardResult,
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        ),
    )
    mirror_before = _filesystem_snapshot(manager._git.mirror_path(HANDLE))
    replay = cast(
        WorkspaceDiscardResult,
        WorkspaceManager(settings).execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        ),
    )
    assert first.idempotent is False
    assert replay.idempotent is True

    workspace = manager._git.workspace_path(workspace_id)
    workspace.mkdir()
    preserved = workspace / "unknown-preserved.txt"
    preserved.write_text("must not be removed\n", encoding="utf-8")
    with pytest.raises(WorkspaceExecutionError) as replaced_root:
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        )
    assert replaced_root.value.code == FailureCode.WORKSPACE_RECOVERY_REQUIRED
    assert preserved.read_text(encoding="utf-8") == "must not be removed\n"
    preserved.unlink()
    workspace.rmdir()

    completed = manager._ownership.load_discard_proof(workspace_id)
    assert completed is not None
    assert completed.state == "completed"
    replayed_pending = completed.model_copy(
        update={
            "state": "pending",
            "completed_at": None,
        }
    )
    manager._ownership.save_discard_proof(replayed_pending)
    with pytest.raises(WorkspaceExecutionError) as rolled_back_proof:
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        )
    assert rolled_back_proof.value.code == FailureCode.WORKSPACE_QUARANTINED
    assert manager._git.workspace_path(sibling_id).is_dir()
    assert _filesystem_snapshot(source) == source_before
    assert _filesystem_snapshot(manager._git.mirror_path(HANDLE)) == mirror_before


def test_tampered_or_replayed_discard_proof_is_quarantined(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    operation_id = uuid.uuid4()
    permit = side_effect_permit(manager, spec, operation_id)
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    registry.pending_operation = {"operation_id": str(operation_id), "kind": "discard"}
    registry.pending_permit_id = permit.id
    original_proof = manager._create_discard_proof(
        spec,
        registry,
        operation_id=operation_id,
        permit=permit,
    )
    manager._save_registry(registry)
    manager._git.discard_worktree(
        manager._git.mirror_path(HANDLE),
        manager._git.workspace_path(workspace_id),
        permit_expires_at=permit.expires_at,
    )
    manager._registry_path(workspace_id).unlink()
    proof_path = manager._ownership.discard_proof_path(workspace_id)
    tampered = json.loads(proof_path.read_text(encoding="utf-8"))
    tampered["permit_id"] = str(uuid.uuid4())
    proof_path.write_text(json.dumps(tampered), encoding="utf-8")
    os.chmod(proof_path, 0o600)

    with pytest.raises(WorkspaceExecutionError) as tamper_error:
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        )
    assert tamper_error.value.code == FailureCode.WORKSPACE_QUARANTINED

    signed = manager._ownership.save_discard_proof(original_proof)
    assert signed.state == "pending"
    replay_operation = uuid.uuid4()
    replay_permit = side_effect_permit(
        manager,
        spec,
        replay_operation,
        expected_current=registry.current_tree_hash,
    )
    with pytest.raises(WorkspaceExecutionError) as replay_error:
        manager.execute(
            spec,
            operation_id=replay_operation,
            cancel_event=threading.Event(),
            side_effect_permit=replay_permit,
        )
    assert replay_error.value.code == FailureCode.WORKSPACE_QUARANTINED


def test_discard_proof_inode_rename_and_expiry_fail_closed(tmp_path: Path) -> None:
    source, revision = repository_fixture(tmp_path)
    settings = runner_settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = execution_grant(revision)
    workspace_id = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
    )
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    operation_id = uuid.uuid4()
    permit = side_effect_permit(manager, spec, operation_id)
    registry = manager._load_registry(workspace_id)
    assert registry is not None
    registry.pending_operation = {"operation_id": str(operation_id), "kind": "discard"}
    registry.pending_permit_id = permit.id
    manager._create_discard_proof(
        spec,
        registry,
        operation_id=operation_id,
        permit=permit,
    )
    manager._save_registry(registry)
    workspace = manager._git.workspace_path(workspace_id)
    nested_preservation = settings.workspace_root / "nested-preservation"
    nested_preservation.mkdir()
    preserved = nested_preservation / workspace.name
    workspace.rename(preserved)
    manager._registry_path(workspace_id).unlink()

    with pytest.raises(WorkspaceExecutionError) as rename_error:
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=permit,
        )
    assert rename_error.value.code == FailureCode.WORKSPACE_RECOVERY_REQUIRED
    assert preserved.is_dir()

    expiry_workspace = uuid.uuid4()
    execute(
        manager,
        WorkspacePrepareJobSpec(workspace_id=expiry_workspace, execution_grant=grant),
    )
    expiry_spec = WorkspaceDiscardJobSpec(
        workspace_id=expiry_workspace,
        execution_grant=grant,
    )
    expiry_operation = uuid.uuid4()
    expiry_permit = side_effect_permit(
        manager,
        expiry_spec,
        expiry_operation,
        expires_at=datetime.now(UTC) + timedelta(milliseconds=300),
    )
    expiry_registry = manager._load_registry(expiry_workspace)
    assert expiry_registry is not None
    expiry_registry.pending_operation = {
        "operation_id": str(expiry_operation),
        "kind": "discard",
    }
    expiry_registry.pending_permit_id = expiry_permit.id
    manager._create_discard_proof(
        expiry_spec,
        expiry_registry,
        operation_id=expiry_operation,
        permit=expiry_permit,
    )
    manager._save_registry(expiry_registry)
    manager._git.discard_worktree(
        manager._git.mirror_path(HANDLE),
        manager._git.workspace_path(expiry_workspace),
        permit_expires_at=expiry_permit.expires_at,
    )
    manager._registry_path(expiry_workspace).unlink()
    time.sleep(0.35)
    with pytest.raises(WorkspaceExecutionError) as expiry_error:
        manager.execute(
            expiry_spec,
            operation_id=expiry_operation,
            cancel_event=threading.Event(),
            side_effect_permit=expiry_permit,
        )
    assert expiry_error.value.code == FailureCode.SIDE_EFFECT_PERMIT_EXPIRED


def test_git_deadline_monitors_group_after_pipes_close_and_escalates_to_kill(
    tmp_path: Path,
) -> None:
    source, _ = repository_fixture(tmp_path)
    operations = GitOperations(
        runner_settings(tmp_path, source).model_copy(update={"git_termination_grace_seconds": 0.05})
    )
    marker = tmp_path / "term-resistant-marker"
    child_code = (
        "import pathlib,signal,time;"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
        f"time.sleep(0.5);pathlib.Path({str(marker)!r}).touch()"
    )
    parent_code = (
        "import subprocess,sys;"
        "subprocess.Popen("
        f"[sys.executable,'-c',{child_code!r}],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL,close_fds=True)"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        with pytest.raises(GitOperationError) as error:
            operations._collect_bounded_output(
                process,
                timeout_seconds=0.05,
                timeout_failure=FailureCode.WORKSPACE_STATE_INVALID,
            )
        assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
        operations._terminate_process_group(process, process.pid)
        operations._terminate_process_group(process, process.pid)
        time.sleep(0.55)
        assert not marker.exists()
        assert not operations._process_group_alive(process.pid)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        process.wait(timeout=1)


def test_git_deadline_kills_multiple_descendants_after_leader_is_reaped(
    tmp_path: Path,
) -> None:
    source, _ = repository_fixture(tmp_path)
    operations = GitOperations(runner_settings(tmp_path, source))
    markers = [tmp_path / f"descendant-{index}" for index in range(3)]
    child_codes = [
        f"import pathlib,time;time.sleep(0.4);pathlib.Path({str(marker)!r}).touch()"
        for marker in markers
    ]
    parent_code = "import subprocess,sys;" + ";".join(
        "subprocess.Popen("
        f"[sys.executable,'-c',{code!r}],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL,close_fds=True)"
        for code in child_codes
    )
    process = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    process.wait(timeout=1)
    try:
        with pytest.raises(GitOperationError) as error:
            operations._collect_bounded_output(
                process,
                timeout_seconds=0.05,
                timeout_failure=FailureCode.WORKSPACE_STATE_INVALID,
            )
        assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
        time.sleep(0.5)
        assert not any(marker.exists() for marker in markers)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def test_git_output_overflow_kills_descendant_and_normal_exit_is_bounded(
    tmp_path: Path,
) -> None:
    source, _ = repository_fixture(tmp_path)
    operations = GitOperations(
        runner_settings(tmp_path, source).model_copy(update={"git_max_output_bytes": 4096})
    )
    normal = subprocess.Popen(
        [sys.executable, "-c", "print('bounded-output')"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    output, returncode = operations._collect_bounded_output(
        normal,
        timeout_seconds=1,
        timeout_failure=FailureCode.WORKSPACE_STATE_INVALID,
    )
    assert output == b"bounded-output\n"
    assert returncode == 0

    marker = tmp_path / "overflow-child-marker"
    child_code = f"import pathlib,time;time.sleep(0.4);pathlib.Path({str(marker)!r}).touch()"
    parent_code = (
        "import subprocess,sys;"
        f"subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
        "sys.stdout.write('x'*8192);sys.stdout.flush()"
    )
    overflowing = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        with pytest.raises(GitOperationError) as error:
            operations._collect_bounded_output(
                overflowing,
                timeout_seconds=1,
                timeout_failure=FailureCode.WORKSPACE_STATE_INVALID,
            )
        assert error.value.code == FailureCode.GIT_OUTPUT_LIMIT_EXCEEDED
        time.sleep(0.5)
        assert not marker.exists()
    finally:
        try:
            os.killpg(overflowing.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        overflowing.wait(timeout=1)


def test_git_group_termination_failure_has_stable_typed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, _ = repository_fixture(tmp_path)
    operations = GitOperations(
        runner_settings(tmp_path, source).model_copy(update={"git_termination_grace_seconds": 0.05})
    )
    process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(1)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    monkeypatch.setattr(operations, "_process_group_alive", lambda _group_id: True)
    try:
        with pytest.raises(GitOperationError) as error:
            operations._collect_bounded_output(
                process,
                timeout_seconds=0.02,
                timeout_failure=FailureCode.GIT_OUTPUT_LIMIT_EXCEEDED,
            )
        assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
    finally:
        monkeypatch.undo()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        process.wait(timeout=1)


def _filesystem_snapshot(root: Path) -> list[tuple[str, int, int, str]]:
    snapshot: list[tuple[str, int, int, str]] = []
    for path in sorted(root.rglob("*")):
        metadata = os.lstat(path)
        digest = ""
        if stat.S_ISREG(metadata.st_mode):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        snapshot.append(
            (
                path.relative_to(root).as_posix(),
                stat.S_IFMT(metadata.st_mode),
                metadata.st_size,
                digest,
            )
        )
    return snapshot
