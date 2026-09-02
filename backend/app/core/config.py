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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
