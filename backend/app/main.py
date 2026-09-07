import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db
from app.modules.catalog.router import router as catalog_router

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(catalog_router)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness: the process is answering. Deliberately does not touch the database."""
    return {"status": "ok"}


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
