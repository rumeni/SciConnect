import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import engine, get_db
from app.core.ratelimit import RateLimitMiddleware, parse_limit
from app.core.security import (
    ADMIN_TOKEN_HEADER,
    AdminTokenMiddleware,
    BodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.modules.catalog.router import router as catalog_router

logger = logging.getLogger(__name__)

# Read the configured limits once, at import, so a malformed value stops the
# process here with a clear message instead of on the first request that would
# have been limited.
for _name in ("rate_limit_read", "rate_limit_write", "rate_limit_geocode", "rate_limit_auth"):
    parse_limit(getattr(settings, _name))

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Say out loud, once, what this process will and will not allow.

    A deployment that is accidentally open is hard to notice from the outside;
    one line in the startup log makes it obvious in the place people look first.
    """
    if settings.writes_require_a_token:
        logger.info("Writes require the %s header", ADMIN_TOKEN_HEADER)
    else:
        logger.warning(
            "APP_ADMIN_TOKEN is not set: every POST and DELETE is open. "
            "This is refused when APP_ENV is production."
        )
    if settings.rate_limit_enabled:
        logger.info(
            "Rate limits: reads %s, writes %s, geocoding %s, trusting %d proxy hop(s)",
            settings.rate_limit_read,
            settings.rate_limit_write,
            settings.rate_limit_geocode,
            settings.trusted_proxy_hops,
        )
    else:
        logger.warning("Rate limiting is switched off")
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    version="0.1.0",
    # The interactive docs list every write endpoint and the exact shape of its
    # payload. That is a feature while developing and a map for an attacker once
    # the API is public, so they follow the environment.
    docs_url="/docs" if settings.serve_docs else None,
    redoc_url="/redoc" if settings.serve_docs else None,
    openapi_url="/openapi.json" if settings.serve_docs else None,
)

# Middleware is applied outermost-last, so this list reads inside-out: the admin
# gate sits closest to the routes, and the host check is the first thing a
# request meets. CORS deliberately wraps the rate limiter, so that a browser
# shown a 429 can read the status instead of an opaque network error.
app.add_middleware(AdminTokenMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # No cookie or browser credential is used: the admin token travels in a
    # header the page sets itself. Leaving credentials off keeps a stolen
    # session from being replayed from another origin.
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", ADMIN_TOKEN_HEADER],
    expose_headers=["Retry-After", "RateLimit-Limit", "RateLimit-Policy"],
    max_age=600,
)
app.add_middleware(SecurityHeadersMiddleware)
if "*" not in settings.allowed_hosts:
    # A request whose Host header names something else is not for this API.
    # Starlette answers it with 400 before any route runs.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

app.include_router(catalog_router)


@app.post("/api/v1/auth/check", tags=["system"])
def check_admin_key() -> dict[str, object]:
    """Confirm that the key this browser holds opens the catalog for writing.

    The body does no checking of its own: this is a POST, so
    `AdminTokenMiddleware` has already refused it unless the key is right, and
    the rate limiter has counted it as a guess. Reaching this line is the
    answer. `key_required` is false only on a development server with no key
    configured, where any key is let through.
    """
    return {"role": "admin", "key_required": settings.writes_require_a_token}


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness: the process is answering. Deliberately does not touch the database."""
    return {"status": "ok"}


@app.head("/api/v1/health", tags=["system"])
def health_head() -> Response:
    """Allow uptime monitors to check liveness without a response body."""
    response = Response(status_code=status.HTTP_200_OK)
    # Omit the length rather than claiming that the GET representation is empty.
    del response.headers["content-length"]
    return response


def _probe(db: Session, sql: str) -> int | str | None:
    """Read one value, answering None when the query cannot run.

    A failed statement aborts the surrounding PostgreSQL transaction, so each
    probe rolls back on failure to leave the session usable for the next one.
    """
    try:
        return db.execute(text(sql)).scalar()
    except SQLAlchemyError:
        db.rollback()
        return None


@app.get("/api/v1/health/database", tags=["system"])
def database_health(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    """Readiness: proves the database answers, and reports what it holds.

    `503` means the database could not be reached. The reply names the error
    type only; the full message goes to the logs, because this endpoint is
    public and connection errors carry host and user names.
    """
    report: dict[str, object] = {"driver": engine.dialect.driver}

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.exception("Database health check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {**report, "database": "unavailable", "error": type(error).__name__}

    # Both probes are optional: they answer None on a database that is reachable
    # but not yet migrated, which is worth telling apart from an unreachable one.
    report["database"] = "ok"
    report["migration"] = _probe(db, "SELECT version_num FROM alembic_version")
    report["institutions"] = _probe(db, "SELECT count(*) FROM institutions")
    return report


@app.head("/api/v1/health/database", tags=["system"])
def database_health_head(db: Annotated[Session, Depends(get_db)]) -> Response:
    """Run the same database checks as GET, returning only the status and headers."""
    response = Response(status_code=status.HTTP_200_OK)
    database_health(response, db)
    del response.headers["content-length"]
    return response
