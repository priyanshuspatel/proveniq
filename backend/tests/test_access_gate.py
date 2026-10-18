import logging

import pytest
from fastapi.testclient import TestClient

from conftest import TEST_ACCESS_TOKEN


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "access-gate.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_missing_access_token_refuses_app_start(monkeypatch, tmp_path):
    monkeypatch.delenv("PROVENIQ_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "missing-token.db"))
    from app.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="PROVENIQ_ACCESS_TOKEN"):
        from app.main import create_app

        create_app()
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "path",
    ["/api/health", "/api/health/live", "/api/health/ready", "/api/health/inference"],
)
def test_safe_health_endpoints_are_public(client, path):
    response = client.get(path)
    assert response.status_code != 401


def test_missing_authorization_is_rejected(client):
    response = client.get("/api/projects")
    assert response.status_code == 401
    assert response.json() == {
        "code": "authentication_required",
        "message": "A valid access token is required.",
        "details": [],
    }
    assert "PROVENIQ_ACCESS_TOKEN" not in response.text


def test_invalid_token_is_rejected(client):
    response = client.get("/api/projects", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_valid_token_can_access_protected_route(client):
    response = client.get("/api/projects", headers={"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == []


def test_authentication_does_not_leak_credentials_to_logs_or_errors(client, caplog):
    submitted = "credential-that-must-not-appear"
    with caplog.at_level(logging.INFO, logger="proveniq.access"):
        response = client.get("/api/projects", headers={"Authorization": f"Bearer {submitted}"})

    assert response.status_code == 401
    assert submitted not in response.text
    assert submitted not in caplog.text


def test_options_preflight_remains_public_and_allows_authorization(client):
    response = client.options(
        "/api/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
