from __future__ import annotations

import hashlib
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from apps.runner.tests.test_workspace_tools import (
    _filesystem_snapshot,
    delivery_authorization,
    execute,
    execution_grant,
    repository_fixture,
    runner_settings,
)

from visual_engineer_runner.workspace_manager import (
    WorkspaceExecutionError,
    WorkspaceManager,
)
from visual_engineer_runner_protocol import (
    FailureCode,
    WorkspaceGitCommitJobSpec,
    WorkspacePrepareJobSpec,
    WorkspaceWriteMode,
    WorkspaceWriteTextJobSpec,
    WorkspaceWriteTextResult,
)


def _add_arbitrary_loose_ref(mirror: Path, revision: str) -> None:
    reference = mirror / "refs" / "heads" / "audit-unmanaged"
    reference.write_text(revision + "\n", encoding="ascii")


def _add_packed_ref(mirror: Path, revision: str) -> None:
    (mirror / "packed-refs").write_text(
        f"# pack-refs with: peeled fully-peeled sorted\n{revision} refs/heads/audit-packed\n",
        encoding="ascii",
    )


def _add_replacement_metadata(mirror: Path, revision: str) -> None:
    replacement = mirror / "refs" / "replace" / revision
    replacement.parent.mkdir()
    replacement.write_text(revision + "\n", encoding="ascii")


@pytest.mark.parametrize(
    "tamper",
    [
        pytest.param(_add_arbitrary_loose_ref, id="arbitrary-loose-ref"),
        pytest.param(_add_packed_ref, id="packed-ref"),
        pytest.param(_add_replacement_metadata, id="replacement-metadata"),
    ],
)
def test_phase6_delivery_revalidates_managed_mirror_immediately_before_ref_mutation(
    tmp_path: Path,
    tamper: Callable[[Path, str], None],
) -> None:
    """VE-P6-FSR-001: post-prepare mirror tampering must deny delivery."""

    source, revision = repository_fixture(tmp_path)
    source_before = _filesystem_snapshot(source)
    manager = WorkspaceManager(runner_settings(tmp_path, source))
    workspace_id = uuid.uuid4()
    grant = execution_grant(revision)
    execute(
        manager,
        WorkspacePrepareJobSpec(
            workspace_id=workspace_id,
            execution_grant=grant,
        ),
    )
    written = execute(
        manager,
        WorkspaceWriteTextJobSpec(
            workspace_id=workspace_id,
            execution_grant=grant,
            mode=WorkspaceWriteMode.REPLACE,
            relative_path="sandbox/tracked.txt",
            content="phase 6 independent audit\n",
            expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
        ),
    )
    assert isinstance(written, WorkspaceWriteTextResult)
    authorization = delivery_authorization(
        grant,
        workspace_id=workspace_id,
        checkpoint_id=uuid.uuid4(),
        checkpoint_fingerprint=written.checkpoint.tree_fingerprint,
        checkpoint_diff_hash=written.checkpoint.diff_hash,
    )
    spec = WorkspaceGitCommitJobSpec(
        workspace_id=workspace_id,
        execution_grant=grant,
        delivery_authorization=authorization,
        checkpoint_id=authorization.checkpoint_id,
        checkpoint_fingerprint=authorization.checkpoint_fingerprint,
        checkpoint_diff_hash=authorization.checkpoint_diff_hash,
    )
    mirror = manager._git.mirror_path(grant.repository_opaque_handle)
    tamper(mirror, revision)

    failure: WorkspaceExecutionError | None = None
    result: object | None = None
    try:
        result = execute(manager, spec)
    except WorkspaceExecutionError as exc:
        failure = exc
    target = subprocess.run(
        [
            "git",
            "-C",
            str(manager._git.workspace_path(workspace_id)),
            "rev-parse",
            "--verify",
            "--quiet",
            authorization.branch_ref,
        ],
        check=False,
        capture_output=True,
    )
    source_unchanged = _filesystem_snapshot(source) == source_before

    assert failure is not None, (
        "VE-P6-FSR-001: governed delivery accepted post-prepare managed-mirror tampering; "
        f"result_type={type(result).__name__}; target_ref_present={target.returncode == 0}; "
        f"source_unchanged={source_unchanged}"
    )
    assert failure.code == FailureCode.WORKSPACE_STATE_INVALID
    assert target.returncode == 1
    assert target.stdout == b""
    assert source_unchanged
