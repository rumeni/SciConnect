from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SciConnect API"
    app_env: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://sciconnect:sciconnect-dev@localhost:5432/sciconnect",
        validation_alias=AliasChoices("DATABASE_URL", "APP_DATABASE_URL"),
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Turning an institution address into map coordinates calls an external
    # service, so it can be switched off for offline or air-gapped runs.
    geocoding_enabled: bool = True
    geocoding_url: str = "https://nominatim.openstreetmap.org/search"
    geocoding_timeout_seconds: float = 8.0
    # Nominatim's usage policy requires an identifying User-Agent. Point this at
    # your own deployment before using the public service in earnest.
    geocoding_user_agent: str = "SciConnect/0.1 (https://example.org/sciconnect)"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
