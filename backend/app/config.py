from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: Path = Path("./data/licensetrail.db")
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma2:2b"
    ollama_timeout_seconds: float = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
