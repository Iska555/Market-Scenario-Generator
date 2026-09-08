"""Alembic DDL and PostgreSQL-specific semantics, isolated from any user database."""

import io
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from src.research.repository import ResearchRepository
from src.research.tables import Base

from tests.test_research_contracts import fact
from tests.test_research_repository import security


def migration_config() -> Config:
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def test_migration_roundtrip_matches_declared_schema() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        command.downgrade(config, "base")
        assert inspect(connection).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_offline_postgresql_migration_includes_immutable_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")
    config = migration_config()
    buffer = io.StringIO()
    config.output_buffer = buffer
    command.upgrade(config, "head", sql=True)
    ddl = buffer.getvalue()
    assert "CREATE TABLE research_observations" in ddl
    assert "TIMESTAMP WITH TIME ZONE" in ddl
    assert "NUMERIC(30, 10)" in ddl
    assert "CREATE TRIGGER research_facts_immutable" in ddl


def test_migration_requires_explicit_postgresql_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        command.upgrade(migration_config(), "head")


@pytest.mark.postgres
def test_postgresql_migrations_precision_and_append_only() -> None:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL test database")
    from uuid import uuid4

    engine = create_engine(url)
    # Unique schema, never drop or migrate the supplied database's existing tables.
    schema = "test_research_" + uuid4().hex
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.commit()
            try:
                config = migration_config()
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
                connection.commit()
                with Session(connection) as session:
                    repo = ResearchRepository(session)
                    asset = security(repo)
                    expected = fact(value="12345678901234567890.1234567890")
                    saved = repo.import_observations(asset.id, [expected])[0]
                    session.commit()
                    session.expire_all()
                    from datetime import UTC, datetime

                    assert (
                        repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC))[0].value
                        == expected.value
                    )
                    session.rollback()
                    for operation in (
                        "UPDATE research_observations SET value = 1",
                        "DELETE FROM research_observations",
                    ):
                        with pytest.raises(DBAPIError, match="append-only"):
                            connection.execute(text(operation))
                        connection.rollback()
                    assert saved.security_id == asset.id
                command.downgrade(config, "base")
                connection.commit()
            finally:
                connection.rollback()
                connection.execute(text("SET search_path TO public"))
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                connection.commit()
    finally:
        engine.dispose()
