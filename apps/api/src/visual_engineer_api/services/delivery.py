from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import NoReturn

from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from visual_engineer_api.core.config import Settings, get_settings
from visual_engineer_api.models.delivery import (
    DeliveryAuthorization,
    DeliveryAuthorizationDecision,
)
from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewPackage,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    RepositoryHandle,
    Workspace,
    WorkspaceCheckpoint,
)
from visual_engineer_api.repositories.delivery import DeliveryRepository
from visual_engineer_api.repositories.review import ReviewRepository
from visual_engineer_api.repositories.workspace import WorkspaceRepository
from visual_engineer_api.schemas.delivery import (
    DeliveryAuthorizationCreate,
    DeliveryAuthorizationDecisionCreate,
    DeliveryAuthorizationDecisionResponse,
    DeliveryAuthorizationListResponse,
    DeliveryAuthorizationResponse,
    LocalDeliveryResponse,
)
from visual_engineer_api.services.review import ReviewService, ReviewServiceError
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_runner_protocol import (
    DeliveryAuthorizationPolicy,
    ExecutionGrantPolicy,
    WorkspaceGitCommitJobSpec,
    canonical_json_bytes,
    compute_delivery_authorization_policy_hash,
    compute_execution_grant_policy_hash,
    delivery_authorization_policy_hash_matches,
)


class DeliveryServiceError(Exception):
    def __init__(self, code: str, message: str, *, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


class DeliveryService:
    _EMPTY_DIFF_HASH = hashlib.sha256(b"").hexdigest()

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._deliveries = DeliveryRepository(session)
        self._reviews = ReviewRepository(session)
        self._workspaces = WorkspaceRepository(session)

    def create(
        self,
        payload: DeliveryAuthorizationCreate,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> DeliveryAuthorizationResponse:
        request_hash = self._digest(payload.model_dump(mode="json"))
        replay = self._deliveries.authorization_by_idempotency(idempotency_key, lock=True)
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "delivery_authorization_idempotency_conflict",
                    "Idempotency-Key is associated with another Delivery Authorization",
                )
            return self._response(replay)

        package, decision, readiness, workspace, checkpoint, handle = self._ready_context(
            payload.review_package_id,
            request_id=request_id,
        )
        if checkpoint.diff_hash == self._EMPTY_DIFF_HASH:
            self._conflict(
                "delivery_empty_diff",
                "Local delivery requires a non-empty reviewed Workspace diff",
            )
        existing = self._deliveries.authorization_by_package(package.id, lock=True)
        if existing is not None:
            return self._response(existing)
        grant = self._workspaces.get_grant(workspace.grant_id, lock=True)
        now = datetime.now(UTC)
        if (
            grant is None
            or grant.status != "approved"
            or grant.revocation_requested_at is not None
            or grant.expires_at <= now
            or workspace.expires_at <= now
        ):
            self._conflict(
                "delivery_execution_authority_inactive",
                "The exact Validation/Workspace authority is no longer active",
            )
        authorization_id = uuid.uuid4()
        expires_at = min(
            grant.expires_at,
            workspace.expires_at,
            now + timedelta(seconds=self._settings.delivery_authorization_ttl_seconds),
        )
        values = {
            "id": authorization_id,
            "authorization_version": 1,
            "review_package_id": package.id,
            "review_decision_id": decision.id,
            "readiness_verdict_id": readiness.id,
            "freshness_generation": package.freshness_generation,
            "package_digest": package.package_digest,
            "decision_digest": decision.decision_digest,
            "readiness_digest": readiness.verdict_digest,
            "workspace_id": workspace.id,
            "checkpoint_id": checkpoint.id,
            "checkpoint_fingerprint": checkpoint.tree_fingerprint,
            "checkpoint_diff_hash": checkpoint.diff_hash,
            "repository_handle_id": handle.id,
            "source_revision": package.source_revision,
            "branch_ref": f"refs/heads/visual-engineer/{workspace.id.hex}",
            "commit_message": (
                f"VisualEngineer: governed local delivery {authorization_id.hex[:8]}"
            ),
            "commit_timestamp": now,
            "local_git_commit_access": True,
            "remote_access": False,
            "push_access": False,
            "pull_request_access": False,
            "tag_access": False,
            "deployment_access": False,
            "source_repository_write_access": False,
            "expires_at": expires_at,
            "policy_hash": "0" * 64,
        }
        draft = DeliveryAuthorizationPolicy.model_validate(values)
        values["policy_hash"] = compute_delivery_authorization_policy_hash(draft)
        policy = DeliveryAuthorizationPolicy.model_validate(values)
        authorization = DeliveryAuthorization(
            id=authorization_id,
            authorization_version=1,
            review_package_id=package.id,
            review_decision_id=decision.id,
            readiness_verdict_id=readiness.id,
            freshness_generation=package.freshness_generation,
            package_digest=package.package_digest,
            decision_digest=decision.decision_digest,
            readiness_digest=readiness.verdict_digest,
            execution_grant_id=grant.id,
            workspace_id=workspace.id,
            checkpoint_id=checkpoint.id,
            checkpoint_fingerprint=checkpoint.tree_fingerprint,
            checkpoint_diff_hash=checkpoint.diff_hash,
            repository_handle_id=handle.id,
            source_revision=package.source_revision,
            branch_ref=policy.branch_ref,
            commit_message=policy.commit_message,
            local_git_commit_access=True,
            remote_access=False,
            push_access=False,
            pull_request_access=False,
            tag_access=False,
            deployment_access=False,
            source_repository_write_access=False,
            status="pending",
            policy_hash=policy.policy_hash,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
            created_at=now,
            expires_at=expires_at,
        )
        self._deliveries.add(authorization)
        self._audit(
            package.run_id,
            package.id,
            "delivery_authorization_created",
            request_id=request_id,
            actor_type="system",
            details={
                "delivery_authorization_id": str(authorization.id),
                "policy_hash": authorization.policy_hash,
                "workspace_id": str(workspace.id),
                "checkpoint_id": str(checkpoint.id),
                "local_git_commit_access": True,
                "remote_access": False,
            },
        )
        try:
            self._session.commit()
        except DBAPIError as exc:
            self._session.rollback()
            winner = self._deliveries.authorization_by_package(package.id)
            if winner is not None:
                return self._response(winner)
            raise DeliveryServiceError(
                "delivery_authorization_conflict",
                "A concurrent Delivery Authorization request won",
                category="conflict",
            ) from exc
        return self._response(self._required(authorization.id))

    def decide(
        self,
        authorization_id: uuid.UUID,
        payload: DeliveryAuthorizationDecisionCreate,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> DeliveryAuthorizationResponse:
        authorization = self._required(authorization_id, lock=True)
        reason = payload.reason.strip() if payload.reason is not None else None
        request_payload = {
            "delivery_authorization_id": str(authorization.id),
            "authorization_policy_hash": authorization.policy_hash,
            "decision": payload.decision,
            "reason": reason,
            "actor_type": "local_user",
        }
        request_hash = self._digest(request_payload)
        replay = self._deliveries.decision_by_idempotency(idempotency_key, lock=True)
        if replay is not None:
            if (
                replay.delivery_authorization_id != authorization.id
                or replay.idempotency_request_hash != request_hash
            ):
                self._conflict(
                    "delivery_decision_idempotency_conflict",
                    "Idempotency-Key is associated with another Delivery Decision",
                )
            return self._response(authorization)
        existing = self._deliveries.decision(authorization.id, lock=True)
        if existing is not None:
            self._conflict(
                "delivery_decision_conflict",
                "Delivery Authorization already has one immutable decision",
            )
        now = datetime.now(UTC)
        if authorization.status != "pending":
            self._conflict(
                "delivery_authorization_not_pending",
                "Delivery Authorization is not pending a decision",
            )
        if authorization.expires_at <= now:
            authorization.status = "stale"
            authorization.decided_at = now
            authorization.terminal_at = now
            authorization.error_code = "delivery_authorization_expired"
            self._session.commit()
            self._conflict(
                "delivery_authorization_expired",
                "Delivery Authorization expired before decision",
            )
        self._assert_authorization_ready(authorization, request_id=request_id)
        decision_id = uuid.uuid4()
        decision_payload = {
            "delivery_decision_id": str(decision_id),
            **request_payload,
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": request_hash,
            "local_git_commit_authorized": payload.decision == "approve",
            "remote_access": False,
            "push_access": False,
            "pull_request_access": False,
            "tag_access": False,
            "deployment_access": False,
        }
        decision = DeliveryAuthorizationDecision(
            id=decision_id,
            delivery_authorization_id=authorization.id,
            authorization_policy_hash=authorization.policy_hash,
            decision=payload.decision,
            reason=reason,
            actor_type="local_user",
            request_id=request_id,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
            decision_digest=self._digest(decision_payload),
            local_git_commit_authorized=payload.decision == "approve",
            remote_access=False,
            push_access=False,
            pull_request_access=False,
            tag_access=False,
            deployment_access=False,
        )
        self._deliveries.add(decision)
        authorization.status = "approved" if payload.decision == "approve" else "rejected"
        authorization.decided_at = now
        if payload.decision == "reject":
            authorization.terminal_at = now
        self._audit(
            self._package_run_id(authorization.review_package_id),
            authorization.review_package_id,
            "delivery_decision_recorded",
            request_id=request_id,
            actor_type="local_user",
            details={
                "delivery_authorization_id": str(authorization.id),
                "decision": payload.decision,
                "local_git_commit_authorized": payload.decision == "approve",
                "remote_access": False,
            },
        )
        try:
            self._session.commit()
        except DBAPIError as exc:
            self._session.rollback()
            winner = self._deliveries.decision_by_idempotency(idempotency_key)
            if (
                winner is not None
                and winner.delivery_authorization_id == authorization.id
                and winner.idempotency_request_hash == request_hash
            ):
                return self._response(self._required(authorization.id))
            raise DeliveryServiceError(
                "delivery_decision_conflict",
                "A concurrent Delivery Decision won",
                category="conflict",
            ) from exc
        return self._response(self._required(authorization.id))

    def dispatch(
        self,
        authorization_id: uuid.UUID,
        *,
        request_id: str,
    ) -> DeliveryAuthorizationResponse:
        authorization = self._required(authorization_id, lock=True)
        existing_job = self._deliveries.job(authorization.id, lock=True)
        if existing_job is not None:
            return self._response(authorization)
        decision = self._deliveries.decision(authorization.id, lock=True)
        now = datetime.now(UTC)
        if (
            authorization.status != "approved"
            or decision is None
            or decision.decision != "approve"
            or not decision.local_git_commit_authorized
        ):
            self._conflict(
                "delivery_authorization_not_approved",
                "Local delivery requires one approved Delivery Authorization",
            )
        if authorization.expires_at <= now:
            self._mark_stale(authorization, "delivery_authorization_expired", now)
            self._session.commit()
            self._conflict(
                "delivery_authorization_expired",
                "Delivery Authorization expired before dispatch",
            )
        self._assert_authorization_ready(authorization, request_id=request_id)
        grant = self._workspaces.get_grant(authorization.execution_grant_id, lock=True)
        handle = self._workspaces.get_repository_handle(
            authorization.repository_handle_id,
            lock=True,
        )
        if grant is None or handle is None:
            self._conflict(
                "delivery_execution_authority_missing",
                "Delivery execution authority is missing",
            )
        execution_policy = self._execution_policy(grant, handle)
        delivery_policy = self._delivery_policy(authorization)
        spec = WorkspaceGitCommitJobSpec(
            workspace_id=authorization.workspace_id,
            execution_grant=execution_policy,
            delivery_authorization=delivery_policy,
            checkpoint_id=authorization.checkpoint_id,
            checkpoint_fingerprint=authorization.checkpoint_fingerprint,
            checkpoint_diff_hash=authorization.checkpoint_diff_hash,
        )
        authorization.status = "dispatched"
        authorization.dispatched_at = now
        self._audit(
            self._package_run_id(authorization.review_package_id),
            authorization.review_package_id,
            "local_delivery_dispatched",
            request_id=request_id,
            actor_type="system",
            details={
                "delivery_authorization_id": str(authorization.id),
                "workspace_id": str(authorization.workspace_id),
                "checkpoint_id": str(authorization.checkpoint_id),
                "remote_access": False,
            },
        )
        try:
            RunnerService(self._session, self._settings).create_workspace_job(
                spec,
                request_id=request_id,
            )
        except RunnerServiceError as exc:
            self._session.rollback()
            raise DeliveryServiceError(exc.code, exc.message, category=exc.category) from exc
        return self._response(self._required(authorization.id))

    def list(self) -> DeliveryAuthorizationListResponse:
        items = [self._response(item) for item in self._deliveries.list_authorizations()]
        return DeliveryAuthorizationListResponse(items=items, total=len(items))

    def get(self, authorization_id: uuid.UUID) -> DeliveryAuthorizationResponse:
        return self._response(self._required(authorization_id))

    def _assert_authorization_ready(
        self,
        authorization: DeliveryAuthorization,
        *,
        request_id: str,
    ) -> None:
        try:
            package, decision, readiness, workspace, checkpoint, handle = self._ready_context(
                authorization.review_package_id,
                request_id=request_id,
            )
        except DeliveryServiceError as exc:
            if authorization.status in {"pending", "approved"}:
                self._mark_stale(authorization, exc.code, datetime.now(UTC))
                self._session.commit()
            raise
        if (
            package.id != authorization.review_package_id
            or decision.id != authorization.review_decision_id
            or readiness.id != authorization.readiness_verdict_id
            or package.freshness_generation != authorization.freshness_generation
            or package.package_digest != authorization.package_digest
            or decision.decision_digest != authorization.decision_digest
            or readiness.verdict_digest != authorization.readiness_digest
            or workspace.id != authorization.workspace_id
            or checkpoint.id != authorization.checkpoint_id
            or checkpoint.tree_fingerprint != authorization.checkpoint_fingerprint
            or checkpoint.diff_hash != authorization.checkpoint_diff_hash
            or handle.id != authorization.repository_handle_id
            or package.source_revision != authorization.source_revision
            or not delivery_authorization_policy_hash_matches(
                self._delivery_policy(authorization),
                authorization.policy_hash,
            )
        ):
            self._mark_stale(
                authorization,
                "delivery_authorization_stale",
                datetime.now(UTC),
            )
            self._session.commit()
            self._conflict(
                "delivery_authorization_stale",
                "Delivery Authorization no longer matches the ready Review baseline",
            )

    def _ready_context(
        self,
        package_id: uuid.UUID,
        *,
        request_id: str,
    ) -> tuple[
        ReviewPackage,
        ReviewDecision,
        ReleaseReadinessVerdict,
        Workspace,
        WorkspaceCheckpoint,
        RepositoryHandle,
    ]:
        try:
            return ReviewService(self._session).require_delivery_ready(
                package_id,
                request_id=request_id,
            )
        except ReviewServiceError as exc:
            raise DeliveryServiceError(exc.code, exc.message, category=exc.category) from exc

    def _delivery_policy(
        self,
        authorization: DeliveryAuthorization,
    ) -> DeliveryAuthorizationPolicy:
        try:
            return DeliveryAuthorizationPolicy(
                id=authorization.id,
                authorization_version=authorization.authorization_version,
                review_package_id=authorization.review_package_id,
                review_decision_id=authorization.review_decision_id,
                readiness_verdict_id=authorization.readiness_verdict_id,
                freshness_generation=authorization.freshness_generation,
                package_digest=authorization.package_digest,
                decision_digest=authorization.decision_digest,
                readiness_digest=authorization.readiness_digest,
                workspace_id=authorization.workspace_id,
                checkpoint_id=authorization.checkpoint_id,
                checkpoint_fingerprint=authorization.checkpoint_fingerprint,
                checkpoint_diff_hash=authorization.checkpoint_diff_hash,
                repository_handle_id=authorization.repository_handle_id,
                source_revision=authorization.source_revision,
                branch_ref=authorization.branch_ref,
                commit_message=authorization.commit_message,
                commit_timestamp=authorization.created_at,
                local_git_commit_access=authorization.local_git_commit_access,
                remote_access=authorization.remote_access,
                push_access=authorization.push_access,
                pull_request_access=authorization.pull_request_access,
                tag_access=authorization.tag_access,
                deployment_access=authorization.deployment_access,
                source_repository_write_access=(authorization.source_repository_write_access),
                expires_at=authorization.expires_at,
                policy_hash=authorization.policy_hash,
            )
        except ValidationError as exc:
            raise DeliveryServiceError(
                "delivery_authorization_invalid",
                "Stored Delivery Authorization policy is invalid",
                category="policy",
            ) from exc

    @staticmethod
    def _execution_policy(
        grant: ExecutionGrant,
        handle: RepositoryHandle,
    ) -> ExecutionGrantPolicy:
        values = {
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
            "validation_workspace_id": grant.validation_workspace_id,
            "validation_checkpoint_id": grant.validation_checkpoint_id,
            "allowed_validation_profiles": grant.allowed_validation_profiles,
            "allowed_validation_suites": grant.allowed_validation_suites,
            "validation_suite_definition_digest": grant.validation_suite_definition_digest,
            "validation_suite_root_run_id": grant.validation_suite_root_run_id,
            "validation_suite_retry_of_run_id": grant.validation_suite_retry_of_run_id,
            "validation_suite_attempt_number": grant.validation_suite_attempt_number,
            "validation_suite_allowed_run_count": grant.validation_suite_allowed_run_count,
            "max_validation_runs": grant.max_validation_runs,
            "validation_timeout_seconds": grant.validation_timeout_seconds,
            "validation_cpu_seconds": grant.validation_cpu_seconds,
            "validation_memory_bytes": grant.validation_memory_bytes,
            "validation_pid_limit": grant.validation_pid_limit,
            "validation_fd_limit": grant.validation_fd_limit,
            "validation_output_bytes": grant.validation_output_bytes,
            "validation_artifact_bytes": grant.validation_artifact_bytes,
            "validation_artifact_count": grant.validation_artifact_count,
            "expires_at": grant.expires_at,
            "policy_hash": grant.policy_hash,
        }
        policy = ExecutionGrantPolicy.model_validate(values)
        if compute_execution_grant_policy_hash(policy) != grant.policy_hash:
            raise DeliveryServiceError(
                "execution_grant_hash_mismatch",
                "Execution Grant policy hash is invalid",
                category="policy",
            )
        return policy

    def _response(
        self,
        authorization: DeliveryAuthorization,
    ) -> DeliveryAuthorizationResponse:
        decision = self._deliveries.decision(authorization.id)
        local_delivery = self._deliveries.local_delivery(authorization.id)
        job = self._deliveries.job(authorization.id)
        return DeliveryAuthorizationResponse(
            id=authorization.id,
            authorization_version=authorization.authorization_version,
            review_package_id=authorization.review_package_id,
            review_decision_id=authorization.review_decision_id,
            readiness_verdict_id=authorization.readiness_verdict_id,
            freshness_generation=authorization.freshness_generation,
            package_digest=authorization.package_digest,
            decision_digest=authorization.decision_digest,
            readiness_digest=authorization.readiness_digest,
            execution_grant_id=authorization.execution_grant_id,
            workspace_id=authorization.workspace_id,
            checkpoint_id=authorization.checkpoint_id,
            checkpoint_fingerprint=authorization.checkpoint_fingerprint,
            checkpoint_diff_hash=authorization.checkpoint_diff_hash,
            repository_handle_id=authorization.repository_handle_id,
            source_revision=authorization.source_revision,
            branch_ref=authorization.branch_ref,
            commit_message=authorization.commit_message,
            local_git_commit_access=True,
            remote_access=False,
            push_access=False,
            pull_request_access=False,
            tag_access=False,
            deployment_access=False,
            source_repository_write_access=False,
            status=authorization.status,
            policy_hash=authorization.policy_hash,
            created_at=authorization.created_at,
            decided_at=authorization.decided_at,
            dispatched_at=authorization.dispatched_at,
            terminal_at=authorization.terminal_at,
            expires_at=authorization.expires_at,
            error_code=authorization.error_code,
            decision=(
                DeliveryAuthorizationDecisionResponse.model_validate(decision)
                if decision is not None
                else None
            ),
            job=(
                RunnerService(self._session, self._settings).get_job(job.id)
                if job is not None
                else None
            ),
            delivery=(
                LocalDeliveryResponse.model_validate(local_delivery)
                if local_delivery is not None
                else None
            ),
        )

    def _audit(
        self,
        run_id: uuid.UUID,
        package_id: uuid.UUID,
        event_type: str,
        *,
        request_id: str,
        actor_type: str,
        details: dict[str, object],
    ) -> None:
        self._session.add(
            AuditEvent(
                run_id=run_id,
                event_type=event_type,
                actor_type=actor_type,
                request_id=request_id,
                details={
                    "review_package_id": str(package_id),
                    **details,
                },
                review_package_id=package_id,
                review_sequence=self._reviews.next_review_event_sequence(package_id),
            )
        )

    def _package_run_id(self, package_id: uuid.UUID) -> uuid.UUID:
        package = self._reviews.package(package_id)
        if package is None:
            self._not_found("review_package_not_found", "Review Package was not found")
        return package.run_id

    def _required(
        self,
        authorization_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> DeliveryAuthorization:
        authorization = self._deliveries.authorization(authorization_id, lock=lock)
        if authorization is None:
            self._not_found(
                "delivery_authorization_not_found",
                "Delivery Authorization was not found",
            )
        return authorization

    @staticmethod
    def _digest(value: object) -> str:
        return hashlib.sha256(canonical_json_bytes({"value": value})).hexdigest()

    @staticmethod
    def _mark_stale(
        authorization: DeliveryAuthorization,
        code: str,
        now: datetime,
    ) -> None:
        authorization.status = "stale"
        authorization.decided_at = authorization.decided_at or now
        authorization.terminal_at = now
        authorization.error_code = code

    @staticmethod
    def _not_found(code: str, message: str) -> NoReturn:
        raise DeliveryServiceError(code, message, category="not_found")

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise DeliveryServiceError(code, message, category="conflict")
