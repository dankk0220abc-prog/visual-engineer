import os
import secrets
from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    (
        "postgresql+psycopg://visualengineer:visualengineer-test-local"
        "@localhost:55433/visualengineer_test"
    ),
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["RUNNER_BOOTSTRAP_TOKEN"] = secrets.token_urlsafe(48)
os.environ["RUNNER_REAPER_ENABLED"] = "false"

from visual_engineer_api.core.config import get_settings  # noqa: E402
from visual_engineer_api.db.session import get_db, get_engine  # noqa: E402
from visual_engineer_api.main import app  # noqa: E402


def alembic_config() -> Config:
    config = Config("apps/api/alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture(scope="session")
def database_url() -> str:
    get_settings.cache_clear()
    get_engine.cache_clear()
    command.upgrade(alembic_config(), "head")
    return TEST_DATABASE_URL


@pytest.fixture
def db_session(database_url: str) -> Generator[Session, None, None]:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE validation_suite_results, validation_suite_step_runs, "
                "validation_suite_runs, validation_evidence, validation_step_runs, "
                "validation_runs, "
                "side_effect_permits, workspace_checkpoints, workspace_events, "
                "runner_job_events, runner_job_attempts, runner_jobs, workspaces, "
                "execution_grant_decisions, execution_grants, repository_handles, "
                "permission_envelopes, runners, audit_events, approval_decisions, "
                "plans, repository_snapshots, runs, tasks"
            )
        )
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_payload() -> dict[str, str]:
    return {
        "title": "Inspect foundation",
        "objective": "Create an inert task metadata record.",
        "repository_kind": "local_path",
        "repository_display_name": "Example repository",
        "repository_locator": "~/Developer/example",
    }


@pytest.fixture
def runner_bootstrap_token() -> str:
    return os.environ["RUNNER_BOOTSTRAP_TOKEN"]
