from alembic import command
from sqlalchemy import create_engine, inspect

from conftest import alembic_config


def test_initial_migration_round_trip(database_url: str) -> None:
    config = alembic_config()
    engine = create_engine(database_url)

    command.downgrade(config, "base")
    assert "tasks" not in inspect(engine).get_table_names()

    command.upgrade(config, "head")
    assert {
        "tasks",
        "runs",
        "repository_snapshots",
        "plans",
        "approval_decisions",
        "audit_events",
        "ai_plan_requests",
        "ai_provider_traces",
        "ai_eval_results",
        "ai_plan_decisions",
        "runners",
        "permission_envelopes",
        "runner_jobs",
        "runner_job_attempts",
        "runner_job_events",
        "review_freshness_states",
        "review_blocker_findings",
        "review_packages",
        "review_package_invalidations",
        "review_decisions",
        "release_readiness_verdicts",
    }.issubset(inspect(engine).get_table_names())
    engine.dispose()
