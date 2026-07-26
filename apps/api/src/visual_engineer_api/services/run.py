import hashlib
import json
import time
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from visual_engineer_api.core.config import get_settings
from visual_engineer_api.core.observability import log_governance_event
from visual_engineer_api.models.run import (
    ApprovalDecision,
    AuditEvent,
    Plan,
    RepositorySnapshot,
    Run,
)
from visual_engineer_api.repositories.run import RunRepository
from visual_engineer_api.repositories.task import TaskRepository
from visual_engineer_api.repository_intelligence import RepositoryScanError, RepositoryScanner
from visual_engineer_api.schemas.run import (
    DecisionKind,
    DeliveryPackage,
    PlanDecisionCreate,
    PlanRevisionCreate,
    RunCreate,
)
from visual_engineer_api.services.deterministic_plan import (
    PlanPolicyViolationError,
    generate_deterministic_plan,
    plan_content_hash,
    validate_plan_for_submission,
    validate_plan_revision,
)
from visual_engineer_api.services.run_state import InvalidRunTransitionError, transition_run


class RunServiceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        category: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category
        self.details = details


def _run_fingerprint(task_id: uuid.UUID, payload: RunCreate) -> str:
    canonical = json.dumps(
        {"task_id": str(task_id), **payload.model_dump(mode="json")},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RunService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._runs = RunRepository(session)
        self._tasks = TaskRepository(session)

    def create_run(
        self,
        task_id: uuid.UUID,
        payload: RunCreate,
        *,
        request_id: str,
        idempotency_key: str | None,
    ) -> tuple[Run, bool]:
        task = self._tasks.get_by_id(task_id)
        if task is None:
            raise RunServiceError("task_not_found", "Task was not found", category="not_found")
        fingerprint = _run_fingerprint(task_id, payload)
        if idempotency_key is not None:
            existing = self._runs.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                if existing.idempotency_request_hash != fingerprint:
                    raise RunServiceError(
                        "run_idempotency_conflict",
                        "Idempotency-Key is already associated with a different Run request",
                        category="conflict",
                    )
                return existing, True

        run = Run(
            task_id=task_id,
            permission_level=payload.permission_level,
            snapshot_mode=payload.snapshot_mode,
            idempotency_key=idempotency_key,
            idempotency_request_hash=fingerprint if idempotency_key is not None else None,
        )
        self._runs.add(run)
        self._session.flush()
        self._audit(
            run,
            "run_created",
            "local_user",
            request_id,
            {
                "permission_level": "read_only",
                "snapshot_mode": "git_head",
            },
        )
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            if idempotency_key is None:
                raise
            winner = self._runs.get_by_idempotency_key(idempotency_key)
            if winner is None:
                raise
            if winner.idempotency_request_hash != fingerprint:
                raise RunServiceError(
                    "run_idempotency_conflict",
                    "Idempotency-Key is already associated with a different Run request",
                    category="conflict",
                ) from None
            return winner, True
        self._session.refresh(run)
        log_governance_event("run_created", run, request_id=request_id)
        return run, False

    def get_run(self, run_id: uuid.UUID) -> Run:
        run = self._runs.get(run_id)
        if run is None:
            raise RunServiceError("run_not_found", "Run was not found", category="not_found")
        return run

    def list_runs(self, task_id: uuid.UUID) -> tuple[list[Run], int]:
        if self._tasks.get_by_id(task_id) is None:
            raise RunServiceError("task_not_found", "Task was not found", category="not_found")
        return self._runs.list_by_task(task_id)

    def create_snapshot(
        self, run_id: uuid.UUID, *, request_id: str
    ) -> tuple[RepositorySnapshot, bool]:
        run = self._locked_run(run_id)
        existing = self._runs.get_snapshot(run_id)
        if existing is not None:
            return existing, True
        if run.status != "created":
            raise self._state_conflict(run, "snapshotting")
        task = self._tasks.get_by_id(run.task_id)
        if task is None:
            raise RunServiceError("task_not_found", "Task was not found", category="not_found")
        if task.repository_kind != "local_path":
            self._policy_denied(
                run,
                request_id=request_id,
                reason_code="repository_kind_not_supported",
            )
            self._session.commit()
            raise RunServiceError(
                "repository_kind_not_supported",
                "Phase 2 can snapshot only allowlisted local Git repositories",
                category="policy",
            )

        transition_run(run, "snapshotting")
        self._audit(run, "snapshot_started", "local_user", request_id, {"mode": "git_head"})
        self._session.commit()
        log_governance_event("snapshot_started", run, request_id=request_id)

        started = time.perf_counter()
        try:
            result = RepositoryScanner(get_settings()).scan(task.repository_locator)
        except RepositoryScanError as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            failed_run = self._locked_run(run_id)
            if failed_run.status == "snapshotting":
                transition_run(failed_run, "failed")
                failed_run.error_code = exc.code
                failed_run.error_message = exc.public_message[:500]
                self._audit(
                    failed_run,
                    "snapshot_failed",
                    "system",
                    request_id,
                    {"reason_code": exc.code, "duration_ms": round(duration_ms, 2)},
                )
                self._policy_denied(
                    failed_run,
                    request_id=request_id,
                    reason_code=exc.code,
                )
                self._session.commit()
            log_governance_event(
                "snapshot_failed",
                failed_run,
                request_id=request_id,
                duration_ms=duration_ms,
                policy_denial_reason_code=exc.code,
            )
            raise RunServiceError(exc.code, exc.public_message, category="policy") from exc
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            failed_run = self._locked_run(run_id)
            if failed_run.status == "snapshotting":
                transition_run(failed_run, "failed")
                failed_run.error_code = "repository_scan_failed"
                failed_run.error_message = "Repository scan failed safely"
                self._audit(
                    failed_run,
                    "snapshot_failed",
                    "system",
                    request_id,
                    {
                        "reason_code": "repository_scan_failed",
                        "duration_ms": round(duration_ms, 2),
                    },
                )
                self._session.commit()
            log_governance_event(
                "snapshot_failed",
                failed_run,
                request_id=request_id,
                duration_ms=duration_ms,
                policy_denial_reason_code="repository_scan_failed",
            )
            raise

        run = self._locked_run(run_id)
        raced_snapshot = self._runs.get_snapshot(run_id)
        if raced_snapshot is not None:
            return raced_snapshot, True
        if run.status != "snapshotting":
            raise self._state_conflict(run, "snapshot_ready")
        snapshot = RepositorySnapshot(run_id=run_id, **result.model_values())
        self._runs.add(snapshot)
        self._session.flush()
        transition_run(run, "snapshot_ready")
        duration_ms = (time.perf_counter() - started) * 1000
        self._audit(
            run,
            "snapshot_completed",
            "system",
            request_id,
            {
                "snapshot_id": str(snapshot.id),
                "fingerprint": snapshot.fingerprint,
                "tracked_file_count": snapshot.tracked_file_count,
                "selected_file_count": snapshot.selected_file_count,
                "duration_ms": round(duration_ms, 2),
            },
        )
        self._session.commit()
        self._session.refresh(snapshot)
        log_governance_event(
            "snapshot_completed",
            run,
            request_id=request_id,
            duration_ms=duration_ms,
            snapshot_id=snapshot.id,
        )
        return snapshot, False

    def get_snapshot(self, run_id: uuid.UUID) -> RepositorySnapshot:
        self.get_run(run_id)
        snapshot = self._runs.get_snapshot(run_id)
        if snapshot is None:
            raise RunServiceError(
                "snapshot_not_found", "Snapshot was not found", category="not_found"
            )
        return snapshot

    def create_plan(
        self,
        run_id: uuid.UUID,
        delivery_package: DeliveryPackage,
        *,
        request_id: str,
    ) -> tuple[Plan, bool]:
        run = self._locked_run(run_id)
        snapshot = self._runs.get_snapshot(run_id)
        if snapshot is None:
            raise RunServiceError(
                "snapshot_required",
                "A successful committed-HEAD Snapshot is required",
                category="conflict",
            )
        latest = self._runs.latest_plan(run_id, lock=True)
        if latest is not None:
            if (
                latest.status == "draft"
                and latest.delivery_package == delivery_package.value
                and run.current_plan_version == latest.version
            ):
                return latest, True
            raise RunServiceError(
                "plan_already_exists",
                "Use the revision endpoint to create another Plan version",
                category="conflict",
            )
        if run.status != "snapshot_ready":
            raise self._state_conflict(run, "plan_ready")
        task = self._tasks.get_by_id(run.task_id)
        if task is None:
            raise RunServiceError("task_not_found", "Task was not found", category="not_found")
        generated = generate_deterministic_plan(task, snapshot, delivery_package)
        values = generated.values()
        plan = Plan(
            run_id=run_id,
            version=1,
            status="draft",
            source="deterministic_policy",
            snapshot_fingerprint=snapshot.fingerprint,
            delivery_package=delivery_package.value,
            execution_available=False,
            content_hash=plan_content_hash(
                values,
                snapshot_fingerprint=snapshot.fingerprint,
                delivery_package=delivery_package.value,
            ),
            **values,
        )
        self._runs.add(plan)
        self._session.flush()
        run.current_plan_version = 1
        transition_run(run, "plan_ready")
        self._audit(
            run,
            "plan_created",
            "system",
            request_id,
            {
                "plan_id": str(plan.id),
                "plan_version": 1,
                "source": "deterministic_policy",
            },
        )
        self._session.commit()
        self._session.refresh(plan)
        log_governance_event("plan_created", run, request_id=request_id, plan_version=plan.version)
        return plan, False

    def list_plans(self, run_id: uuid.UUID) -> tuple[list[Plan], int]:
        self.get_run(run_id)
        return self._runs.list_plans(run_id)

    def get_plan(self, run_id: uuid.UUID, version: int) -> Plan:
        self.get_run(run_id)
        plan = self._runs.get_plan(run_id, version)
        if plan is None:
            raise RunServiceError(
                "plan_not_found", "Plan version was not found", category="not_found"
            )
        return plan

    def revise_plan(
        self,
        run_id: uuid.UUID,
        version: int,
        payload: PlanRevisionCreate,
        *,
        request_id: str,
    ) -> Plan:
        run = self._locked_run(run_id)
        plan = self._runs.get_plan(run_id, version, lock=True)
        if plan is None:
            raise RunServiceError(
                "plan_not_found", "Plan version was not found", category="not_found"
            )
        latest = self._runs.latest_plan(run_id, lock=True)
        if (
            latest is None
            or latest.id != plan.id
            or run.current_plan_version != version
            or plan.status != "draft"
        ):
            raise RunServiceError(
                "stale_plan_version",
                "Only the latest draft Plan can be revised",
                category="conflict",
            )
        if run.status == "approved":
            raise RunServiceError(
                "approved_run_is_terminal",
                "An approved Run cannot create a new Plan version",
                category="conflict",
            )
        if run.status != "plan_ready":
            raise self._state_conflict(run, "plan_ready")

        try:
            validate_plan_revision(payload)
        except PlanPolicyViolationError as exc:
            self._policy_denied(
                run,
                request_id=request_id,
                reason_code="plan_revision_policy_violation",
                metadata={"violation_rules": sorted({item["rule"] for item in exc.violations})},
            )
            self._session.commit()
            raise RunServiceError(
                "plan_policy_violation",
                "Plan revision violates the Phase 2 policy boundary",
                category="policy",
                details=exc.violations,
            ) from exc

        editable = {
            "objective_summary": plan.objective_summary,
            "proposed_change_scope": plan.proposed_change_scope,
            "explicit_non_goals": plan.explicit_non_goals,
            "assumptions": plan.assumptions,
            "acceptance_criteria": plan.acceptance_criteria,
            "evidence_requirements": plan.evidence_requirements,
            "stop_conditions": plan.stop_conditions,
        }
        editable.update(payload.model_dump(exclude_none=True))
        values: dict[str, Any] = {
            **editable,
            "repository_context_summary": plan.repository_context_summary,
            "risk_items": plan.risk_items,
            "validation_steps": plan.validation_steps,
            "required_future_permission_level": plan.required_future_permission_level,
        }
        new_version = version + 1
        revised = Plan(
            run_id=run_id,
            version=new_version,
            status="draft",
            source="deterministic_policy",
            snapshot_fingerprint=plan.snapshot_fingerprint,
            delivery_package=plan.delivery_package,
            execution_available=False,
            content_hash=plan_content_hash(
                values,
                snapshot_fingerprint=plan.snapshot_fingerprint,
                delivery_package=plan.delivery_package,
            ),
            **values,
        )
        plan.status = "superseded"
        self._runs.add(revised)
        self._session.flush()
        run.current_plan_version = new_version
        run.version += 1
        self._audit(
            run,
            "plan_revised",
            "local_user",
            request_id,
            {
                "superseded_version": version,
                "plan_version": new_version,
                "changed_fields": sorted(payload.model_dump(exclude_none=True)),
            },
        )
        self._session.commit()
        self._session.refresh(revised)
        log_governance_event("plan_revised", run, request_id=request_id, plan_version=new_version)
        return revised

    def submit_plan(self, run_id: uuid.UUID, version: int, *, request_id: str) -> Plan:
        run = self._locked_run(run_id)
        plan = self._runs.get_plan(run_id, version, lock=True)
        if plan is None:
            raise RunServiceError(
                "plan_not_found", "Plan version was not found", category="not_found"
            )
        if (
            run.status == "awaiting_plan_approval"
            and run.current_plan_version == version
            and plan.status == "awaiting_approval"
        ):
            return plan
        latest = self._runs.latest_plan(run_id, lock=True)
        if (
            latest is None
            or latest.id != plan.id
            or run.current_plan_version != version
            or plan.status != "draft"
        ):
            raise RunServiceError(
                "stale_plan_version",
                "Only the latest draft Plan can be submitted",
                category="conflict",
            )
        if run.status != "plan_ready":
            raise self._state_conflict(run, "awaiting_plan_approval")
        try:
            validate_plan_for_submission(plan)
        except PlanPolicyViolationError as exc:
            self._policy_denied(
                run,
                request_id=request_id,
                reason_code="plan_submission_policy_violation",
                metadata={"violation_rules": sorted({item["rule"] for item in exc.violations})},
            )
            self._session.commit()
            raise RunServiceError(
                "plan_policy_violation",
                "Plan violates the Phase 2 policy boundary",
                category="policy",
                details=exc.violations,
            ) from exc
        plan.status = "awaiting_approval"
        transition_run(run, "awaiting_plan_approval")
        self._audit(
            run,
            "plan_submitted",
            "local_user",
            request_id,
            {
                "plan_id": str(plan.id),
                "plan_version": version,
                "content_hash": plan.content_hash,
            },
        )
        self._session.commit()
        self._session.refresh(plan)
        log_governance_event("plan_submitted", run, request_id=request_id, plan_version=version)
        return plan

    def decide_plan(
        self,
        run_id: uuid.UUID,
        version: int,
        payload: PlanDecisionCreate,
        *,
        request_id: str,
    ) -> tuple[ApprovalDecision, bool]:
        run = self._locked_run(run_id)
        plan = self._runs.get_plan(run_id, version, lock=True)
        if plan is None:
            raise RunServiceError(
                "plan_not_found", "Plan version was not found", category="not_found"
            )
        existing = self._runs.get_decision(plan.id)
        if existing is not None:
            if existing.decision == payload.decision.value and existing.comment == payload.comment:
                return existing, True
            raise RunServiceError(
                "decision_conflict",
                "A different final decision already exists for this Plan",
                category="conflict",
            ) from None
        latest = self._runs.latest_plan(run_id, lock=True)
        if (
            latest is None
            or latest.id != plan.id
            or run.current_plan_version != version
            or plan.status != "awaiting_approval"
        ):
            raise RunServiceError(
                "stale_plan_decision",
                "Only the latest awaiting Plan can receive a decision",
                category="conflict",
            )
        if run.status != "awaiting_plan_approval":
            raise self._state_conflict(
                run,
                "approved" if payload.decision == DecisionKind.APPROVE else "rejected",
            )

        decision = ApprovalDecision(
            run_id=run_id,
            plan_id=plan.id,
            decision=payload.decision.value,
            comment=payload.comment,
            actor_type="local_user",
            request_id=request_id,
        )
        self._runs.add(decision)
        plan.status = "approved" if payload.decision == DecisionKind.APPROVE else "rejected"
        target_status = "approved" if payload.decision == DecisionKind.APPROVE else "rejected"
        transition_run(run, target_status)
        self._audit(
            run,
            "plan_approved" if target_status == "approved" else "plan_rejected",
            "local_user",
            request_id,
            {
                "plan_id": str(plan.id),
                "plan_version": version,
                "comment_provided": payload.comment is not None,
                "execution_available": False,
            },
        )
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            winner_plan = self._runs.get_plan(run_id, version)
            if winner_plan is None:
                raise
            winner = self._runs.get_decision(winner_plan.id)
            if (
                winner is not None
                and winner.decision == payload.decision.value
                and winner.comment == payload.comment
            ):
                return winner, True
            raise RunServiceError(
                "decision_conflict",
                "A different final decision already exists for this Plan",
                category="conflict",
            ) from None
        self._session.refresh(decision)
        log_governance_event(
            "plan_approved" if target_status == "approved" else "plan_rejected",
            run,
            request_id=request_id,
            plan_version=version,
        )
        return decision, False

    def cancel_run(self, run_id: uuid.UUID, *, request_id: str, reason_provided: bool) -> Run:
        run = self._locked_run(run_id)
        if run.status == "cancelled":
            return run
        if run.status in {"approved", "rejected", "failed"}:
            raise RunServiceError(
                "run_terminal",
                "A terminal Run cannot be cancelled",
                category="conflict",
            )
        try:
            transition_run(run, "cancelled")
        except InvalidRunTransitionError as exc:
            raise self._state_conflict(run, "cancelled") from exc
        latest = self._runs.latest_plan(run_id, lock=True)
        if latest is not None and latest.status in {"draft", "awaiting_approval"}:
            latest.status = "superseded"
        self._audit(
            run,
            "run_cancelled",
            "local_user",
            request_id,
            {"reason_provided": reason_provided},
        )
        self._session.commit()
        self._session.refresh(run)
        log_governance_event("run_cancelled", run, request_id=request_id)
        return run

    def list_audit_events(self, run_id: uuid.UUID) -> tuple[list[AuditEvent], int]:
        self.get_run(run_id)
        return self._runs.list_audit_events(run_id)

    def _locked_run(self, run_id: uuid.UUID) -> Run:
        run = self._runs.get(run_id, lock=True)
        if run is None:
            raise RunServiceError("run_not_found", "Run was not found", category="not_found")
        return run

    @staticmethod
    def _state_conflict(run: Run, target: str) -> RunServiceError:
        return RunServiceError(
            "invalid_run_transition",
            f"Run cannot transition from {run.status} to {target}",
            category="conflict",
        )

    def _audit(
        self,
        run: Run,
        event_type: str,
        actor_type: str,
        request_id: str,
        metadata: dict[str, Any],
    ) -> None:
        self._runs.add(
            AuditEvent(
                run_id=run.id,
                event_type=event_type,
                actor_type=actor_type,
                request_id=request_id,
                details=_sanitize_metadata(metadata),
            )
        )

    def _policy_denied(
        self,
        run: Run,
        *,
        request_id: str,
        reason_code: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit(
            run,
            "policy_denied",
            "system",
            request_id,
            {"reason_code": reason_code, **(metadata or {})},
        )
        log_governance_event(
            "policy_denied",
            run,
            request_id=request_id,
            policy_denial_reason_code=reason_code,
        )


def _sanitize_metadata(value: dict[str, Any]) -> dict[str, Any]:
    allowed: dict[str, Any] = {}
    for key, item in value.items():
        if key not in {
            "changed_fields",
            "comment_provided",
            "content_hash",
            "duration_ms",
            "execution_available",
            "fingerprint",
            "mode",
            "permission_level",
            "plan_id",
            "plan_version",
            "reason_code",
            "reason_provided",
            "selected_file_count",
            "snapshot_id",
            "snapshot_mode",
            "source",
            "superseded_version",
            "tracked_file_count",
            "violation_rules",
        }:
            continue
        if isinstance(item, str):
            allowed[key] = item[:128]
        elif isinstance(item, (bool, int, float)):
            allowed[key] = item
        elif isinstance(item, list):
            allowed[key] = [str(entry)[:64] for entry in item[:20]]
    return allowed
