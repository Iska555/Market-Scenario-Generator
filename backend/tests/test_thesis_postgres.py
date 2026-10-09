"""Real PostgreSQL guarantees for immutable thesis versions and competing writers."""

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from src.research.repository import ResearchConflict, ResearchRepository
from src.research.thesis.repository import ThesisRepository
from src.research.thesis.schemas import ReviewCreate, RevisionCreate, ThesisCreate

from tests.test_research_migrations import migration_config
from tests.test_research_repository import security
from tests.test_thesis_backend import CONTENT, REVIEW

pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL test database")
    admin = create_engine(url)
    schema = "test_thesis_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-c search_path={schema}"})
    try:
        with engine.begin() as connection:
            config = migration_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_postgresql_thesis_precision_and_immutable_records(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as session, session.begin():
        asset = security(ResearchRepository(session))
        thesis = ThesisRepository(session).create_thesis(
            ThesisCreate.model_validate(
                {
                    **CONTENT,
                    "security_id": asset.id,
                    "target_high": "12345678901234567890.1234567890",
                }
            )
        )
        ThesisRepository(session).create_review(
            thesis.id, ReviewCreate.model_validate({**REVIEW, "revision_id": thesis.latest.id})
        )
    with Session(postgres_engine) as session:
        saved = ThesisRepository(session).get_thesis(thesis.id)
        assert saved.latest.target_high == Decimal("12345678901234567890.1234567890")
    for table in ("research_theses", "research_thesis_revisions", "research_thesis_reviews"):
        for statement in (f"UPDATE {table} SET id = id", f"DELETE FROM {table}"):
            with postgres_engine.connect() as connection:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(statement))
                connection.rollback()


def test_competing_revision_writers_preserve_original(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as session, session.begin():
        asset = security(ResearchRepository(session))
        original = ThesisRepository(session).create_thesis(
            ThesisCreate.model_validate({**CONTENT, "security_id": asset.id})
        )
    barrier = Barrier(2)

    def write(note: str) -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            try:
                with session.begin():
                    revision = ThesisRepository(session).append_revision(
                        original.id,
                        RevisionCreate.model_validate(
                            {**CONTENT, "expected_revision": 1, "notes": note}
                        ),
                    )
                    assert revision.revision == 2
                return "saved"
            except ResearchConflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, ["Writer A", "Writer B"]))
    assert sorted(outcomes) == ["conflict", "saved"]
    with Session(postgres_engine) as session:
        repo = ThesisRepository(session)
        assert repo.get_thesis(original.id).latest.revision == 2
        assert repo.get_thesis(original.id, as_of=original.latest.created_at) == original


def test_database_rejects_review_of_another_thesis_revision(postgres_engine: Engine) -> None:
    from src.research.thesis.tables import ThesisReview

    with Session(postgres_engine) as session, session.begin():
        asset = security(ResearchRepository(session))
        repo = ThesisRepository(session)
        first = repo.create_thesis(
            ThesisCreate.model_validate({**CONTENT, "security_id": asset.id})
        )
        second = repo.create_thesis(
            ThesisCreate.model_validate({**CONTENT, "security_id": asset.id})
        )
    with Session(postgres_engine) as session:
        invalid = ThesisReview(
            **ReviewCreate.model_validate({**REVIEW, "revision_id": second.latest.id}).model_dump(),
            thesis_id=first.id,
            reviewed_at=second.latest.created_at,
        )
        session.add(invalid)
        with pytest.raises(DBAPIError, match="foreign key"):
            session.commit()
        session.rollback()


def test_upgrade_and_downgrade_preserve_existing_research(postgres_engine: Engine) -> None:
    from src.research.tables import Security

    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "20260908_01")
    with Session(postgres_engine) as session, session.begin():
        asset = security(ResearchRepository(session))
    with postgres_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with Session(postgres_engine) as session:
        assert session.get(Security, asset.id) is not None
    with postgres_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "20260908_01")
    with Session(postgres_engine) as session:
        assert session.get(Security, asset.id) is not None
