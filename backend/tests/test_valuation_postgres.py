"""Real PostgreSQL evidence precision, temporal boundaries and stateless valuation replay."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.research.repository import ResearchRepository
from src.research.schemas import SecurityCreate
from src.research.thesis.repository import ThesisRepository
from src.research.thesis.schemas import RevisionCreate, ThesisCreate
from src.valuation.contracts import FundamentalRequest, UserViewRequest
from src.valuation.service import evaluate

from tests.test_research_contracts import fact
from tests.test_research_migrations import migration_config
from tests.test_research_repository import security
from tests.test_thesis_backend import CONTENT, SECURITY
from tests.test_valuation_contracts import context
from tests.test_valuation_models import assumptions

pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL test database")
    admin = create_engine(url)
    schema = "test_valuation_" + uuid4().hex
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


def database_snapshot(engine: Engine) -> dict[str, list[str]]:
    """Capture every migrated table and complete row, including the migration version."""
    with engine.connect() as connection:
        inspector = inspect(connection)
        schema = connection.scalar(text("SELECT current_schema()"))
        tables = inspector.get_table_names(schema=schema)
        quote = engine.dialect.identifier_preparer.quote
        return {
            name: list(
                connection.scalars(
                    text(f"SELECT to_jsonb(t)::text FROM {quote(name)} AS t ORDER BY 1")
                )
            )
            for name in tables
        }


def test_evaluation_preserves_exact_evidence_and_replays_without_database_writes(
    postgres_engine: Engine,
) -> None:
    exact = Decimal("12345678901234567890.1234567890")
    with Session(postgres_engine) as session, session.begin():
        repo = ResearchRepository(session)
        asset = security(repo)
        observation = repo.import_observations(
            asset.id,
            [fact(metric="market_cap", unit="currency", currency="USD", value=str(exact))],
        )[0]
        theses = ThesisRepository(session)
        thesis = theses.create_thesis(
            ThesisCreate.model_validate({**CONTENT, "security_id": asset.id})
        )
        later = theses.append_revision(
            thesis.id,
            RevisionCreate.model_validate(
                {**CONTENT, "expected_revision": 1, "notes": "Later owner assumption"}
            ),
        )
    before = database_snapshot(postgres_engine)
    cutoff = datetime.now(UTC)
    request = FundamentalRequest(
        context=context(
            security_id=asset.id,
            valuation_date=cutoff.date(),
            as_of=cutoff,
            known_at=cutoff,
            observation_ids=[observation.id],
            thesis_revision_id=thesis.latest.id,
        ),
        assumptions=assumptions(price_observed_at=cutoff),
    )
    with Session(postgres_engine) as session, session.begin():
        first = evaluate(session, request)
    assert first.manifest.observations[0].value == exact
    assert first.manifest.observations[0].model_dump(mode="json")["value"] == str(exact)
    assert first.manifest.observations[0].id == observation.id
    assert first.manifest.thesis_revision == thesis.latest
    assert first.manifest.thesis_revision.id != later.id
    assert first.result.kind == "valuation_result"
    assert first.result.returns.cumulative_return == pytest.approx(0.391)
    replay_request = FundamentalRequest.model_validate(first.manifest.resolved_inputs)
    # Replay in a new session from the returned input contract, not retained ORM objects.
    with Session(postgres_engine) as session, session.begin():
        replay = evaluate(session, replay_request)
    assert replay.result == first.result
    assert replay.manifest.input_sha256 == first.manifest.input_sha256
    assert replay.manifest.evidence_sha256 == first.manifest.evidence_sha256
    assert replay.manifest.observations == first.manifest.observations
    assert replay.manifest.thesis_revision == first.manifest.thesis_revision
    assert database_snapshot(postgres_engine) == before


def test_observation_publication_and_system_knowledge_boundaries(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as session, session.begin():
        repo = ResearchRepository(session)
        asset = security(repo)
        observation = repo.import_observations(asset.id, [fact()])[0]
    ctx = context(
        security_id=asset.id,
        valuation_date=observation.recorded_at.date(),
        as_of=observation.reported_at,
        known_at=observation.recorded_at,
        observation_ids=[observation.id],
    )
    before = database_snapshot(postgres_engine)
    with Session(postgres_engine) as session, session.begin():
        accepted = evaluate(
            session,
            UserViewRequest(context=ctx, annualized_return=Decimal("0.0800"), rationale="Owner"),
        )
    assert accepted.manifest.observations[0] == observation
    assert accepted.manifest.resolved_inputs["annualized_return"] == "0.0800"
    # Each exact cutoff is inclusive; one microsecond before either is insufficient.
    for field, cutoff in (
        ("as_of", observation.reported_at),
        ("known_at", observation.recorded_at),
    ):
        unavailable = context(**{**ctx.model_dump(), field: cutoff - timedelta(microseconds=1)})
        with Session(postgres_engine) as session, session.begin():
            with pytest.raises(ValueError, match="not available under requested cutoffs"):
                evaluate(
                    session,
                    UserViewRequest(
                        context=unavailable, annualized_return=Decimal("0.08"), rationale="Owner"
                    ),
                )
    assert database_snapshot(postgres_engine) == before


def test_thesis_revision_cutoffs_and_cross_security_evidence_are_rejected(
    postgres_engine: Engine,
) -> None:
    with Session(postgres_engine) as session, session.begin():
        repo = ResearchRepository(session)
        asset = security(repo)
        other = repo.create_security(SecurityCreate.model_validate({**SECURITY, "ticker": "BBB"}))
        observation = repo.import_observations(other.id, [fact()])[0]
        thesis = ThesisRepository(session).create_thesis(
            ThesisCreate.model_validate({**CONTENT, "security_id": asset.id})
        )
    cutoff = thesis.latest.created_at
    ctx = context(
        security_id=asset.id,
        valuation_date=cutoff.date(),
        as_of=cutoff,
        known_at=cutoff,
        thesis_revision_id=thesis.latest.id,
    )
    before = database_snapshot(postgres_engine)
    with Session(postgres_engine) as session, session.begin():
        accepted = evaluate(
            session,
            UserViewRequest(context=ctx, annualized_return=Decimal("0.08"), rationale="Owner"),
        )
    assert accepted.manifest.thesis_revision == thesis.latest
    invalid_contexts: list[tuple[dict[str, Any], str]] = [
        ({"as_of": cutoff - timedelta(microseconds=1)}, "not available"),
        ({"known_at": cutoff - timedelta(microseconds=1)}, "not available"),
        ({"security_id": other.id}, "Thesis revision must belong"),
        ({"thesis_revision_id": uuid4()}, "Thesis revision must belong"),
        ({"observation_ids": [observation.id]}, "Evidence observation must belong"),
        ({"observation_ids": [uuid4()]}, "Evidence observation must belong"),
    ]
    for update, message in invalid_contexts:
        invalid = context(**{**ctx.model_dump(), **update})
        with Session(postgres_engine) as session, session.begin():
            with pytest.raises(ValueError, match=message):
                evaluate(
                    session,
                    UserViewRequest(
                        context=invalid, annualized_return=Decimal("0.08"), rationale="Owner"
                    ),
                )
    assert database_snapshot(postgres_engine) == before
