from pathlib import Path

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_unset_database_url_keeps_the_sqlite_file(monkeypatch, tmp_path):
    database = tmp_path / "kept.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    assert get_settings().sqlite_database_path() == database
    assert not database.exists()


def test_sqlite_url_selects_that_file_without_using_the_default(monkeypatch, tmp_path):
    selected = tmp_path / "selected.db"
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "other.db"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{selected}")
    get_settings.cache_clear()
    assert get_settings().sqlite_database_path() == Path(str(selected))


def test_postgres_url_is_refused_and_does_not_echo_the_url(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "should-not-matter.db"))
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:secret-value@db.example:5432/proveniq")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError) as caught:
        get_settings().sqlite_database_path()
    message = str(caught.value)
    assert "PostgreSQL is not connected" in message
    assert "secret-value" not in message
    assert "db.example" not in message


def test_ollama_and_request_limits_reject_unsafe_configuration(monkeypatch):
    from pydantic import ValidationError

    monkeypatch.setenv("OLLAMA_MAX_RESPONSE_BYTES", "0")
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "-1")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()
