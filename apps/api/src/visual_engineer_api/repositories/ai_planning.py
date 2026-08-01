import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from visual_engineer_api.models.ai_planning import (
    AIEvalResult,
    AIPlanDecision,
    AIPlanRequest,
    AIProviderTrace,
)


class AIPlanningRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        value: AIPlanRequest | AIProviderTrace | AIEvalResult | AIPlanDecision,
    ) -> None:
        self._session.add(value)

    def get_request(self, request_id: uuid.UUID, *, lock: bool = False) -> AIPlanRequest | None:
        statement = select(AIPlanRequest).where(AIPlanRequest.id == request_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_by_run(self, run_id: uuid.UUID, *, lock: bool = False) -> AIPlanRequest | None:
        statement = select(AIPlanRequest).where(AIPlanRequest.run_id == run_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_by_idempotency_key(self, key: str) -> AIPlanRequest | None:
        return self._session.scalar(
            select(AIPlanRequest).where(AIPlanRequest.idempotency_key == key)
        )

    def traces(self, request_id: uuid.UUID) -> list[AIProviderTrace]:
        return list(
            self._session.scalars(
                select(AIProviderTrace)
                .where(AIProviderTrace.ai_plan_request_id == request_id)
                .order_by(AIProviderTrace.attempt_number)
            )
        )

    def eval_results(self, request_id: uuid.UUID) -> list[AIEvalResult]:
        return list(
            self._session.scalars(
                select(AIEvalResult)
                .where(AIEvalResult.ai_plan_request_id == request_id)
                .order_by(AIEvalResult.eval_id)
            )
        )

    def decision(self, request_id: uuid.UUID) -> AIPlanDecision | None:
        return self._session.scalar(
            select(AIPlanDecision).where(AIPlanDecision.ai_plan_request_id == request_id)
        )
