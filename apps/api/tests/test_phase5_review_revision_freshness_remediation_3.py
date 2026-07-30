from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from test_phase5_governed_final_review import _create_package
from test_phase5_review_revision_freshness_single_finding_rereview import (
    _approve,
    _invalidation,
    _invalidation_events,
    _registration_payload,
    _successful_context,
)
from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewFreshnessState,
    ReviewPackage,
)
from visual_engineer_api.models.runner import Runner
from visual_engineer_api.repositories.workspace import WorkspaceRepository
from visual_engineer_api.services.workspace import WorkspaceService
from visual_engineer_runner_protocol import RepositoryRegistrationRequest

IDENTICAL_REVISION = "b" * 40
OTHER_REVISION = "c" * 40


def _wait_for_revision_lock(
    database_url: str,
    application_prefix: str,
    *,
    timeout_seconds: float = 5.0,
) -> tuple[str, str, str]:
    engine = create_engine(database_url)
    deadline = time.monotonic() + timeout_seconds
    try:
        while time.monotonic() < deadline:
            with engine.connect() as connection:
                connection.execute(text("SELECT pg_stat_clear_snapshot()"))
                row = connection.execute(
                    text(
                        """
                        SELECT application_name, wait_event_type, wait_event
                        FROM pg_stat_activity
                        WHERE application_name LIKE :application_prefix
                          AND wait_event_type = 'Lock'
                        ORDER BY application_name
                        LIMIT 1
                        """
                    ),
                    {"application_prefix": f"{application_prefix}%"},
                ).one_or_none()
            if row is not None:
                return (
                    cast(str, row.application_name),
                    cast(str, row.wait_event_type),
                    cast(str, row.wait_event),
                )
            time.sleep(0.02)
    finally:
        engine.dispose()
    raise AssertionError("concurrent revision registration did not reach a PostgreSQL lock wait")


def _concurrent_registrations(
    *,
    context: Any,
    runner_id: uuid.UUID,
    scope_id: uuid.UUID,
    revisions: tuple[str, str],
    database_url: str,
    application_prefix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, str, int]], tuple[str, str, str]]:
    initial_lookup_barrier = threading.Barrier(2)
    holder_ready = threading.Event()
    release_holder = threading.Event()
    holder_selection_lock = threading.Lock()
    holder_selected = False
    original_lookup = WorkspaceRepository.get_repository_handle_by_opaque

    def synchronized_lookup(
        repository: WorkspaceRepository,
        lookup_runner_id: uuid.UUID,
        opaque_handle: str,
        *,
        lock: bool = False,
    ) -> Any:
        nonlocal holder_selected
        result = original_lookup(
            repository,
            lookup_runner_id,
            opaque_handle,
            lock=lock,
        )
        if not lock:
            initial_lookup_barrier.wait(timeout=5)
            return result
        with holder_selection_lock:
            hold_lock = not holder_selected
            holder_selected = True
        if hold_lock:
            holder_ready.set()
            if not release_holder.wait(timeout=5):
                raise AssertionError("timed out holding the first revision-authority lock")
        return result

    monkeypatch.setattr(
        WorkspaceRepository,
        "get_repository_handle_by_opaque",
        synchronized_lookup,
    )

    def revise(item: tuple[int, str]) -> tuple[str, str, int]:
        sequence, revision = item
        engine = create_engine(
            database_url,
            connect_args={
                "application_name": f"{application_prefix}{sequence}-{uuid.uuid4()}",
            },
        )
        try:
            with Session(engine) as session:
                runner = session.get(Runner, runner_id)
                assert runner is not None
                response = WorkspaceService(session).register_repository(
                    runner,
                    RepositoryRegistrationRequest.model_validate(
                        _registration_payload(context, revision)
                    ),
                    request_id=str(uuid.uuid4()),
                )
                scope = session.get(ReviewFreshnessState, scope_id)
                assert scope is not None
                return revision, response.current_revision, scope.generation
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(revise, item)
            for item in enumerate(
                revisions,
                start=1,
            )
        ]
        assert holder_ready.wait(timeout=5)
        try:
            lock_observation = _wait_for_revision_lock(
                database_url,
                application_prefix,
            )
        finally:
            release_holder.set()
        outcomes = [future.result(timeout=10) for future in futures]
    return outcomes, lock_observation


def test_concurrent_identical_revision_replay_returns_one_final_generation(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    decided = _approve(
        client,
        package_payload,
        key=f"remediation-3-ready-{uuid.uuid4()}",
    )
    readiness_response = client.post(f"/api/v1/review-packages/{package_id}/readiness")
    assert readiness_response.status_code == 200, readiness_response.text
    assert readiness_response.json()["readiness"]["effective_verdict"] == "ready"

    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope_id = package.freshness_state_id
    original_generation = package.freshness_generation
    original_blocker_summary_digest = package.blocker_summary_digest
    runner_id = uuid.UUID(cast(str, context.runner["runner_id"]))
    decision_id = uuid.UUID(cast(str, cast(dict[str, Any], decided["decision"])["id"]))
    ready_id = uuid.UUID(cast(str, readiness_response.json()["readiness"]["id"]))
    db_session.close()

    application_prefix = f"ve-r3-identical-{uuid.uuid4().hex[:8]}-"
    outcomes, lock_observation = _concurrent_registrations(
        context=context,
        runner_id=runner_id,
        scope_id=scope_id,
        revisions=(IDENTICAL_REVISION, IDENTICAL_REVISION),
        database_url=database_url,
        application_prefix=application_prefix,
        monkeypatch=monkeypatch,
    )

    assert outcomes == [
        (IDENTICAL_REVISION, IDENTICAL_REVISION, original_generation + 1),
        (IDENTICAL_REVISION, IDENTICAL_REVISION, original_generation + 1),
    ]

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            stored = session.get(ReviewPackage, package_id)
            scope = session.get(ReviewFreshnessState, scope_id)
            assert stored is not None
            assert scope is not None
            assert scope.generation == original_generation + 1
            assert stored.blocker_summary_digest == original_blocker_summary_digest
            assert _invalidation(session, package_id) is not None
            assert len(_invalidation_events(session, package_id)) == 1
            decisions = list(
                session.scalars(
                    select(ReviewDecision).where(ReviewDecision.review_package_id == package_id)
                )
            )
            readiness_rows = list(
                session.scalars(
                    select(ReleaseReadinessVerdict).where(
                        ReleaseReadinessVerdict.review_package_id == package_id
                    )
                )
            )
            assert [decision.id for decision in decisions] == [decision_id]
            assert [readiness.id for readiness in readiness_rows] == [ready_id]

    finally:
        engine.dispose()

    observed = client.get(f"/api/v1/review-packages/{package_id}")
    assert observed.status_code == 200, observed.text
    assert observed.json()["freshness"] == "stale"
    assert observed.json()["readiness"]["effective_verdict"] == "stale"
    print(
        "REMEDIATION_3_LEDGER concurrent_identical "
        + json.dumps(
            {
                "input_revisions": [IDENTICAL_REVISION, IDENTICAL_REVISION],
                "initial_generation": original_generation,
                "registration_outcomes": outcomes,
                "final_generation": original_generation + 1,
                "invalidation_rows": 1,
                "invalidation_events": 1,
                "decision_rows": 1,
                "ready_rows": 1,
                "effective_ready": "stale",
                "lock_observation": lock_observation,
            },
            sort_keys=True,
        )
    )


def test_concurrent_different_revisions_remain_distinct_transitions(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope_id = package.freshness_state_id
    original_generation = package.freshness_generation
    runner_id = uuid.UUID(cast(str, context.runner["runner_id"]))
    handle_id = package.repository_handle_id
    db_session.close()

    application_prefix = f"ve-r3-different-{uuid.uuid4().hex[:8]}-"
    outcomes, lock_observation = _concurrent_registrations(
        context=context,
        runner_id=runner_id,
        scope_id=scope_id,
        revisions=(IDENTICAL_REVISION, OTHER_REVISION),
        database_url=database_url,
        application_prefix=application_prefix,
        monkeypatch=monkeypatch,
    )
    assert {input_revision for input_revision, _returned, _generation in outcomes} == {
        IDENTICAL_REVISION,
        OTHER_REVISION,
    }
    assert all(
        input_revision == returned_revision for input_revision, returned_revision, _ in outcomes
    )

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            scope = session.get(ReviewFreshnessState, scope_id)
            current_revision = session.execute(
                text("SELECT current_revision FROM repository_handles WHERE id = :id"),
                {"id": handle_id},
            ).scalar_one()
            assert scope is not None
            assert scope.generation == original_generation + 2
            assert current_revision in {IDENTICAL_REVISION, OTHER_REVISION}
            assert _invalidation(session, package_id) is not None
            assert len(_invalidation_events(session, package_id)) == 1
            assert session.scalar(select(ReviewDecision)) is None
            assert session.scalar(select(ReleaseReadinessVerdict)) is None
            print(
                "REMEDIATION_3_LEDGER concurrent_different "
                + json.dumps(
                    {
                        "input_revisions": [IDENTICAL_REVISION, OTHER_REVISION],
                        "initial_generation": original_generation,
                        "registration_outcomes": outcomes,
                        "final_generation": scope.generation,
                        "final_revision": current_revision,
                        "invalidation_rows": 1,
                        "invalidation_events": 1,
                        "decision_rows": 0,
                        "ready_rows": 0,
                        "lock_observation": lock_observation,
                    },
                    sort_keys=True,
                )
            )
    finally:
        engine.dispose()
