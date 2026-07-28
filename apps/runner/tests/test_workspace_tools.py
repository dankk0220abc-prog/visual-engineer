import hashlib
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

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
    mirror_settings = runner_settings(tmp_path / "mirror-budget", source).model_copy(
        update={"mirror_max_object_bytes": 1024}
    )
    mirror_manager = WorkspaceManager(mirror_settings)
    opened_object = tmp_path / "opened-object"
    opened_object.write_bytes(os.urandom(2048))
    opened_destination = tmp_path / "opened-object-copy"
    with pytest.raises(GitOperationError) as opened_limit:
        mirror_manager._git._copy_object_file(
            opened_object,
            opened_destination,
            max_bytes=1024,
            permit_expires_at=datetime.now(UTC) + timedelta(seconds=5),
        )
    assert opened_limit.value.code == FailureCode.MIRROR_BUDGET_EXCEEDED
    assert not opened_destination.exists()

    accumulated_source = tmp_path / "accumulated-source"
    accumulated_destination = tmp_path / "accumulated-destination"
    (accumulated_source / "objects" / "aa").mkdir(parents=True)
    (accumulated_destination / "aa").mkdir(parents=True)
    (accumulated_destination / "bb").mkdir()
    (accumulated_source / "objects" / "aa" / ("1" * 38)).write_bytes(os.urandom(400))
    (accumulated_destination / "bb" / ("2" * 38)).write_bytes(os.urandom(800))
    with pytest.raises(GitOperationError) as accumulated_limit:
        mirror_manager._git._copy_source_objects(
            accumulated_source,
            accumulated_destination,
            permit_expires_at=datetime.now(UTC) + timedelta(seconds=5),
        )
    assert accumulated_limit.value.code == FailureCode.MIRROR_BUDGET_EXCEEDED
    assert not (accumulated_destination / "aa" / ("1" * 38)).exists()

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
