from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.main import app


def test_liveness_does_not_require_database(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_hides_database_failure() -> None:
    broken_session = Mock(spec=Session)
    broken_session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("secret"))

    def broken_db() -> Session:
        return broken_session

    app.dependency_overrides[get_db] = broken_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/health/ready")
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_not_ready"
    assert "secret" not in response.text


def test_request_id_is_generated_and_returned(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.headers["x-request-id"]
    assert response.json() == {"status": "ok"}


def test_valid_request_id_is_propagated(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "foundation-test-42"})
    assert response.headers["x-request-id"] == "foundation-test-42"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "contains spaces"})
    assert response.headers["x-request-id"] != "contains spaces"


def test_cors_allows_only_configured_local_origin(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"

    denied = client.options(
        "/api/v1/tasks",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
