"""Opt-in research configuration; importing the app never opens a database."""

import os
import secrets
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def postgres_url(value: str) -> URL:
    """Reject implicit drivers and SQLite, including in accidental deployments."""
    url = make_url(value)
    if url.drivername != "postgresql+psycopg" or not url.database:
        raise ValueError("PostgreSQL with psycopg and an explicit database is required")
    return url


def require_research_access(
    x_research_key: Annotated[str | None, Header()] = None,
) -> None:
    key = os.environ.get("RESEARCH_API_KEY", "")
    try:
        postgres_url(os.environ.get("DATABASE_URL", ""))
        if len(key.strip()) < 32:
            raise ValueError("Owner key must contain at least 32 characters")
    except (ValueError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Research API is not configured") from exc
    if x_research_key is None or not secrets.compare_digest(x_research_key.encode(), key.encode()):
        raise HTTPException(status_code=401, detail="Invalid research API key")


@lru_cache(maxsize=1)
def build_engine(url: str) -> Engine:
    """Lazy pool construction; schema setup belongs to Alembic, never app startup."""
    return create_engine(postgres_url(url), pool_pre_ping=True)


def get_engine() -> Engine:
    try:
        return build_engine(os.environ.get("DATABASE_URL", ""))
    except (ValueError, SQLAlchemyError, ImportError) as exc:
        raise HTTPException(status_code=503, detail="Research database unavailable") from exc


def get_session(engine: Annotated[Engine, Depends(get_engine)]) -> Iterator[Session]:
    """Commit before HTTP success; context exit rolls back rejected/failed requests."""
    try:
        with Session(engine) as session, session.begin():
            yield session
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Research database unavailable") from exc
