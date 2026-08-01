import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from visual_engineer_api.models.delivery import (
    DeliveryAuthorization,
    DeliveryAuthorizationDecision,
    LocalDelivery,
)
from visual_engineer_api.models.runner import RunnerJob


class DeliveryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        value: DeliveryAuthorization | DeliveryAuthorizationDecision | LocalDelivery,
    ) -> None:
        self._session.add(value)

    def authorization(
        self,
        authorization_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> DeliveryAuthorization | None:
        statement = select(DeliveryAuthorization).where(
            DeliveryAuthorization.id == authorization_id
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def authorization_by_package(
        self,
        package_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> DeliveryAuthorization | None:
        statement = select(DeliveryAuthorization).where(
            DeliveryAuthorization.review_package_id == package_id
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def authorization_by_idempotency(
        self,
        key: str,
        *,
        lock: bool = False,
    ) -> DeliveryAuthorization | None:
        statement = select(DeliveryAuthorization).where(
            DeliveryAuthorization.idempotency_key == key
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_authorizations(self) -> list[DeliveryAuthorization]:
        return list(
            self._session.scalars(
                select(DeliveryAuthorization).order_by(
                    DeliveryAuthorization.created_at.desc(),
                    DeliveryAuthorization.id.desc(),
                )
            )
        )

    def decision(
        self,
        authorization_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> DeliveryAuthorizationDecision | None:
        statement = select(DeliveryAuthorizationDecision).where(
            DeliveryAuthorizationDecision.delivery_authorization_id == authorization_id
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def decision_by_idempotency(
        self,
        key: str,
        *,
        lock: bool = False,
    ) -> DeliveryAuthorizationDecision | None:
        statement = select(DeliveryAuthorizationDecision).where(
            DeliveryAuthorizationDecision.idempotency_key == key
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def local_delivery(
        self,
        authorization_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> LocalDelivery | None:
        statement = select(LocalDelivery).where(
            LocalDelivery.delivery_authorization_id == authorization_id
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def job(self, authorization_id: uuid.UUID, *, lock: bool = False) -> RunnerJob | None:
        statement = (
            select(RunnerJob)
            .where(RunnerJob.delivery_authorization_id == authorization_id)
            .order_by(RunnerJob.created_at.desc(), RunnerJob.id.desc())
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)
