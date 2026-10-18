import ipaddress
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: Path = Path("./data/licensetrail.db")
    database_url: str | None = None
    app_env: str = "development"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma2:2b"
    ollama_timeout_seconds: float = Field(default=60, gt=0, le=600)
    ollama_health_timeout_seconds: float = Field(default=3, gt=0, le=60)
    ollama_api_key: str | None = None
    request_timeout_seconds: float = Field(default=150, gt=0, le=900)
    # Two MiB leaves room for JSON encoding overhead while preserving the 200,000-character text contract.
    max_request_body_bytes: int = Field(default=2_097_152, gt=0, le=16_777_216)
    ollama_max_response_bytes: int = Field(default=1_048_576, gt=0, le=16_777_216)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def sqlite_database_path(self) -> Path:
        """Local SQLite file. A Postgres URL is refused so it cannot be mistaken for a live connection."""
        url = (self.database_url or "").strip()
        if not url:
            return self.database_path
        if url.startswith("sqlite:///"):
            raw = url.removeprefix("sqlite:///")
            if not raw:
                raise RuntimeError("DATABASE_URL sqlite path is empty. Use DATABASE_PATH or sqlite:///./data/licensetrail.db.")
            return Path(raw)
        lowered = url.split(":", 1)[0].lower()
        if lowered in {"postgres", "postgresql"}:
            raise RuntimeError(
                "PostgreSQL is not connected. Proveniq uses SQLite, including PRAGMA foreign_keys and ON CONFLICT. "
                "Unset DATABASE_URL to keep the local file. A Postgres migration is not implemented."
            )
        raise RuntimeError("DATABASE_URL must be empty or start with sqlite:///. The URL value was not logged.")

    def normalized_env(self) -> str:
        value = (self.app_env or "development").strip().lower()
        if value not in {"development", "test", "production"}:
            raise RuntimeError("APP_ENV must be development, test, or production.")
        return value

    def validate_runtime(self) -> None:
        environment = self.normalized_env()
        origins = self.cors_origin_list
        if not origins or any(origin == "*" for origin in origins):
            if environment == "production":
                raise RuntimeError("Production CORS_ORIGINS must be an explicit list. A wildcard origin is not allowed.")
        self._require_private_or_authenticated_inference(environment)

    def _require_private_or_authenticated_inference(self, environment: str) -> None:
        if environment != "production":
            return
        host = (urlparse(self.ollama_host).hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}:
            return
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback):
            return
        raise RuntimeError(
            "Production inference must use a private Ollama host reachable only from the API. "
            "OLLAMA_API_KEY is forwarded to an existing proxy but does not secure a public Ollama endpoint. "
            "The host was not logged."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
