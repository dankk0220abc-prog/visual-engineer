from sqlalchemy import String, func, select
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.contracts import AIPlanContract, is_sensitive_path
from visual_engineer_api.ai_planning.invocation_contract import upstream_request_fingerprint
from visual_engineer_api.ai_planning.prompt_registry import redact_structured_payload
from visual_engineer_api.ai_planning.provider_registry import ProviderId
from visual_engineer_api.models.ai_planning import AIPlanRequest, AIProviderInvocation
from visual_engineer_api.models.delivery import DeliveryAuthorization
from visual_engineer_api.models.review import ReviewPackage
from visual_engineer_api.models.run import Run
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.task import Task
from visual_engineer_api.models.workspace import ExecutionGrant
from visual_engineer_api.repositories.ai_planning import AIPlanningRepository
from visual_engineer_api.schemas.ai_planning import (
    LiveProviderEvidenceDetail,
    LiveProviderEvidenceEvaluation,
    LiveProviderEvidenceOperation,
    LiveProviderEvidenceSummary,
    LiveProviderGovernanceBoundary,
)


class LiveProviderEvidenceError(Exception):
    def __init__(self, code: str, *, category: str) -> None:
        super().__init__(code)
        self.code = code
        self.category = category


class LiveProviderEvidenceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._planning = AIPlanningRepository(session)

    def live_verified_provider_ids(self) -> set[ProviderId]:
        values = self._session.scalars(
            select(AIProviderInvocation.provider_id)
            .join(
                AIPlanRequest,
                AIPlanRequest.id == AIProviderInvocation.ai_plan_request_id,
            )
            .join(Run, Run.id == AIPlanRequest.run_id)
            .join(Task, Task.id == Run.task_id)
            .where(
                AIProviderInvocation.classification == "live",
                AIProviderInvocation.status == "succeeded",
                Task.classification == "live_canary",
            )
            .distinct()
        )
        return {ProviderId(value) for value in values}

    def list(self, *, limit: int = 20) -> list[LiveProviderEvidenceSummary]:
        invocations = self._session.scalars(
            select(AIProviderInvocation)
            .join(
                AIPlanRequest,
                AIPlanRequest.id == AIProviderInvocation.ai_plan_request_id,
            )
            .join(Run, Run.id == AIPlanRequest.run_id)
            .join(Task, Task.id == Run.task_id)
            .where(
                AIProviderInvocation.classification == "live",
                AIProviderInvocation.status == "succeeded",
                Task.classification == "live_canary",
            )
            .order_by(AIProviderInvocation.completed_at.desc())
            .limit(limit)
        )
        return [self._summary(invocation) for invocation in invocations]

    def detail(self, correlation: str) -> LiveProviderEvidenceDetail:
        matches = [
            invocation
            for invocation in self._session.scalars(
                select(AIProviderInvocation)
                .join(
                    AIPlanRequest,
                    AIPlanRequest.id == AIProviderInvocation.ai_plan_request_id,
                )
                .join(Run, Run.id == AIPlanRequest.run_id)
                .join(Task, Task.id == Run.task_id)
                .where(
                    AIProviderInvocation.classification == "live",
                    AIProviderInvocation.status == "succeeded",
                    Task.classification == "live_canary",
                    func.substr(
                        func.replace(AIProviderInvocation.id.cast(String), "-", ""),
                        1,
                        12,
                    )
                    == correlation,
                )
                .limit(2)
            )
        ]
        if not matches:
            raise LiveProviderEvidenceError("live_evidence_not_found", category="not_found")
        if len(matches) != 1:
            raise LiveProviderEvidenceError(
                "live_evidence_correlation_ambiguous", category="conflict"
            )
        invocation = matches[0]
        ai_request = self._session.get(AIPlanRequest, invocation.ai_plan_request_id)
        if ai_request is None or ai_request.response_payload is None:
            raise LiveProviderEvidenceError("live_evidence_plan_missing", category="conflict")
        run = self._session.get(Run, ai_request.run_id)
        task = self._session.get(Task, run.task_id) if run is not None else None
        if run is None or task is None or task.classification != "live_canary":
            raise LiveProviderEvidenceError("live_evidence_context_invalid", category="conflict")
        try:
            plan = AIPlanContract.model_validate(ai_request.response_payload)
        except ValueError:
            raise LiveProviderEvidenceError(
                "live_evidence_plan_schema_invalid", category="conflict"
            ) from None

        operations: list[LiveProviderEvidenceOperation] = []
        for operation in plan.proposed_operations:
            target = getattr(operation, "relative_path", None)
            if not isinstance(target, str) or is_sensitive_path(target):
                target = None
            operations.append(
                LiveProviderEvidenceOperation(kind=str(operation.kind), target=target)
            )

        evaluations: list[LiveProviderEvidenceEvaluation] = []
        for evaluation in self._planning.eval_results(ai_request.id):
            safe_summary, redactions = redact_structured_payload(evaluation.summary)
            summary = (
                "Evaluation summary withheld by the safe projection."
                if redactions or not isinstance(safe_summary, str)
                else safe_summary
            )
            evaluations.append(
                LiveProviderEvidenceEvaluation(
                    eval_id=evaluation.eval_id,
                    passed=evaluation.passed,
                    summary=summary,
                )
            )

        safe_plan_summary, redactions = redact_structured_payload(plan.requirement_summary)
        if redactions or not isinstance(safe_plan_summary, str):
            safe_plan_summary = "Live Plan summary withheld by the safe projection."
        evidence_summary = self._summary(invocation)
        return LiveProviderEvidenceDetail(
            **evidence_summary.model_dump(),
            plan_summary=safe_plan_summary,
            operations=operations,
            evaluations=evaluations,
            task_classification="live_canary",
            public_task_context="Synthetic public Provider verification context",
            governance=self._governance(ai_request, run),
        )

    def _governance(self, ai_request: AIPlanRequest, run: Run) -> LiveProviderGovernanceBoundary:
        decision = self._planning.decision(ai_request.id)
        grant_ids = list(
            self._session.scalars(select(ExecutionGrant.id).where(ExecutionGrant.run_id == run.id))
        )
        runner_job_count = 0
        if grant_ids:
            runner_job_count = int(
                self._session.scalar(
                    select(func.count())
                    .select_from(RunnerJob)
                    .where(RunnerJob.execution_grant_id.in_(grant_ids))
                )
                or 0
            )
        review_ids = list(
            self._session.scalars(select(ReviewPackage.id).where(ReviewPackage.run_id == run.id))
        )
        delivery_count = 0
        if review_ids:
            delivery_count = int(
                self._session.scalar(
                    select(func.count())
                    .select_from(DeliveryAuthorization)
                    .where(DeliveryAuthorization.review_package_id.in_(review_ids))
                )
                or 0
            )
        return LiveProviderGovernanceBoundary(
            ai_plan_status=ai_request.status,
            approval_status=(decision.decision if decision is not None else "not_decided"),
            execution_grant_status="present" if grant_ids else "not_issued",
            runner_authority="present" if runner_job_count else "not_granted",
            review_status="present" if review_ids else "not_created",
            delivery_status="present" if delivery_count else "not_created",
        )

    @staticmethod
    def _summary(invocation: AIProviderInvocation) -> LiveProviderEvidenceSummary:
        if invocation.response_digest is None or invocation.completed_at is None:
            raise LiveProviderEvidenceError(
                "live_evidence_terminal_shape_invalid", category="conflict"
            )
        return LiveProviderEvidenceSummary(
            correlation=invocation.id.hex[:12],
            provider_id=invocation.provider_id,
            classification="live",
            lifecycle="succeeded",
            requested_model_id=invocation.requested_model_id,
            effective_model_status=invocation.effective_model_status,
            effective_model_id=invocation.effective_model_id,
            usage_status=invocation.usage_status,
            input_tokens=invocation.input_tokens,
            output_tokens=invocation.output_tokens,
            total_tokens=invocation.total_tokens,
            provider_elapsed_ms=invocation.provider_elapsed_ms,
            client_total_elapsed_ms=invocation.client_total_elapsed_ms,
            billing_status=invocation.billing_status,
            cost_amount=invocation.cost_amount,
            cost_currency=invocation.cost_currency,
            upstream_request_id_status=invocation.upstream_request_id_status,
            upstream_request_fingerprint=upstream_request_fingerprint(
                invocation.upstream_request_id
            ),
            request_digest=invocation.request_digest,
            response_digest=invocation.response_digest,
            completed_at=invocation.completed_at,
        )
