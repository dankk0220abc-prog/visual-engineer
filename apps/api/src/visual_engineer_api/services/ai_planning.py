import threading
import uuid
from typing import Any, NoReturn

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.contracts import (
    AIPlanContract,
    AIPlanGenerationRequest,
    ContextBudget,
    ContextManifestEntry,
    PromptBinding,
    RepositoryBinding,
    canonical_digest,
    canonical_json,
    is_sensitive_path,
)
from visual_engineer_api.ai_planning.evaluator import (
    EVALUATOR_VERSION,
    MANDATORY_EVAL_IDS,
    evaluate_plan,
)
from visual_engineer_api.ai_planning.fake_provider import DeterministicFixtureProvider
from visual_engineer_api.ai_planning.prompt_registry import (
    PROMPT_DIGEST,
    PROMPT_TEMPLATE_ID,
    PROMPT_VERSION,
    prompt_payload,
    redact_requirement,
    redact_structured_payload,
)
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    PlanningProvider,
    ProviderErrorCategory,
    invoke_provider,
)
from visual_engineer_api.ai_planning.provider_registry import (
    ProviderId,
    ProviderRegistry,
)
from visual_engineer_api.core.config import Settings, get_settings
from visual_engineer_api.core.observability import log_governance_event
from visual_engineer_api.models.ai_planning import (
    AIEvalResult,
    AIPlanDecision,
    AIPlanRequest,
    AIProviderTrace,
)
from visual_engineer_api.models.run import (
    ApprovalDecision,
    AuditEvent,
    Plan,
    RepositorySnapshot,
    Run,
)
from visual_engineer_api.models.task import Task
from visual_engineer_api.repositories.ai_planning import AIPlanningRepository
from visual_engineer_api.repositories.run import RunRepository
from visual_engineer_api.repositories.task import TaskRepository
from visual_engineer_api.repository_intelligence import RepositoryScanError, RepositoryScanner
from visual_engineer_api.schemas.ai_planning import (
    AIEvalResultResponse,
    AIPlanDecisionCreate,
    AIPlanDecisionResponse,
    AIPlanRequestCreate,
    AIPlanRequestResponse,
    AIProviderTraceResponse,
)
from visual_engineer_api.services.run_state import transition_run


class AIPlanningServiceError(Exception):
    def __init__(self, code: str, message: str, *, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


class _CancellationRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tokens: dict[uuid.UUID, CancellationToken] = {}

    def register(self, request_id: uuid.UUID, token: CancellationToken) -> None:
        with self._lock:
            self._tokens[request_id] = token

    def cancel(self, request_id: uuid.UUID) -> None:
        with self._lock:
            token = self._tokens.get(request_id)
        if token is not None:
            token.cancel()

    def discard(self, request_id: uuid.UUID) -> None:
        with self._lock:
            self._tokens.pop(request_id, None)


_CANCELLATIONS = _CancellationRegistry()


class AIPlanningService:
    def __init__(
        self,
        session: Session,
        *,
        provider: PlanningProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._repository = AIPlanningRepository(session)
        self._runs = RunRepository(session)
        self._tasks = TaskRepository(session)
        self._settings = settings or get_settings()
        self._provider_override = provider
        self._provider_registry = ProviderRegistry(self._settings)

    @property
    def provider(self) -> PlanningProvider:
        return self._provider_override or DeterministicFixtureProvider()

    def create_request(
        self,
        run_id: uuid.UUID,
        payload: AIPlanRequestCreate,
        *,
        request_id: str,
        idempotency_key: str,
    ) -> tuple[AIPlanRequestResponse, bool]:
        provider = self._select_provider(payload.provider_id)
        request_hash = canonical_digest(
            {
                "run_id": str(run_id),
                "delivery_package": payload.delivery_package.value,
                "provider_id": provider.capabilities.provider_id,
                "prompt_version": PROMPT_VERSION,
            }
        )
        existing = self._repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.idempotency_request_hash != request_hash:
                self._conflict(
                    "ai_plan_idempotency_conflict",
                    "Idempotency-Key is associated with a different AI Plan request",
                )
            if existing.status == "requested":
                self._generate(existing.id, request_id=request_id)
            return self.response(existing.id), True

        run = self._runs.get(run_id, lock=True)
        if run is None:
            self._not_found("run_not_found", "Run was not found")
        snapshot = self._runs.get_snapshot(run_id)
        if snapshot is None:
            self._conflict(
                "snapshot_required",
                "A successful committed-HEAD Snapshot is required",
            )
        if run.status != "snapshot_ready":
            self._conflict(
                "ai_plan_run_state_conflict",
                f"AI planning requires snapshot_ready, not {run.status}",
            )
        if self._runs.latest_plan(run_id, lock=True) is not None:
            self._conflict(
                "plan_already_exists",
                "A governed Plan already exists for this Run",
            )
        prior = self._repository.get_by_run(run_id, lock=True)
        if prior is not None:
            self._conflict(
                "ai_plan_request_already_exists",
                "Use the original Idempotency-Key to replay this Run's AI Plan request",
            )
        task = self._tasks.get_by_id(run.task_id)
        if task is None:
            self._not_found("task_not_found", "Task was not found")

        generation_request, prompt, redactions, excluded_count = self._generation_request(
            task, snapshot, payload, provider
        )
        request_values = generation_request.model_dump(mode="json")
        context_values = [
            item.model_dump(mode="json") for item in generation_request.context_manifest
        ]
        ai_request = AIPlanRequest(
            run_id=run.id,
            status="requested",
            delivery_package=payload.delivery_package.value,
            source_revision=snapshot.source_revision,
            snapshot_fingerprint=snapshot.fingerprint,
            prompt_template_id=PROMPT_TEMPLATE_ID,
            prompt_version=PROMPT_VERSION,
            prompt_digest=PROMPT_DIGEST,
            prompt_payload=prompt,
            provider_id=provider.capabilities.provider_id,
            provider_metadata=provider.capabilities.model_dump(mode="json"),
            request_payload=request_values,
            request_digest=canonical_digest(request_values),
            response_payload=None,
            deterministic_digest=None,
            context_manifest=context_values,
            context_digest=canonical_digest(context_values),
            context_bytes=len(canonical_json(context_values)),
            context_reference_count=len(context_values),
            context_excluded_count=excluded_count,
            redaction_record=redactions,
            retry_count=0,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
        )
        self._repository.add(ai_request)
        self._session.flush()
        self._audit(
            run,
            "ai_plan_requested",
            request_id,
            {
                "ai_plan_request_id": str(ai_request.id),
                "provider_id": ai_request.provider_id,
                "prompt_version": ai_request.prompt_version,
                "source_revision": ai_request.source_revision,
                "context_reference_count": ai_request.context_reference_count,
                "context_excluded_count": ai_request.context_excluded_count,
            },
        )
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            winner = self._repository.get_by_idempotency_key(idempotency_key)
            if winner is not None and winner.idempotency_request_hash == request_hash:
                return self.response(winner.id), True
            self._conflict(
                "ai_plan_request_race_conflict",
                "A competing AI Plan request already won for this Run",
            )
        log_governance_event(
            "ai_plan_requested",
            run,
            request_id=request_id,
            ai_plan_request_id=ai_request.id,
        )
        self._generate(ai_request.id, request_id=request_id)
        return self.response(ai_request.id), False

    def response(self, ai_plan_request_id: uuid.UUID) -> AIPlanRequestResponse:
        ai_request = self._repository.get_request(ai_plan_request_id)
        if ai_request is None:
            self._not_found("ai_plan_request_not_found", "AI Plan request was not found")
        traces = self._repository.traces(ai_request.id)
        eval_results = self._repository.eval_results(ai_request.id)
        decision = self._repository.decision(ai_request.id)
        plan = (
            AIPlanContract.model_validate(ai_request.response_payload)
            if ai_request.response_payload is not None
            else None
        )
        return AIPlanRequestResponse(
            id=ai_request.id,
            run_id=ai_request.run_id,
            status=ai_request.status,
            delivery_package=ai_request.delivery_package,
            source_revision=ai_request.source_revision,
            snapshot_fingerprint=ai_request.snapshot_fingerprint,
            prompt_template_id=ai_request.prompt_template_id,
            prompt_version=ai_request.prompt_version,
            prompt_digest=ai_request.prompt_digest,
            prompt_payload=ai_request.prompt_payload,
            provider_id=ai_request.provider_id,
            provider_metadata=ai_request.provider_metadata,
            request_payload=ai_request.request_payload,
            request_digest=ai_request.request_digest,
            plan=plan,
            deterministic_digest=ai_request.deterministic_digest,
            context_manifest=ai_request.context_manifest,
            context_digest=ai_request.context_digest,
            context_bytes=ai_request.context_bytes,
            context_reference_count=ai_request.context_reference_count,
            context_excluded_count=ai_request.context_excluded_count,
            redaction_record=ai_request.redaction_record,
            retry_count=ai_request.retry_count,
            error_category=ai_request.error_category,
            error_code=ai_request.error_code,
            error_message=ai_request.error_message,
            handoff_plan_id=ai_request.handoff_plan_id,
            traces=[AIProviderTraceResponse.model_validate(item) for item in traces],
            eval_results=[AIEvalResultResponse.model_validate(item) for item in eval_results],
            decision=AIPlanDecisionResponse.model_validate(decision) if decision else None,
            created_at=ai_request.created_at,
            updated_at=ai_request.updated_at,
        )

    def list_for_run(self, run_id: uuid.UUID) -> tuple[list[AIPlanRequestResponse], int]:
        if self._runs.get(run_id) is None:
            self._not_found("run_not_found", "Run was not found")
        item = self._repository.get_by_run(run_id)
        return ([self.response(item.id)] if item is not None else []), int(item is not None)

    def refresh_freshness(
        self, ai_plan_request_id: uuid.UUID, *, request_id: str
    ) -> AIPlanRequestResponse:
        ai_request = self._repository.get_request(ai_plan_request_id)
        if ai_request is None:
            self._not_found("ai_plan_request_not_found", "AI Plan request was not found")
        if ai_request.status != "generated":
            return self.response(ai_request.id)
        run = self._runs.get(ai_request.run_id)
        if run is None:
            self._not_found("run_not_found", "Run was not found")
        task = self._tasks.get_by_id(run.task_id)
        snapshot = self._runs.get_snapshot(run.id)
        if task is None or snapshot is None:
            self._conflict("ai_plan_context_missing", "AI Plan repository context is unavailable")
        try:
            current = RepositoryScanner(self._settings).scan(task.repository_locator)
        except RepositoryScanError as exc:
            raise AIPlanningServiceError(
                "ai_plan_freshness_unavailable",
                "The repository revision could not be safely revalidated",
                category="conflict",
            ) from exc
        if (
            current.source_revision == ai_request.source_revision
            and current.fingerprint == ai_request.snapshot_fingerprint
        ):
            return self.response(ai_request.id)

        locked = self._repository.get_request(ai_request.id, lock=True)
        locked_run = self._runs.get(ai_request.run_id, lock=True)
        if locked is None or locked_run is None:
            self._not_found("ai_plan_request_not_found", "AI Plan request was not found")
        if locked.status == "generated":
            locked.status = "stale"
            locked.error_category = "freshness"
            locked.error_code = "repository_revision_changed"
            locked.error_message = "Repository revision or Snapshot fingerprint changed"
            if locked_run.status == "plan_ready":
                transition_run(locked_run, "failed")
                locked_run.error_code = "repository_revision_changed"
                locked_run.error_message = "AI Plan became stale before approval"
            self._audit(
                locked_run,
                "ai_plan_stale",
                request_id,
                {
                    "ai_plan_request_id": str(locked.id),
                    "reason_code": "repository_revision_changed",
                },
            )
            self._session.commit()
            log_governance_event(
                "ai_plan_stale",
                locked_run,
                request_id=request_id,
                ai_plan_request_id=locked.id,
                policy_denial_reason_code="repository_revision_changed",
            )
        return self.response(ai_request.id)

    def decide(
        self,
        ai_plan_request_id: uuid.UUID,
        payload: AIPlanDecisionCreate,
        *,
        request_id: str,
    ) -> tuple[AIPlanDecisionResponse, bool]:
        freshness = self.refresh_freshness(ai_plan_request_id, request_id=request_id)
        if freshness.status == "stale":
            self._conflict("stale_ai_plan", "A stale AI Plan cannot receive approval")

        ai_request = self._repository.get_request(ai_plan_request_id, lock=True)
        if ai_request is None:
            self._not_found("ai_plan_request_not_found", "AI Plan request was not found")
        existing = self._repository.decision(ai_request.id)
        if existing is not None:
            if existing.decision == payload.decision and existing.comment == payload.comment:
                return AIPlanDecisionResponse.model_validate(existing), True
            self._conflict(
                "ai_plan_decision_conflict",
                "A different final decision already exists for this AI Plan",
            )
        if ai_request.status != "generated":
            self._conflict(
                "ai_plan_not_decidable",
                f"AI Plan status {ai_request.status} cannot receive a decision",
            )
        run = self._runs.get(ai_request.run_id, lock=True)
        snapshot = self._runs.get_snapshot(ai_request.run_id)
        if run is None or snapshot is None:
            self._conflict("ai_plan_context_missing", "AI Plan repository context is unavailable")
        if run.status != "plan_ready":
            self._conflict(
                "ai_plan_run_state_conflict",
                f"AI Plan decision requires plan_ready, not {run.status}",
            )
        evals = self._repository.eval_results(ai_request.id)
        eval_ids = {item.eval_id for item in evals}
        if eval_ids != set(MANDATORY_EVAL_IDS) or any(
            not item.passed
            or item.severity != "blocking"
            or item.evaluator_version != EVALUATOR_VERSION
            or item.evaluator_trust != "system_policy"
            for item in evals
        ):
            self._conflict(
                "ai_plan_eval_incomplete",
                "Every mandatory system Eval must pass before human approval",
            )
        plan_contract = AIPlanContract.model_validate(ai_request.response_payload)

        handoff: Plan | None = None
        if payload.decision == "approve":
            if self._runs.latest_plan(run.id, lock=True) is not None:
                self._conflict("plan_already_exists", "A governed Plan already exists for this Run")
            handoff_values = self._handoff_values(plan_contract)
            handoff = Plan(
                run_id=run.id,
                version=1,
                status="approved",
                source="governed_ai",
                snapshot_fingerprint=snapshot.fingerprint,
                delivery_package=ai_request.delivery_package,
                execution_available=False,
                content_hash=canonical_digest(
                    {
                        "source": "governed_ai",
                        "ai_plan_request_id": str(ai_request.id),
                        "deterministic_digest": ai_request.deterministic_digest,
                        "snapshot_fingerprint": snapshot.fingerprint,
                        **handoff_values,
                    }
                ),
                **handoff_values,
            )
            self._session.add(handoff)
            self._session.flush()
            self._session.add(
                ApprovalDecision(
                    run_id=run.id,
                    plan_id=handoff.id,
                    decision="approve",
                    comment=payload.comment,
                    actor_type="local_user",
                    request_id=request_id,
                )
            )
            run.current_plan_version = 1
            transition_run(run, "awaiting_plan_approval")
            transition_run(run, "approved")
            ai_request.status = "approved"
            ai_request.handoff_plan_id = handoff.id
        else:
            transition_run(run, "awaiting_plan_approval")
            transition_run(run, "rejected")
            ai_request.status = "rejected"

        decision = AIPlanDecision(
            ai_plan_request_id=ai_request.id,
            run_id=run.id,
            decision=payload.decision,
            comment=payload.comment,
            actor_type="local_user",
            request_id=request_id,
            handoff_plan_id=handoff.id if handoff is not None else None,
        )
        self._repository.add(decision)
        self._audit(
            run,
            "ai_plan_approved" if payload.decision == "approve" else "ai_plan_rejected",
            request_id,
            {
                "ai_plan_request_id": str(ai_request.id),
                "handoff_plan_id": str(handoff.id) if handoff else None,
                "comment_provided": payload.comment is not None,
                "execution_grant_issued": False,
                "review_approval_issued": False,
                "delivery_authorization_issued": False,
            },
        )
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            winner = self._repository.decision(ai_plan_request_id)
            if (
                winner is not None
                and winner.decision == payload.decision
                and winner.comment == payload.comment
            ):
                return AIPlanDecisionResponse.model_validate(winner), True
            self._conflict(
                "ai_plan_decision_conflict",
                "A different final decision already exists for this AI Plan",
            )
        self._session.refresh(decision)
        log_governance_event(
            "ai_plan_approved" if payload.decision == "approve" else "ai_plan_rejected",
            run,
            request_id=request_id,
            ai_plan_request_id=ai_request.id,
            plan_id=handoff.id if handoff else None,
        )
        return AIPlanDecisionResponse.model_validate(decision), False

    def cancel(self, ai_plan_request_id: uuid.UUID, *, request_id: str) -> AIPlanRequestResponse:
        ai_request = self._repository.get_request(ai_plan_request_id, lock=True)
        if ai_request is None:
            self._not_found("ai_plan_request_not_found", "AI Plan request was not found")
        if ai_request.status == "cancelled":
            return self.response(ai_request.id)
        if ai_request.status in {"approved", "rejected", "failed", "stale"}:
            self._conflict(
                "ai_plan_terminal",
                f"Terminal AI Plan status {ai_request.status} cannot be cancelled",
            )
        run = self._runs.get(ai_request.run_id, lock=True)
        if run is None:
            self._not_found("run_not_found", "Run was not found")
        _CANCELLATIONS.cancel(ai_request.id)
        ai_request.status = "cancelled"
        ai_request.error_category = ProviderErrorCategory.CANCELLED.value
        ai_request.error_code = "ai_plan_cancelled"
        ai_request.error_message = "AI Plan generation or review was cancelled"
        if run.status in {"snapshot_ready", "plan_ready"}:
            transition_run(run, "cancelled")
        self._audit(
            run,
            "ai_plan_cancelled",
            request_id,
            {"ai_plan_request_id": str(ai_request.id)},
        )
        self._session.commit()
        log_governance_event(
            "ai_plan_cancelled",
            run,
            request_id=request_id,
            ai_plan_request_id=ai_request.id,
        )
        return self.response(ai_request.id)

    def _generate(self, ai_plan_request_id: uuid.UUID, *, request_id: str) -> None:
        ai_request = self._repository.get_request(ai_plan_request_id, lock=True)
        if ai_request is None or ai_request.status != "requested":
            return
        provider = self._select_persisted_provider(ai_request.provider_id)
        run = self._runs.get(ai_request.run_id, lock=True)
        if run is None or run.status != "snapshot_ready":
            self._conflict(
                "ai_plan_run_state_conflict",
                "AI Plan generation no longer has a snapshot_ready Run",
            )
        ai_request.status = "generating"
        self._audit(
            run,
            "ai_plan_generating",
            request_id,
            {
                "ai_plan_request_id": str(ai_request.id),
                "provider_id": ai_request.provider_id,
            },
        )
        self._session.commit()
        generation_request = AIPlanGenerationRequest.model_validate(ai_request.request_payload)
        token = CancellationToken()
        _CANCELLATIONS.register(ai_request.id, token)
        try:
            provider_run = invoke_provider(
                provider,
                generation_request,
                token,
                timeout_seconds=self._settings.ai_provider_timeout_seconds,
                max_attempts=self._settings.ai_provider_max_attempts,
            )
        finally:
            _CANCELLATIONS.discard(ai_request.id)

        locked = self._repository.get_request(ai_request.id, lock=True)
        locked_run = self._runs.get(ai_request.run_id, lock=True)
        if locked is None or locked_run is None:
            return
        for attempt in provider_run.attempts:
            if attempt.result is not None:
                usage = attempt.result.usage
                trace_status = "succeeded"
                try:
                    response_digest = canonical_digest(attempt.result.response_payload)
                except (TypeError, ValueError):
                    response_digest = None
                latency_ms = attempt.result.latency_ms
                error_category = None
                error_code = None
                retryable = False
                input_tokens = usage.input_tokens
                output_tokens = usage.output_tokens
                total_tokens = usage.total_tokens
                cost = usage.cost_estimate_microunits
                cost_basis = usage.cost_basis
            else:
                assert attempt.error is not None
                trace_status = (
                    "timeout"
                    if attempt.error.category == ProviderErrorCategory.TIMEOUT
                    else "cancelled"
                    if attempt.error.category == ProviderErrorCategory.CANCELLED
                    else "failed"
                )
                response_digest = None
                latency_ms = attempt.observed_latency_ms
                error_category = attempt.error.category.value
                error_code = attempt.error.code
                retryable = attempt.error.retryable
                input_tokens = output_tokens = total_tokens = cost = 0
                cost_basis = "synthetic_not_billable"
            self._repository.add(
                AIProviderTrace(
                    ai_plan_request_id=locked.id,
                    attempt_number=attempt.attempt_number,
                    status=trace_status,
                    provider_id=locked.provider_id,
                    provider_metadata=locked.provider_metadata,
                    request_digest=locked.request_digest,
                    response_digest=response_digest,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_estimate_microunits=cost,
                    cost_basis=cost_basis,
                    error_category=error_category,
                    error_code=error_code,
                    retryable=retryable,
                    redactions=locked.redaction_record,
                )
            )
        locked.retry_count = max(0, len(provider_run.attempts) - 1)
        if locked.status == "cancelled":
            self._session.commit()
            return
        if provider_run.result is None:
            error = provider_run.error
            locked.status = "failed"
            locked.error_category = error.category.value if error else "internal"
            locked.error_code = error.code if error else "provider_failed"
            locked.error_message = (
                error.public_message if error else "Provider generation failed safely"
            )[:500]
            if locked_run.status == "snapshot_ready":
                transition_run(locked_run, "failed")
                locked_run.error_code = locked.error_code
                locked_run.error_message = locked.error_message
            self._audit(
                locked_run,
                "ai_plan_failed",
                request_id,
                {
                    "ai_plan_request_id": str(locked.id),
                    "reason_code": locked.error_code,
                    "attempt_count": len(provider_run.attempts),
                },
            )
            self._session.commit()
            return

        invalid_response_code: str | None = None
        invalid_response_message: str | None = None
        try:
            response_bytes = len(canonical_json(provider_run.result.response_payload))
        except (TypeError, ValueError):
            invalid_response_code = "provider_response_not_json"
            invalid_response_message = "Provider response was not canonical JSON"
        else:
            if response_bytes > provider.capabilities.max_output_bytes:
                invalid_response_code = "provider_output_budget_exceeded"
                invalid_response_message = "Provider response exceeded its output budget"
        try:
            plan = AIPlanContract.model_validate(provider_run.result.response_payload)
        except ValidationError:
            invalid_response_code = invalid_response_code or "provider_schema_invalid"
            invalid_response_message = (
                invalid_response_message or "Provider response did not match the AI Plan contract"
            )
        if invalid_response_code is not None:
            locked.status = "failed"
            locked.error_category = ProviderErrorCategory.INVALID_RESPONSE.value
            locked.error_code = invalid_response_code
            locked.error_message = invalid_response_message
            if locked_run.status == "snapshot_ready":
                transition_run(locked_run, "failed")
                locked_run.error_code = locked.error_code
                locked_run.error_message = locked.error_message
            self._audit(
                locked_run,
                "ai_plan_failed",
                request_id,
                {
                    "ai_plan_request_id": str(locked.id),
                    "reason_code": locked.error_code,
                    "attempt_count": len(provider_run.attempts),
                },
            )
            self._session.commit()
            log_governance_event(
                "ai_plan_failed",
                locked_run,
                request_id=request_id,
                ai_plan_request_id=locked.id,
                policy_denial_reason_code=locked.error_code,
            )
            return
        eval_results = evaluate_plan(
            generation_request,
            plan,
            locked.prompt_payload,
            provider,
            expected_source_revision=locked.source_revision,
            expected_snapshot_fingerprint=locked.snapshot_fingerprint,
        )
        for result in eval_results:
            self._repository.add(
                AIEvalResult(
                    ai_plan_request_id=locked.id,
                    eval_id=result.eval_id,
                    passed=result.passed,
                    severity=result.severity,
                    summary=result.summary,
                    evidence=result.evidence,
                    evaluator_version=EVALUATOR_VERSION,
                    evaluator_trust="system_policy",
                )
            )
        locked.response_payload = plan.model_dump(mode="json")
        locked.deterministic_digest = plan.deterministic_digest
        if all(result.passed for result in eval_results):
            locked.status = "generated"
            transition_run(locked_run, "plan_ready")
            event_type = "ai_plan_generated"
            reason_code = None
        else:
            locked.status = "failed"
            locked.error_category = "evaluation"
            locked.error_code = "ai_plan_eval_failed"
            locked.error_message = "One or more mandatory AI Plan Evals failed"
            transition_run(locked_run, "failed")
            locked_run.error_code = locked.error_code
            locked_run.error_message = locked.error_message
            event_type = "ai_plan_failed"
            reason_code = locked.error_code
        self._audit(
            locked_run,
            event_type,
            request_id,
            {
                "ai_plan_request_id": str(locked.id),
                "deterministic_digest": locked.deterministic_digest,
                "eval_pass_count": sum(result.passed for result in eval_results),
                "eval_total": len(eval_results),
                "reason_code": reason_code,
            },
        )
        self._session.commit()
        log_governance_event(
            event_type,
            locked_run,
            request_id=request_id,
            ai_plan_request_id=locked.id,
            policy_denial_reason_code=reason_code,
        )

    def _generation_request(
        self,
        task: Task,
        snapshot: RepositorySnapshot,
        payload: AIPlanRequestCreate,
        provider: PlanningProvider,
    ) -> tuple[AIPlanGenerationRequest, dict[str, Any], list[dict[str, Any]], int]:
        redacted = redact_requirement(task.objective)
        provider_context_limit = provider.capabilities.max_context_bytes
        budget = ContextBudget(
            max_context_bytes=min(self._settings.ai_plan_context_max_bytes, provider_context_limit),
            max_references=self._settings.ai_plan_context_max_references,
        )
        candidates, excluded = self._context_candidates(snapshot)
        selected: list[ContextManifestEntry] = []
        for candidate_values in candidates:
            candidate = ContextManifestEntry(
                reference_id=f"ctx-{len(selected) + 1:04d}",
                **candidate_values,
            )
            proposed = [*selected, candidate]
            if (
                len(proposed) > budget.max_references
                or len(canonical_json([item.model_dump(mode="json") for item in proposed]))
                > budget.max_context_bytes
            ):
                excluded += 1
                continue
            selected.append(candidate)
        if not selected:
            raise AIPlanningServiceError(
                "ai_context_budget_too_small",
                "The governed context budget cannot hold the repository revision binding",
                category="policy",
            )
        facts = {
            "repository_is_dirty": snapshot.repository_is_dirty,
            "tracked_file_count": snapshot.tracked_file_count,
            "selected_file_count": snapshot.selected_file_count,
            "skipped_file_count": snapshot.skipped_file_count,
            "languages": snapshot.tech_stack.get("languages", []),
            "frameworks": snapshot.tech_stack.get("frameworks", []),
            "package_manager": snapshot.package_manager,
            "safety_finding_rule_counts": _rule_counts(snapshot.safety_findings),
        }
        context_digest = canonical_digest([item.model_dump(mode="json") for item in selected])
        generation_request = AIPlanGenerationRequest(
            delivery_package=payload.delivery_package,
            requirement=redacted.value,
            requirement_was_redacted=bool(redacted.records),
            malicious_instruction_signals=redacted.injection_signals,
            repository=RepositoryBinding(
                source_revision=snapshot.source_revision,
                snapshot_fingerprint=snapshot.fingerprint,
                scanner_version=snapshot.scanner_version,
                scan_policy_version=snapshot.scan_policy_version,
            ),
            repository_facts=facts,
            context_manifest=selected,
            context_budget=budget,
            prompt=PromptBinding(
                template_id=PROMPT_TEMPLATE_ID,
                version=PROMPT_VERSION,
                digest=PROMPT_DIGEST,
                context_manifest_digest=context_digest,
                source_revision=snapshot.source_revision,
                snapshot_fingerprint=snapshot.fingerprint,
            ),
        )
        safe_request, structured_redactions = redact_structured_payload(
            generation_request.model_dump(mode="json")
        )
        generation_request = AIPlanGenerationRequest.model_validate(safe_request)
        prompt = prompt_payload(generation_request.model_dump(mode="json"))
        records = [*redacted.records, *structured_redactions]
        if redacted.injection_signals:
            records.append(
                {
                    "rule": "untrusted_instruction_signals",
                    "signals": redacted.injection_signals,
                    "replacement_count": 0,
                }
            )
        return generation_request, prompt, records, excluded

    @staticmethod
    def _context_candidates(
        snapshot: RepositorySnapshot,
    ) -> tuple[list[dict[str, Any]], int]:
        base = {
            "source_revision": snapshot.source_revision,
            "provenance": "committed_head_structured_extraction",
        }
        candidates: list[dict[str, Any]] = [
            {
                **base,
                "kind": "repository_revision",
                "summary": f"Committed repository revision {snapshot.source_revision}",
            }
        ]
        policy_excluded = 0
        for language in sorted(_string_values(snapshot.tech_stack.get("languages"))):
            candidates.append({**base, "kind": "language", "summary": f"Language: {language}"})
        for framework in sorted(_string_values(snapshot.tech_stack.get("frameworks"))):
            candidates.append({**base, "kind": "framework", "summary": f"Framework: {framework}"})
        if snapshot.package_manager:
            candidates.append(
                {
                    **base,
                    "kind": "package_manager",
                    "summary": f"Package manager: {snapshot.package_manager}",
                }
            )
        for item in snapshot.test_surfaces:
            relative_path = item.get("relative_path")
            if isinstance(relative_path, str) and not is_sensitive_path(relative_path):
                candidates.append(
                    {
                        **base,
                        "kind": "test_surface",
                        "summary": (
                            f"Test surface: {item.get('kind', 'unknown')} at {relative_path}"
                        ),
                        "relative_path": relative_path,
                    }
                )
            elif isinstance(relative_path, str):
                policy_excluded += 1
        for item in snapshot.design_system_signals:
            relative_path = item.get("relative_path")
            if isinstance(relative_path, str) and not is_sensitive_path(relative_path):
                candidates.append(
                    {
                        **base,
                        "kind": "design_system_signal",
                        "summary": (
                            "Design-system signal: "
                            f"{item.get('kind', 'unknown')} at {relative_path}"
                        ),
                        "relative_path": relative_path,
                    }
                )
            elif isinstance(relative_path, str):
                policy_excluded += 1
        for item in snapshot.repository_instructions:
            relative_path = item.get("relative_path")
            if isinstance(relative_path, str) and not is_sensitive_path(relative_path):
                candidates.append(
                    {
                        **base,
                        "kind": "repository_instruction",
                        "summary": (
                            f"Untrusted repository instruction metadata at {relative_path}: "
                            f"{item.get('risk_label', 'untrusted_content')}"
                        ),
                        "relative_path": relative_path,
                        "content_sha256": item.get("content_sha256"),
                    }
                )
            elif isinstance(relative_path, str):
                policy_excluded += 1
        for item in snapshot.available_scripts:
            summary = (
                "Available package script metadata: "
                f"{item.get('workspace', '.')}:{item.get('script')}"
                if item.get("kind") == "package_script"
                else f"Available Make target metadata: {item.get('target')}"
            )
            candidates.append({**base, "kind": "available_validation", "summary": summary})
        for item in snapshot.manifest:
            relative_path = item.get("relative_path")
            content_sha256 = item.get("content_sha256")
            if (
                item.get("selected") is True
                and isinstance(relative_path, str)
                and isinstance(content_sha256, str)
                and not is_sensitive_path(relative_path)
            ):
                candidates.append(
                    {
                        "source_revision": snapshot.source_revision,
                        "provenance": "git_head_manifest",
                        "kind": "repository_file",
                        "summary": f"Selected committed file: {relative_path}",
                        "relative_path": relative_path,
                        "content_sha256": content_sha256,
                    }
                )
            elif item.get("selected") is True and isinstance(relative_path, str):
                policy_excluded += 1
        return candidates, policy_excluded

    @staticmethod
    def _handoff_values(plan: AIPlanContract) -> dict[str, Any]:
        validation_steps = [
            check.model_dump(mode="json")
            for suite in plan.validation_suites
            for check in suite.checks
        ]
        return {
            "objective_summary": plan.requirement_summary[:4000],
            "repository_context_summary": " ".join(
                finding.summary for finding in plan.repository_findings
            )[:4000],
            "assumptions": list(plan.assumptions),
            "proposed_change_scope": [
                f"{change.change_type} {change.relative_path}: {change.component}"
                for change in plan.expected_changes
            ],
            "explicit_non_goals": [
                "No Provider or Plan self-approval.",
                "No automatic Execution Grant, Review Approval, or Delivery Authorization.",
                "No real Provider, credential, network, source write, remote Git, or deployment.",
            ],
            "risk_items": [
                f"{risk.severity}: {risk.summary} Mitigation: {risk.mitigation}"
                for risk in plan.risks
            ],
            "acceptance_criteria": [item.statement for item in plan.acceptance_criteria],
            "evidence_requirements": [
                "Exact AI Plan deterministic digest and Prompt binding.",
                "Bounded context manifest with committed-HEAD provenance.",
                "All mandatory system-owned Eval results pass.",
                "Human AI Plan decision and independent later governance decisions.",
            ],
            "stop_conditions": [
                "Repository revision or Snapshot fingerprint changes.",
                "Any mandatory Eval fails or evidence is missing.",
                "A requested operation, path, secret, network, or authority exceeds policy.",
            ],
            "validation_steps": validation_steps,
            "required_future_permission_level": "separate_execution_grant_required",
        }

    def _audit(self, run: Run, event_type: str, request_id: str, details: dict[str, Any]) -> None:
        safe = {
            key: value
            for key, value in details.items()
            if value is not None
            and key
            in {
                "ai_plan_request_id",
                "attempt_count",
                "comment_provided",
                "context_excluded_count",
                "context_reference_count",
                "delivery_authorization_issued",
                "deterministic_digest",
                "eval_pass_count",
                "eval_total",
                "execution_grant_issued",
                "handoff_plan_id",
                "prompt_version",
                "provider_id",
                "reason_code",
                "review_approval_issued",
                "source_revision",
            }
        }
        self._session.add(
            AuditEvent(
                run_id=run.id,
                event_type=event_type,
                actor_type="local_user"
                if event_type
                in {
                    "ai_plan_requested",
                    "ai_plan_approved",
                    "ai_plan_rejected",
                    "ai_plan_cancelled",
                }
                else "system",
                request_id=request_id,
                details=safe,
            )
        )

    def _select_provider(self, provider_id: ProviderId) -> PlanningProvider:
        if self._provider_override is not None:
            if self._provider_override.capabilities.provider_id != provider_id.value:
                raise AIPlanningServiceError(
                    "provider_disabled",
                    "The selected Provider is not enabled for this planning service",
                    category="policy",
                )
            return self._provider_override

        status = self._provider_registry.get(provider_id)
        if not status.configured:
            raise AIPlanningServiceError(
                "provider_not_configured",
                "The selected Provider is missing its local API key",
                category="policy",
            )
        if not status.enabled:
            raise AIPlanningServiceError(
                "provider_disabled",
                "The selected Provider is disabled until live validation is completed",
                category="policy",
            )
        if provider_id == ProviderId.DETERMINISTIC_FIXTURE:
            return DeterministicFixtureProvider()
        raise AIPlanningServiceError(
            "provider_disabled",
            "The selected Provider is not enabled for governed planning",
            category="policy",
        )

    def _select_persisted_provider(self, provider_id: str) -> PlanningProvider:
        try:
            typed_provider_id = ProviderId(provider_id)
        except ValueError as exc:
            raise AIPlanningServiceError(
                "provider_disabled",
                "The stored Provider is outside the closed registry",
                category="policy",
            ) from exc
        return self._select_provider(typed_provider_id)

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise AIPlanningServiceError(code, message, category="conflict")

    @staticmethod
    def _not_found(code: str, message: str) -> NoReturn:
        raise AIPlanningServiceError(code, message, category="not_found")


def _string_values(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _rule_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        rule = finding.get("rule_type")
        if isinstance(rule, str):
            counts[rule] = counts.get(rule, 0) + 1
    return dict(sorted(counts.items()))
