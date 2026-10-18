import json
import logging
from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient


class TagsResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int = -1):
        return self.payload if size < 0 else self.payload[:size]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "health.db"))
    monkeypatch.setenv("APP_ENV", "test")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_liveness_does_not_depend_on_inference(client):
    live = client.get("/api/health/live")
    existing = client.get("/api/health")
    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert existing.json() == {"status": "ok"}


def test_readiness_checks_sqlite(client):
    ready = client.get("/api/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}


def test_inference_reports_configured_model_without_license_text(client, monkeypatch):
    monkeypatch.setattr(
        "app.health.request.urlopen",
        lambda *_args, **_kwargs: TagsResponse({"models": [{"name": "gemma2:2b"}]}),
    )
    response = client.get("/api/health/inference")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "gemma2:2b"}
    assert "license" not in response.text


def test_inference_unavailable_is_503(client, monkeypatch):
    def down(*_args, **_kwargs):
        raise URLError("down")

    monkeypatch.setattr("app.health.request.urlopen", down)
    response = client.get("/api/health/inference")
    assert response.status_code == 503
    assert response.json()["code"] == "extraction_unavailable"


def test_inference_response_limit_is_bounded(client, monkeypatch):
    from app.config import get_settings

    get_settings().ollama_max_response_bytes = 8
    monkeypatch.setattr(
        "app.health.request.urlopen",
        lambda *_args, **_kwargs: TagsResponse({"models": [{"name": "gemma2:2b"}]}),
    )
    response = client.get("/api/health/inference")
    assert response.status_code == 503
    assert response.json()["code"] == "extraction_unavailable"


def test_production_rejects_wildcard_cors(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "prod.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with pytest.raises(RuntimeError, match="wildcard"):
        create_app()
    get_settings.cache_clear()


def test_production_public_ollama_requires_a_key(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://proveniq.example")
    monkeypatch.setenv("OLLAMA_HOST", "https://models.example")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "prod.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with pytest.raises(RuntimeError, match="private Ollama host"):
        create_app()
    get_settings.cache_clear()


def test_production_public_ollama_with_key_is_still_refused(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://proveniq.example")
    monkeypatch.setenv("OLLAMA_HOST", "https://models.example")
    monkeypatch.setenv("OLLAMA_API_KEY", "not-a-proxy")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "prod-key.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with pytest.raises(RuntimeError, match="does not secure a public Ollama endpoint"):
        create_app()
    get_settings.cache_clear()


def test_access_log_omits_license_text(client, caplog):
    notice = "SECRET-NOTICE-TEXT-NOT-FOR-LOGS"
    with caplog.at_level(logging.INFO, logger="proveniq.access"):
        client.post(
            "/api/projects",
            json={
                "name": "Log check",
                "client_label": notice,
                "declared_intended_use": "noncommercial",
            },
        )
    assert notice not in caplog.text
    assert "POST /api/projects" in caplog.text


def test_request_body_limit_returns_safe_413(client):
    response = client.post("/api/projects", content=b"x" * (2_097_152 + 1))
    assert response.status_code == 413
    assert response.json() == {
        "code": "request_too_large",
        "message": "Request body exceeds the configured limit.",
        "details": [],
    }
