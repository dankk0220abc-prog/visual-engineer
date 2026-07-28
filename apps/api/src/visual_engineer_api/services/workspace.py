import fnmatch
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import NoReturn

from pydantic import ValidationError
from sqlalchemy.orm import Session

from visual_engineer_api.core.config import get_settings
from visual_engineer_api.models.runner import Runner
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    ExecutionGrantDecision,
    RepositoryHandle,
    Workspace,
    WorkspaceEvent,
)
from visual_engineer_api.repositories.workspace import WorkspaceRepository
from visual_engineer_api.schemas.workspace import (
    EligibleExecutionContextResponse,
    ExecutionGrantCreate,
    ExecutionGrantDecisionCreate,
    ExecutionGrantDecisionResponse,
    ExecutionGrantResponse,
    RepositoryHandleResponse,
    WorkspaceActionResponse,
    WorkspaceCheckpointResponse,
    WorkspaceCreate,
    WorkspaceListAction,
    WorkspaceReadTextAction,
    WorkspaceResponse,
    WorkspaceWriteTextAction,
)
from visual_engineer_api.services.runner import RunnerService
from visual_engineer_runner_protocol import (
    ExecutionGrantPolicy,
    JobKind,
    RepositoryRegistrationRequest,
    RepositoryRegistrationResponse,
    WorkspaceDiffJobSpec,
    WorkspaceDiscardJobSpec,
    WorkspaceJobSpec,
    WorkspaceListJobSpec,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspaceReadTextJobSpec,
    WorkspaceRollbackJobSpec,
    WorkspaceStatusJobSpec,
    WorkspaceWriteTextJobSpec,
    compute_execution_grant_policy_hash,
    execution_grant_policy_hash_matches,
)

PHASE4_ALLOWED_OPERATIONS = [
    WorkspaceOperation.PREPARE,
    WorkspaceOperation.LIST,
    WorkspaceOperation.READ_TEXT,
    WorkspaceOperation.WRITE_TEXT,
    WorkspaceOperation.STATUS,
    WorkspaceOperation.DIFF,
    WorkspaceOperation.ROLLBACK,
    WorkspaceOperation.DISCARD,
]
PHASE4_ALLOWED_PATHS = ["sandbox/**"]
PHASE4_DENIED_PATHS = [
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
    "**/*.crt",
    "**/*.cer",
    "**/*.p12",
    "**/*.pfx",
]
PHASE4_MAX_FILES_CHANGED = 8
PHASE4_MAX_TOTAL_WRITE_BYTES = 128 * 1024
PHASE4_MAX_SINGLE_FILE_BYTES = 32 * 1024
PHASE4_MAX_DIFF_BYTES = 32 * 1024
PHASE4_GRANT_TTL_SECONDS = 30 * 60
PHASE4_WORKSPACE_TTL_SECONDS = 20 * 60
_SENSITIVE_COMPONENT = re.compile(
    r"(?i)(?:^\.env(?:\.|$)|credential|secret|token|"
    r"(?:^|[._-])(?:id_rsa|id_ed25519)(?:$|[._-])|"
    r"\.(?:key|pem|crt|cer|p12|pfx)$)"
)
_SENSITIVE_TEXT = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(?:token|secret|password|authorization)\s*[:=]\s*\S{8,}))"
)


class WorkspaceServiceError(Exception):
    def __init__(self, code: str, message: str, *, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repositories = WorkspaceRepository(session)
        self._settings = get_settings()

    def register_repository(
        self,
        authenticated: Runner,
        payload: RepositoryRegistrationRequest,
        *,
        request_id: str,
    ) -> RepositoryRegistrationResponse:
        del request_id
        if authenticated.id != payload.runner_id:
            raise WorkspaceServiceError(
                "runner_identity_mismatch",
                "Runner identity does not match its credential",
                category="forbidden",
            )
        handle = self._repositories.get_repository_handle_by_opaque(
            authenticated.id,
            payload.opaque_handle,
            lock=True,
        )
        now = utc_now()
        if handle is None:
            handle = RepositoryHandle(
                runner_id=authenticated.id,
                opaque_handle=payload.opaque_handle,
                display_name=payload.display_name,
                vcs_kind=payload.vcs_kind,
                status="available",
                capabilities=list(payload.capabilities),
                current_revision=payload.current_revision,
                current_branch=payload.current_branch,
                source_status=payload.source_status.value,
                source_is_dirty=payload.source_is_dirty,
                dirty_path_count=payload.dirty_path_count,
                last_verified_at=now,
                metadata_version=payload.metadata_version,
            )
            self._repositories.add(handle)
            self._session.flush()
        elif handle.status == "revoked":
            raise WorkspaceServiceError(
                "repository_handle_revoked",
                "Repository Handle is revoked",
                category="forbidden",
            )
        else:
            handle.display_name = payload.display_name
            handle.status = "available"
            handle.capabilities = list(payload.capabilities)
            handle.current_revision = payload.current_revision
            handle.current_branch = payload.current_branch
            handle.source_status = payload.source_status.value
            handle.source_is_dirty = payload.source_is_dirty
            handle.dirty_path_count = payload.dirty_path_count
            handle.last_verified_at = now
            handle.metadata_version = payload.metadata_version
        self._session.commit()
        return RepositoryRegistrationResponse(
            repository_handle_id=handle.id,
            opaque_handle=handle.opaque_handle,
            status="available",
            current_revision=payload.current_revision,
            last_verified_at=now,
        )

    def list_repositories(self) -> list[RepositoryHandleResponse]:
        return [
            self._repository_response(item) for item in self._repositories.list_repository_handles()
        ]

    def get_repository(self, repository_id: uuid.UUID) -> RepositoryHandleResponse:
        handle = self._repositories.get_repository_handle(repository_id)
        if handle is None:
            self._not_found("repository_not_found", "Repository Handle was not found")
        return self._repository_response(handle)

    def list_eligible_contexts(self) -> list[EligibleExecutionContextResponse]:
        return [
            EligibleExecutionContextResponse(
                plan_id=plan.id,
                run_id=run.id,
                task_id=task.id,
                plan_version=plan.version,
                task_title=task.title,
                repository_handle_id=handle.id,
                repository_display_name=handle.display_name,
                source_revision=snapshot.source_revision,
                snapshot_fingerprint=snapshot.fingerprint,
            )
            for plan, run, task, snapshot, handle in (
                self._repositories.eligible_execution_contexts()
            )
        ]

    def create_grant(
        self,
        payload: ExecutionGrantCreate,
        *,
        request_id: str,
    ) -> ExecutionGrantResponse:
        del request_id
        existing = self._repositories.latest_grant_for_context(
            payload.plan_id, payload.repository_handle_id
        )
        if existing is not None:
            if self._expire_grant(existing):
                self._session.commit()
            if existing.status in {"pending", "approved"}:
                return self._grant_response(existing)
        context = self._repositories.execution_context(
            payload.plan_id,
            payload.repository_handle_id,
            lock=True,
        )
        if context is None:
            self._not_found(
                "execution_context_not_found",
                "Approved Plan and Repository context was not found",
            )
        plan, run, task, snapshot, handle = context
        if plan.status != "approved" or run.status != "approved":
            self._conflict(
                "plan_not_approved",
                "Execution Grant requires an approved Plan",
            )
        if plan.snapshot_fingerprint != snapshot.fingerprint:
            self._conflict(
                "plan_snapshot_mismatch",
                "Plan is not bound to the current stored Snapshot",
            )
        if (
            handle.status != "available"
            or handle.current_revision is None
            or handle.current_revision != snapshot.source_revision
            or handle.display_name != task.repository_display_name
        ):
            self._conflict(
                "stale_execution_baseline",
                "Repository revision or identity no longer matches the approved Plan",
            )
        if set(handle.capabilities) != {
            "committed_head_read",
            "isolated_workspace",
        }:
            raise WorkspaceServiceError(
                "repository_capability_denied",
                "Repository Handle lacks isolated workspace capability",
                category="policy",
            )

        now = utc_now()
        grant_id = uuid.uuid4()
        expires_at = now + timedelta(seconds=PHASE4_GRANT_TTL_SECONDS)
        values = {
            "id": grant_id,
            "grant_version": 1,
            "task_id": task.id,
            "run_id": run.id,
            "plan_id": plan.id,
            "repository_handle_id": handle.id,
            "repository_opaque_handle": handle.opaque_handle,
            "source_revision": snapshot.source_revision,
            "snapshot_fingerprint": snapshot.fingerprint,
            "allowed_operations": PHASE4_ALLOWED_OPERATIONS,
            "allowed_paths": PHASE4_ALLOWED_PATHS,
            "denied_paths": PHASE4_DENIED_PATHS,
            "max_files_changed": PHASE4_MAX_FILES_CHANGED,
            "max_total_write_bytes": PHASE4_MAX_TOTAL_WRITE_BYTES,
            "max_single_file_bytes": PHASE4_MAX_SINGLE_FILE_BYTES,
            "max_diff_bytes": PHASE4_MAX_DIFF_BYTES,
            "workspace_ttl_seconds": PHASE4_WORKSPACE_TTL_SECONDS,
            "network_policy": "none",
            "shell_access": False,
            "git_delivery_access": False,
            "source_repository_write_access": False,
            "expires_at": expires_at,
            "policy_hash": "0" * 64,
        }
        draft = ExecutionGrantPolicy.model_validate(values)
        values["policy_hash"] = compute_execution_grant_policy_hash(draft)
        policy = ExecutionGrantPolicy.model_validate(values)
        grant = ExecutionGrant(
            id=grant_id,
            grant_version=policy.grant_version,
            task_id=task.id,
            run_id=run.id,
            plan_id=plan.id,
            repository_handle_id=handle.id,
            source_revision=policy.source_revision,
            snapshot_fingerprint=policy.snapshot_fingerprint,
            allowed_operations=[item.value for item in policy.allowed_operations],
            allowed_paths=policy.allowed_paths,
            denied_paths=policy.denied_paths,
            max_files_changed=policy.max_files_changed,
            max_total_write_bytes=policy.max_total_write_bytes,
            max_single_file_bytes=policy.max_single_file_bytes,
            max_diff_bytes=policy.max_diff_bytes,
            workspace_ttl_seconds=policy.workspace_ttl_seconds,
            network_policy=policy.network_policy,
            shell_access=policy.shell_access,
            git_delivery_access=policy.git_delivery_access,
            source_repository_write_access=policy.source_repository_write_access,
            status="pending",
            policy_hash=policy.policy_hash,
            requested_at=now,
            expires_at=expires_at,
        )
        self._repositories.add(grant)
        self._session.commit()
        self._session.refresh(grant)
        return self._grant_response(grant)

    def list_grants(self) -> list[ExecutionGrantResponse]:
        changed = False
        grants = self._repositories.list_grants()
        for grant in grants:
            changed = self._expire_grant(grant) or changed
            changed = self._advance_grant_revocation(grant) or changed
        if changed:
            self._session.commit()
        return [self._grant_response(item) for item in grants]

    def get_grant(self, grant_id: uuid.UUID) -> ExecutionGrantResponse:
        grant = self._repositories.get_grant(grant_id, lock=True)
        if grant is None:
            self._not_found("execution_grant_not_found", "Execution Grant was not found")
        if self._expire_grant(grant):
            self._session.commit()
        elif self._advance_grant_revocation(grant):
            self._session.commit()
        return self._grant_response(grant)

    def decide_grant(
        self,
        grant_id: uuid.UUID,
        payload: ExecutionGrantDecisionCreate,
        *,
        request_id: str,
    ) -> ExecutionGrantResponse:
        grant = self._repositories.get_grant(grant_id, lock=True)
        if grant is None:
            self._not_found("execution_grant_not_found", "Execution Grant was not found")
        existing = self._repositories.grant_decision(grant.id)
        if existing is not None:
            if existing.decision == payload.decision and existing.reason == payload.reason:
                return self._grant_response(grant)
            self._conflict(
                "execution_grant_decision_conflict",
                "A different Execution Grant decision is already recorded",
            )
        if self._expire_grant(grant):
            self._session.commit()
            self._conflict(
                "execution_grant_expired",
                "Execution Grant expired before decision",
            )
        if grant.status != "pending":
            self._conflict(
                "execution_grant_not_pending",
                "Execution Grant is not pending a decision",
            )
        decision = ExecutionGrantDecision(
            grant_id=grant.id,
            decision=payload.decision,
            reason=payload.reason,
            actor_type="local_user",
            request_id=request_id[:128],
        )
        now = utc_now()
        grant.status = "approved" if payload.decision == "approve" else "rejected"
        grant.decided_at = now
        self._repositories.add(decision)
        self._session.commit()
        self._session.refresh(grant)
        return self._grant_response(grant)

    def revoke_grant(
        self,
        grant_id: uuid.UUID,
        *,
        request_id: str,
    ) -> ExecutionGrantResponse:
        # Side-effect Permit acquisition locks Job/Attempt before Grant/Workspace.
        # Keep the same ordering here so a concurrent revoke cannot deadlock
        # against an acquire transaction.
        if self._repositories.get_grant(grant_id) is None:
            self._not_found("execution_grant_not_found", "Execution Grant was not found")
        active_jobs = self._repositories.active_jobs_for_grant(grant_id, lock=True)
        grant = self._repositories.get_grant(grant_id, lock=True)
        if grant is None:
            self._not_found("execution_grant_not_found", "Execution Grant was not found")
        if grant.status == "revoked":
            return self._grant_response(grant)
        if grant.status == "revoke_requested":
            if self._advance_grant_revocation(grant):
                self._session.commit()
            return self._grant_response(grant)
        if grant.status in {"rejected", "expired"}:
            self._conflict(
                "execution_grant_terminal",
                "Rejected or expired Execution Grant cannot be revoked",
            )
        now = utc_now()
        grant.status = "revoke_requested"
        grant.decided_at = grant.decided_at or now
        grant.revocation_requested_at = now
        seen_workspaces: set[uuid.UUID] = set()
        for job in active_jobs:
            if job.workspace_id is not None and job.workspace_id not in seen_workspaces:
                workspace = self._repositories.get_workspace(job.workspace_id, lock=True)
                if workspace is not None:
                    self._workspace_event(
                        workspace,
                        "grant_revoke_requested",
                        request_id=request_id,
                        metadata={"state": "revoke_requested"},
                    )
                    seen_workspaces.add(workspace.id)
        self._session.flush()
        runner_service = RunnerService(self._session)
        for job in active_jobs:
            if job.state not in {"cancelled", "succeeded", "failed"}:
                job.error_code = "execution_grant_inactive"
                job.error_message = "Execution Grant revocation cancelled the Workspace Job"
                runner_service.cancel_job(
                    job.id,
                    request_id=f"{request_id[:96]}-grant-revoke",
                )
        self._advance_grant_revocation(grant)
        self._session.commit()
        return self._grant_response(grant)

    def create_workspace(
        self,
        payload: WorkspaceCreate,
        *,
        request_id: str,
    ) -> WorkspaceActionResponse:
        replay = self._repositories.workspace_by_request(payload.grant_id, request_id)
        if replay is not None:
            latest = self._repositories.latest_workspace_job(replay.id)
            if latest is None:
                raise WorkspaceServiceError(
                    "workspace_job_missing",
                    "Workspace preparation Job is unavailable",
                    category="internal",
                )
            return WorkspaceActionResponse(
                workspace=self._workspace_response(replay),
                job=RunnerService(self._session).get_job(latest.id),
            )
        grant = self._active_grant(payload.grant_id, lock=True)
        existing = self._repositories.nonterminal_workspace_for_grant(grant.id, lock=True)
        if existing is not None:
            self._conflict(
                "workspace_already_exists",
                "Execution Grant already has a non-terminal Workspace",
            )
        handle = self._required_handle(grant.repository_handle_id)
        self._validate_current_baseline(grant, handle)
        now = utc_now()
        workspace = Workspace(
            grant_id=grant.id,
            runner_id=handle.runner_id,
            repository_handle_id=handle.id,
            source_revision=grant.source_revision,
            state="requested",
            changed_file_count=0,
            total_written_bytes=0,
            created_paths=[],
            expires_at=min(
                grant.expires_at,
                now + timedelta(seconds=grant.workspace_ttl_seconds),
            ),
        )
        self._repositories.add(workspace)
        self._session.flush()
        self._workspace_event(
            workspace,
            "grant_approved",
            request_id=request_id,
            metadata={"policy_hash": grant.policy_hash},
        )
        self._workspace_event(
            workspace,
            "workspace_requested",
            request_id=request_id,
            metadata={"state": workspace.state},
        )
        spec = WorkspacePrepareJobSpec(
            workspace_id=workspace.id,
            execution_grant=self._execution_policy(grant, handle),
        )
        job = RunnerService(self._session).create_workspace_job(spec, request_id=request_id)
        return WorkspaceActionResponse(
            workspace=self._workspace_response(workspace),
            job=job,
        )

    def list_workspaces(self) -> list[WorkspaceResponse]:
        changed = False
        workspaces = self._repositories.list_workspaces()
        for workspace in workspaces:
            changed = self._expire_workspace(workspace) or changed
        if changed:
            self._session.commit()
        return [self._workspace_response(item) for item in workspaces]

    def get_workspace(self, workspace_id: uuid.UUID) -> WorkspaceResponse:
        workspace = self._repositories.get_workspace(workspace_id, lock=True)
        if workspace is None:
            self._not_found("workspace_not_found", "Workspace was not found")
        if self._expire_workspace(workspace):
            self._session.commit()
        return self._workspace_response(workspace)

    def list_action(
        self,
        workspace_id: uuid.UUID,
        payload: WorkspaceListAction,
        *,
        request_id: str,
    ) -> WorkspaceActionResponse:
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.LIST,
            request_id=request_id,
            allowed_states={"ready", "active", "sealed", "rolled_back"},
        )
        self._require_path(grant, payload.relative_directory, directory=True)
        return self._dispatch_action(
            workspace,
            WorkspaceListJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
                relative_directory=payload.relative_directory,
                depth=payload.depth,
                max_entries=payload.max_entries,
            ),
            request_id=request_id,
        )

    def read_action(
        self,
        workspace_id: uuid.UUID,
        payload: WorkspaceReadTextAction,
        *,
        request_id: str,
    ) -> WorkspaceActionResponse:
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.READ_TEXT,
            request_id=request_id,
            allowed_states={"ready", "active", "sealed", "rolled_back"},
        )
        self._require_path(grant, payload.relative_path)
        return self._dispatch_action(
            workspace,
            WorkspaceReadTextJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
                relative_path=payload.relative_path,
                max_bytes=min(payload.max_bytes, grant.max_single_file_bytes),
            ),
            request_id=request_id,
        )

    def write_action(
        self,
        workspace_id: uuid.UUID,
        payload: WorkspaceWriteTextAction,
        *,
        request_id: str,
    ) -> WorkspaceActionResponse:
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.WRITE_TEXT,
            request_id=request_id,
            allowed_states={"ready", "active"},
        )
        self._require_path(grant, payload.relative_path)
        content_bytes = len(payload.content.encode("utf-8"))
        if _SENSITIVE_TEXT.search(payload.content):
            raise WorkspaceServiceError(
                "sensitive_content_denied",
                "Secret-like content cannot be submitted to a Workspace",
                category="policy",
            )
        if content_bytes > grant.max_single_file_bytes:
            raise WorkspaceServiceError(
                "file_too_large",
                "Write exceeds the Execution Grant single-file budget",
                category="policy",
            )
        if workspace.total_written_bytes + content_bytes > grant.max_total_write_bytes:
            raise WorkspaceServiceError(
                "total_write_budget_exceeded",
                "Write exceeds the Execution Grant total byte budget",
                category="policy",
            )
        return self._dispatch_action(
            workspace,
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
                mode=payload.mode,
                relative_path=payload.relative_path,
                content=payload.content,
                expected_absent=payload.expected_absent,
                expected_sha256=payload.expected_sha256,
            ),
            request_id=request_id,
        )

    def status_action(self, workspace_id: uuid.UUID, *, request_id: str) -> WorkspaceActionResponse:
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.STATUS,
            request_id=request_id,
            allowed_states={"ready", "active", "sealed", "rolled_back"},
        )
        return self._dispatch_action(
            workspace,
            WorkspaceStatusJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
            ),
            request_id=request_id,
        )

    def diff_action(self, workspace_id: uuid.UUID, *, request_id: str) -> WorkspaceActionResponse:
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.DIFF,
            request_id=request_id,
            allowed_states={"ready", "active", "sealed"},
        )
        return self._dispatch_action(
            workspace,
            WorkspaceDiffJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
            ),
            request_id=request_id,
        )

    def rollback_action(
        self, workspace_id: uuid.UUID, *, request_id: str
    ) -> WorkspaceActionResponse:
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.ROLLBACK,
            request_id=request_id,
            allowed_states={"ready", "active", "sealed"},
        )
        workspace.state = "rollback_requested"
        self._workspace_event(
            workspace,
            "rollback_requested",
            request_id=request_id,
            metadata={"state": workspace.state},
        )
        return self._dispatch_action(
            workspace,
            WorkspaceRollbackJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
            ),
            request_id=request_id,
        )

    def discard_action(
        self, workspace_id: uuid.UUID, *, request_id: str
    ) -> WorkspaceActionResponse:
        workspace = self._repositories.get_workspace(workspace_id, lock=True)
        if workspace is None:
            self._not_found("workspace_not_found", "Workspace was not found")
        if workspace.state == "discarded":
            latest = self._repositories.latest_workspace_job(workspace.id)
            if latest is None or latest.kind != JobKind.WORKSPACE_DISCARD_V1.value:
                raise WorkspaceServiceError(
                    "workspace_job_missing",
                    "Discarded Workspace has no disposal Job evidence",
                    category="internal",
                )
            return WorkspaceActionResponse(
                workspace=self._workspace_response(workspace),
                job=RunnerService(self._session).get_job(latest.id),
            )
        workspace, grant, handle = self._action_context(
            workspace_id,
            WorkspaceOperation.DISCARD,
            request_id=request_id,
            allowed_states={"sealed", "rolled_back", "failed", "expired"},
            allow_expired_workspace=True,
        )
        workspace.state = "discard_requested"
        self._workspace_event(
            workspace,
            "discard_requested",
            request_id=request_id,
            metadata={"state": workspace.state},
        )
        return self._dispatch_action(
            workspace,
            WorkspaceDiscardJobSpec(
                workspace_id=workspace.id,
                execution_grant=self._execution_policy(grant, handle),
            ),
            request_id=request_id,
        )

    def list_events(self, workspace_id: uuid.UUID) -> list[WorkspaceEvent]:
        if self._repositories.get_workspace(workspace_id) is None:
            self._not_found("workspace_not_found", "Workspace was not found")
        return self._repositories.list_workspace_events(workspace_id)

    def list_checkpoints(self, workspace_id: uuid.UUID) -> list[WorkspaceCheckpointResponse]:
        if self._repositories.get_workspace(workspace_id) is None:
            self._not_found("workspace_not_found", "Workspace was not found")
        return [
            WorkspaceCheckpointResponse.model_validate(item)
            for item in self._repositories.list_checkpoints(workspace_id)
        ]

    def _dispatch_action(
        self,
        workspace: Workspace,
        spec: WorkspaceJobSpec,
        *,
        request_id: str,
    ) -> WorkspaceActionResponse:
        replay = self._repositories.workspace_job_by_request(workspace.id, request_id)
        normalized_parameters = spec.model_dump(mode="json", exclude={"kind"})
        if replay is not None:
            if replay.kind != spec.kind.value or replay.parameters != normalized_parameters:
                self._conflict(
                    "idempotency_conflict",
                    "Request ID was reused for a different Workspace action",
                )
            return WorkspaceActionResponse(
                workspace=self._workspace_response(workspace),
                job=RunnerService(self._session).get_job(replay.id),
            )
        latest = self._repositories.latest_workspace_job(workspace.id)
        if latest is not None and latest.state in {
            "queued",
            "leased",
            "running",
            "cancel_requested",
        }:
            self._conflict(
                "workspace_action_in_progress",
                "Another Workspace action is still in progress",
            )
        job = RunnerService(self._session).create_workspace_job(spec, request_id=request_id)
        return WorkspaceActionResponse(
            workspace=self._workspace_response(workspace),
            job=job,
        )

    def _action_context(
        self,
        workspace_id: uuid.UUID,
        operation: WorkspaceOperation,
        *,
        request_id: str,
        allowed_states: set[str],
        allow_expired_workspace: bool = False,
    ) -> tuple[Workspace, ExecutionGrant, RepositoryHandle]:
        del request_id
        workspace = self._repositories.get_workspace(workspace_id, lock=True)
        if workspace is None:
            self._not_found("workspace_not_found", "Workspace was not found")
        self._expire_workspace(workspace)
        if workspace.state not in allowed_states:
            self._conflict(
                "workspace_state_invalid",
                "Workspace action is unavailable from its current state",
            )
        if workspace.expires_at <= utc_now() and not allow_expired_workspace:
            self._conflict("workspace_expired", "Workspace is expired")
        grant = self._active_grant(workspace.grant_id, lock=True)
        if operation.value not in grant.allowed_operations:
            raise WorkspaceServiceError(
                "operation_not_granted",
                "Workspace operation is outside the Execution Grant",
                category="policy",
            )
        handle = self._required_handle(workspace.repository_handle_id)
        self._validate_current_baseline(grant, handle)
        if (
            workspace.runner_id != handle.runner_id
            or workspace.repository_handle_id != grant.repository_handle_id
            or workspace.source_revision != grant.source_revision
        ):
            self._conflict(
                "workspace_binding_mismatch",
                "Workspace identity no longer matches the Execution Grant",
            )
        return workspace, grant, handle

    def _active_grant(self, grant_id: uuid.UUID, *, lock: bool) -> ExecutionGrant:
        grant = self._repositories.get_grant(grant_id, lock=lock)
        if grant is None:
            self._not_found("execution_grant_not_found", "Execution Grant was not found")
        if self._expire_grant(grant):
            self._session.flush()
        if grant.status != "approved":
            self._conflict(
                "execution_grant_inactive",
                "Execution Grant is not approved and active",
            )
        handle = self._required_handle(grant.repository_handle_id)
        policy = self._execution_policy(grant, handle)
        if not execution_grant_policy_hash_matches(policy, grant.policy_hash):
            raise WorkspaceServiceError(
                "execution_grant_hash_mismatch",
                "Execution Grant policy hash is invalid",
                category="policy",
            )
        return grant

    def _execution_policy(
        self, grant: ExecutionGrant, handle: RepositoryHandle
    ) -> ExecutionGrantPolicy:
        try:
            return ExecutionGrantPolicy.model_validate(
                {
                    "id": grant.id,
                    "grant_version": grant.grant_version,
                    "task_id": grant.task_id,
                    "run_id": grant.run_id,
                    "plan_id": grant.plan_id,
                    "repository_handle_id": grant.repository_handle_id,
                    "repository_opaque_handle": handle.opaque_handle,
                    "source_revision": grant.source_revision,
                    "snapshot_fingerprint": grant.snapshot_fingerprint,
                    "allowed_operations": grant.allowed_operations,
                    "allowed_paths": grant.allowed_paths,
                    "denied_paths": grant.denied_paths,
                    "max_files_changed": grant.max_files_changed,
                    "max_total_write_bytes": grant.max_total_write_bytes,
                    "max_single_file_bytes": grant.max_single_file_bytes,
                    "max_diff_bytes": grant.max_diff_bytes,
                    "workspace_ttl_seconds": grant.workspace_ttl_seconds,
                    "network_policy": grant.network_policy,
                    "shell_access": grant.shell_access,
                    "git_delivery_access": grant.git_delivery_access,
                    "source_repository_write_access": grant.source_repository_write_access,
                    "expires_at": grant.expires_at,
                    "policy_hash": grant.policy_hash,
                }
            )
        except ValidationError as exc:
            raise WorkspaceServiceError(
                "execution_grant_invalid",
                "Stored Execution Grant policy is invalid",
                category="policy",
            ) from exc

    def _required_handle(self, repository_id: uuid.UUID) -> RepositoryHandle:
        handle = self._repositories.get_repository_handle(repository_id, lock=True)
        if handle is None:
            self._not_found("repository_not_found", "Repository Handle was not found")
        return handle

    def _validate_current_baseline(self, grant: ExecutionGrant, handle: RepositoryHandle) -> None:
        if (
            handle.status != "available"
            or handle.current_revision != grant.source_revision
            or handle.runner_id is None
        ):
            self._conflict(
                "stale_execution_baseline",
                "Repository Handle no longer matches the granted source revision",
            )

    def _require_path(
        self,
        grant: ExecutionGrant,
        relative_path: str,
        *,
        directory: bool = False,
    ) -> None:
        components = relative_path.split("/")
        if ".git" in components or any(_SENSITIVE_COMPONENT.search(item) for item in components):
            raise WorkspaceServiceError(
                "sensitive_path_denied",
                "Sensitive or Git metadata paths are denied",
                category="policy",
            )
        if any(fnmatch.fnmatchcase(relative_path, pattern) for pattern in grant.denied_paths):
            raise WorkspaceServiceError(
                "path_denied",
                "Path is denied by the Execution Grant",
                category="policy",
            )
        allowed = any(
            fnmatch.fnmatchcase(relative_path, pattern)
            or (directory and pattern.startswith(relative_path.rstrip("/") + "/"))
            for pattern in grant.allowed_paths
        )
        if not allowed:
            raise WorkspaceServiceError(
                "path_denied",
                "Path is outside the Execution Grant allowlist",
                category="policy",
            )

    def _advance_grant_revocation(self, grant: ExecutionGrant) -> bool:
        if grant.status != "revoke_requested":
            return False
        now = utc_now()
        cutoff = now - timedelta(seconds=self._settings.side_effect_permit_safety_seconds)
        for permit in self._repositories.expired_in_flight_permits_for_grant(
            grant.id,
            cutoff,
            lock=True,
        ):
            permit.state = "expired"
            permit.terminal_at = now
        if self._repositories.in_flight_permits_for_grant(grant.id, lock=True):
            return False
        grant.status = "revoked"
        grant.revoked_at = now
        for workspace in self._repositories.workspaces_for_grant(grant.id):
            self._workspace_event(
                workspace,
                "grant_revoke_effective",
                request_id="grant-revoke-effective",
                metadata={"state": "revoked"},
            )
        return True

    def _expire_grant(self, grant: ExecutionGrant) -> bool:
        if grant.status in {"pending", "approved"} and grant.expires_at <= utc_now():
            grant.status = "expired"
            grant.decided_at = grant.decided_at or utc_now()
            return True
        return False

    def _expire_workspace(self, workspace: Workspace) -> bool:
        if (
            workspace.state
            not in {
                "discarded",
                "failed",
                "expired",
                "rolled_back",
                "recovery_required",
                "quarantined",
            }
            and workspace.expires_at <= utc_now()
            and workspace.active_attempt_id is None
        ):
            workspace.state = "expired"
            self._workspace_event(
                workspace,
                "workspace_expired",
                request_id="workspace-expiry",
                metadata={"state": workspace.state},
            )
            return True
        return False

    def _repository_response(self, handle: RepositoryHandle) -> RepositoryHandleResponse:
        runner = self._repositories.get_runner(handle.runner_id)
        if runner is None:
            raise WorkspaceServiceError(
                "runner_not_found",
                "Repository Runner was not found",
                category="internal",
            )
        return RepositoryHandleResponse(
            id=handle.id,
            runner_id=handle.runner_id,
            runner_display_name=runner.display_name,
            opaque_handle=handle.opaque_handle,
            display_name=handle.display_name,
            vcs_kind="git",
            status=handle.status,
            capabilities=handle.capabilities,
            current_revision=handle.current_revision,
            current_branch=handle.current_branch,
            source_status=handle.source_status,
            source_is_dirty=handle.source_is_dirty,
            dirty_path_count=handle.dirty_path_count,
            last_verified_at=handle.last_verified_at,
            metadata_version=1,
            created_at=handle.created_at,
            updated_at=handle.updated_at,
        )

    def _grant_response(self, grant: ExecutionGrant) -> ExecutionGrantResponse:
        handle = self._required_handle(grant.repository_handle_id)
        decision = self._repositories.grant_decision(grant.id)
        return ExecutionGrantResponse(
            id=grant.id,
            grant_version=1,
            task_id=grant.task_id,
            run_id=grant.run_id,
            plan_id=grant.plan_id,
            repository_handle_id=grant.repository_handle_id,
            repository_display_name=handle.display_name,
            runner_id=handle.runner_id,
            source_revision=grant.source_revision,
            snapshot_fingerprint=grant.snapshot_fingerprint,
            allowed_operations=grant.allowed_operations,
            allowed_paths=grant.allowed_paths,
            denied_paths=grant.denied_paths,
            max_files_changed=grant.max_files_changed,
            max_total_write_bytes=grant.max_total_write_bytes,
            max_single_file_bytes=grant.max_single_file_bytes,
            max_diff_bytes=grant.max_diff_bytes,
            workspace_ttl_seconds=grant.workspace_ttl_seconds,
            network_policy="none",
            shell_access=False,
            git_delivery_access=False,
            source_repository_write_access=False,
            status=grant.status,
            policy_hash=grant.policy_hash,
            requested_at=grant.requested_at,
            decided_at=grant.decided_at,
            revocation_requested_at=grant.revocation_requested_at,
            revoked_at=grant.revoked_at,
            in_flight_permit_count=len(self._repositories.in_flight_permits_for_grant(grant.id)),
            expires_at=grant.expires_at,
            created_at=grant.created_at,
            decision=(
                ExecutionGrantDecisionResponse.model_validate(decision)
                if decision is not None
                else None
            ),
        )

    def _workspace_response(self, workspace: Workspace) -> WorkspaceResponse:
        grant = self._repositories.get_grant(workspace.grant_id)
        handle = self._repositories.get_repository_handle(workspace.repository_handle_id)
        runner = self._repositories.get_runner(workspace.runner_id)
        if grant is None or handle is None or runner is None:
            raise WorkspaceServiceError(
                "workspace_binding_missing",
                "Workspace binding is unavailable",
                category="internal",
            )
        latest = self._repositories.latest_workspace_job(workspace.id)
        return WorkspaceResponse(
            id=workspace.id,
            grant_id=workspace.grant_id,
            runner_id=workspace.runner_id,
            runner_display_name=runner.display_name,
            repository_handle_id=workspace.repository_handle_id,
            repository_display_name=handle.display_name,
            source_revision=workspace.source_revision,
            state=workspace.state,
            workspace_fingerprint=workspace.workspace_fingerprint,
            initial_tree_hash=workspace.initial_tree_hash,
            current_tree_hash=workspace.current_tree_hash,
            changed_file_count=workspace.changed_file_count,
            total_written_bytes=workspace.total_written_bytes,
            max_files_changed=grant.max_files_changed,
            max_total_write_bytes=grant.max_total_write_bytes,
            max_single_file_bytes=grant.max_single_file_bytes,
            max_diff_bytes=grant.max_diff_bytes,
            created_paths=workspace.created_paths,
            active_attempt_id=workspace.active_attempt_id,
            expires_at=workspace.expires_at,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            sealed_at=workspace.sealed_at,
            discarded_at=workspace.discarded_at,
            error_code=workspace.error_code,
            error_message=workspace.error_message,
            latest_job_id=latest.id if latest is not None else None,
            latest_job_kind=latest.kind if latest is not None else None,
            latest_job_state=latest.state if latest is not None else None,
        )

    def _workspace_event(
        self,
        workspace: Workspace,
        event_type: str,
        *,
        request_id: str,
        metadata: dict[str, str | int | bool],
    ) -> None:
        allowed = {
            "policy_hash",
            "state",
        }
        sanitized = {
            key: value[:128] if isinstance(value, str) else value
            for key, value in metadata.items()
            if key in allowed
        }
        self._repositories.add(
            WorkspaceEvent(
                workspace_id=workspace.id,
                runner_id=workspace.runner_id,
                event_type=event_type,
                sequence=self._repositories.next_workspace_event_sequence(workspace.id),
                request_id=request_id[:128],
                details=sanitized,
            )
        )
        self._session.flush()

    @staticmethod
    def _not_found(code: str, message: str) -> NoReturn:
        raise WorkspaceServiceError(code, message, category="not_found")

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise WorkspaceServiceError(code, message, category="conflict")
