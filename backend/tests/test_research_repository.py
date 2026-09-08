"""Synthetic research history tests run against SQLite and optional isolated PostgreSQL."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from src.research.repository import ResearchConflict, ResearchNotFound, ResearchRepository
from src.research.schemas import SecurityCreate, SecurityRead
from src.research.tables import Base

from tests.test_research_contracts import fact


@pytest.fixture(params=["sqlite"] + (["postgres"] if os.environ.get("TEST_DATABASE_URL") else []))
def session(request: pytest.FixtureRequest) -> Iterator[Session]:
    engine = create_engine(
        os.environ["TEST_DATABASE_URL"] if request.param == "postgres" else "sqlite://",
        connect_args={} if request.param == "postgres" else {"autocommit": False},
    )
    schema = "test_research_" + uuid4().hex
    try:
        with engine.connect() as connection:
            if request.param == "postgres":
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            connection.commit()
            try:
                with Session(connection) as unit:
                    yield unit
            finally:
                connection.rollback()
                if request.param == "postgres":
                    connection.execute(text("SET search_path TO public"))
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                    connection.commit()
    finally:
        engine.dispose()


def security(repo: ResearchRepository) -> SecurityRead:
    return repo.create_security(
        SecurityCreate.model_validate(
            {
                "ticker": "AAA",
                "name": "Example",
                "exchange": "XNAS",
                "currency": "USD",
                "country": "US",
            }
        )
    )


def test_restated_fact_never_leaks_into_earlier_publication_query(session: Session) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    original = repo.import_observations(asset.id, [fact()])[0]
    revised = fact(
        value="0.20",
        reported_at="2025-04-01T12:00:00Z",
        fetched_at="2025-04-02T12:00:00Z",
        source_record_id="revision-2",
    )
    repo.import_observations(asset.id, [revised])
    assert repo.observations(asset.id, datetime(2025, 1, 1, tzinfo=UTC)) == []
    earlier = repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC))
    assert [item.id for item in earlier] == [original.id]
    later = repo.observations(asset.id, datetime(2025, 5, 1, tzinfo=UTC))
    assert [item.value for item in later] == [revised.value]


def test_known_at_uses_server_recording_not_just_claimed_fetch_time(session: Session) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    saved = repo.import_observations(asset.id, [fact()])[0]
    # Imported now, even though originally published/fetched in 2025.
    assert (
        repo.observations(
            asset.id, datetime(2025, 3, 1, tzinfo=UTC), known_at=datetime(2025, 3, 1, tzinfo=UTC)
        )
        == []
    )
    assert (
        repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC), known_at=saved.recorded_at)[
            0
        ].id
        == saved.id
    )


def test_identical_import_reuses_fact_and_changed_content_conflicts(session: Session) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    saved = repo.import_observations(asset.id, [fact()])[0]
    repeated = repo.import_observations(
        asset.id, [fact(value="0.1000", fetched_at="2025-03-01T00:00:00Z")]
    )[0]
    assert repeated.id == saved.id
    assert repeated.fetched_at == saved.fetched_at
    with pytest.raises(ResearchConflict):
        repo.import_observations(asset.id, [fact(value="0.2")])


def test_batch_conflict_rolls_back_earlier_batch_insert(session: Session) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    repo.import_observations(asset.id, [fact()])
    with pytest.raises(ResearchConflict):
        repo.import_observations(
            asset.id, [fact(source_record_id="new", source="other"), fact(value="0.9")]
        )
    assert len(repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC))) == 1


def test_sources_and_period_bases_remain_separate(session: Session) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    repo.import_observations(
        asset.id,
        [
            fact(),
            fact(source="other", value="0.5"),
            fact(source_record_id="adjusted", basis="adjusted", value="0.3"),
        ],
    )
    assert len(repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC))) == 3
    assert len(repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC), source="other")) == 1


def test_security_rename_preserves_identity_and_observations(session: Session) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    saved = repo.import_observations(asset.id, [fact()])[0]
    changed = repo.update_security(
        asset.id,
        SecurityCreate.model_validate(
            {
                "ticker": "NEW",
                "name": "Example",
                "exchange": "XNAS",
                "currency": "USD",
                "country": "US",
            }
        ),
    )
    assert changed.id == asset.id
    assert repo.get_security(asset.id).ticker == "NEW"
    assert repo.observations(asset.id, datetime(2025, 3, 1, tzinfo=UTC))[0].id == saved.id


def test_unknown_security_and_duplicate_label_fail(session: Session) -> None:
    from uuid import uuid4

    repo = ResearchRepository(session)
    with pytest.raises(ResearchNotFound):
        repo.get_security(uuid4())
    security(repo)
    with pytest.raises(ResearchConflict):
        security(repo)


def test_same_publication_cannot_silently_choose_between_conflicting_versions(
    session: Session,
) -> None:
    repo = ResearchRepository(session)
    asset = security(repo)
    repo.import_observations(asset.id, [fact()])
    with pytest.raises(ResearchConflict):
        repo.import_observations(asset.id, [fact(source_record_id="ambiguous", value="0.8")])
