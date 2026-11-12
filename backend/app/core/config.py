from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Environments that are treated as a real deployment, where a missing admin
# token or a wildcard origin is a refusal to start rather than a convenience.
PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod", "staging"})


class Settings(BaseSettings):
    app_name: str = "SciConnect API"
    # Named explicitly: with the APP_ prefix the field alone would be read from
    # APP_APP_ENV, so the APP_ENV every compose file sets would be ignored and
    # the production checks below would never run.
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "APP_APP_ENV"),
    )
    database_url: str = Field(
        default="postgresql+psycopg://sciconnect:sciconnect-dev@localhost:5432/sciconnect",
        validation_alias=AliasChoices("DATABASE_URL", "APP_DATABASE_URL"),
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("database_url")
    @classmethod
    def use_installed_postgres_driver(cls, value: str) -> str:
        """Name the driver this project actually ships.

        Managed hosts inject a driverless URL (`postgresql://…`, or the legacy
        Heroku-style `postgres://…`). SQLAlchemy 2.0 reads a driverless
        PostgreSQL URL as psycopg2, which is not installed here: the project
        uses psycopg 3. SQLAlchemy 2.1 defaults to psycopg, but the dependency
        range allows both, and `postgres://` is not understood by either.
        Naming the driver keeps a host-supplied URL working on any of them.
        """
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return f"postgresql+psycopg://{value[len(prefix):]}"
        return value

    # Turning an institution address into map coordinates calls an external
    # service, so it can be switched off for offline or air-gapped runs.
    geocoding_enabled: bool = True
    geocoding_url: str = "https://nominatim.openstreetmap.org/search"
    geocoding_timeout_seconds: float = 8.0
    # Nominatim's usage policy requires an identifying User-Agent. Point this at
    # your own deployment before using the public service in earnest.
    geocoding_user_agent: str = "SciConnect/0.1 (https://example.org/sciconnect)"

    # --- Writing to the catalog -------------------------------------------
    # Every POST and DELETE carries this secret in an `X-Admin-Token` header.
    # Empty means "writes are open", which is refused outside development: see
    # `refuse_an_unsafe_production_configuration` below.
    admin_token: str = ""

    # --- Who may reach the API --------------------------------------------
    # Host header allowlist. `["*"]` accepts any name, which lets an attacker
    # reach the API through a hostname of their own choosing and is therefore
    # refused in production.
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    # How many reverse proxies sit in front. The client address is read from
    # `X-Forwarded-For` only this many hops deep, so a request cannot forge its
    # own address by sending the header itself. 0 means "no proxy, trust the
    # socket". One Caddy in front is 1.
    trusted_proxy_hops: int = 0

    # --- Rate limiting -----------------------------------------------------
    # Each limit is "<count>/<second|minute|hour>", counted per client address
    # over a sliding window. Writes are scarcer than reads, and the geocoding
    # proxy is scarcest: it spends someone else's quota on every call.
    rate_limit_enabled: bool = True
    rate_limit_read: str = "120/minute"
    rate_limit_write: str = "20/minute"
    rate_limit_geocode: str = "10/minute"
    # Checking an admin key. Each attempt is a guess at the secret, so this is
    # the tightest budget of all: a 48-character random key is out of reach
    # anyway, and this keeps a weak one that slipped through out of reach too.
    rate_limit_auth: str = "5/minute"
    # A hard ceiling on tracked clients, so a flood of forged addresses cannot
    # grow the counters without bound.
    rate_limit_max_clients: int = 20_000

    # --- Request shape -----------------------------------------------------
    # The largest JSON body any write accepts. The catalog's payloads are a few
    # hundred bytes; this is generous and still refuses a memory-exhausting body.
    max_body_bytes: int = 256 * 1024

    # --- Interactive documentation -----------------------------------------
    # `/docs` publishes every write endpoint and its payload shape. Useful while
    # developing, an invitation once the API is public, so it follows app_env
    # unless set explicitly.
    docs_enabled: bool | None = None

    # Send HSTS even when the request arrived over plain HTTP. The proxy
    # terminates TLS and forwards HTTP, so in production the header has to be
    # sent unconditionally to reach the browser at all.
    hsts_enabled: bool | None = None

    log_level: Literal["critical", "error", "warning", "info", "debug"] = "info"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in PRODUCTION_ENVIRONMENTS

    @property
    def serve_docs(self) -> bool:
        """Interactive docs: explicit setting first, otherwise off in production."""
        if self.docs_enabled is not None:
            return self.docs_enabled
        return not self.is_production

    @property
    def send_hsts(self) -> bool:
        if self.hsts_enabled is not None:
            return self.hsts_enabled
        return self.is_production

    @property
    def writes_require_a_token(self) -> bool:
        return bool(self.admin_token)

    @model_validator(mode="after")
    def refuse_an_unsafe_production_configuration(self) -> "Settings":
        """Fail to start rather than serve a deployment that is open to anyone.

        Each of these is harmless while developing on localhost and a real hole
        once the app answers on a domain, so the check is tied to app_env rather
        than left to a deployment checklist.
        """
        if not self.is_production:
            return self

        problems: list[str] = []

        if not self.admin_token:
            problems.append(
                "APP_ADMIN_TOKEN is not set, which would leave every POST and "
                "DELETE open to anyone who can reach the API"
            )
        elif len(self.admin_token) < 32:
            problems.append(
                "APP_ADMIN_TOKEN is shorter than 32 characters; generate one with "
                "`openssl rand -base64 48`"
            )

        if not self.cors_origins or "*" in self.cors_origins:
            problems.append(
                "APP_CORS_ORIGINS must name the site's own origins; '*' lets any "
                "page on the internet call this API from a visitor's browser"
            )

        insecure_origins = [
            origin
            for origin in self.cors_origins
            if origin.startswith("http://") and not _is_loopback(origin)
        ]
        if insecure_origins:
            problems.append(
                f"APP_CORS_ORIGINS contains plain-HTTP origins {insecure_origins}; "
                "use https:// for a public site"
            )

        if "*" in self.allowed_hosts:
            problems.append(
                "APP_ALLOWED_HOSTS must name the domains this API answers on, "
                "not '*'"
            )

        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL points at SQLite, which is not a production database")

        if problems:
            raise ValueError(
                "Refusing to start in "
                f"{self.app_env!r} with an unsafe configuration:\n  - "
                + "\n  - ".join(problems)
            )
        return self


def _is_loopback(origin: str) -> bool:
    host = origin.removeprefix("http://").split(":", 1)[0]
    return host in {"localhost", "127.0.0.1", "[::1]", "::1"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
