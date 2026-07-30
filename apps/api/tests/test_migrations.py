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
        "runners",
        "permission_envelopes",
        "runner_jobs",
        "runner_job_attempts",
        "runner_job_events",
        "review_packages",
        "review_package_invalidations",
        "review_decisions",
        "release_readiness_verdicts",
    }.issubset(inspect(engine).get_table_names())
    engine.dispose()
