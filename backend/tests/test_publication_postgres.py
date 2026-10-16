"""Actual PostgreSQL publication, source coherence and serialized competing owners."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.public_track_record.publication import (
    PreviewIntent,
    PublishIntent,
    preview,
    publish,
    read_public,
)
from src.research.repository import ResearchConflict

from tests.test_demo_launch import setup
from tests.test_publication import (
    prepare,
)
from tests.test_publication import (
    test_immutable_versions_correction_withdrawal_and_republication as lifecycle,
)
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def test_postgres_lifecycle_and_immutable_storage(postgres_engine: Engine) -> None:
    lifecycle(postgres_engine)
    for table in ("publication_channels", "publication_previews", "publication_events"):
        for action in (f"UPDATE {table} SET id = id", f"DELETE FROM {table}"):
            with postgres_engine.connect() as connection:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(action))
                connection.rollback()


def test_competing_publishers_one_wins_and_exact_retry(postgres_engine: Engine) -> None:
    portfolio, _ = setup(postgres_engine)
    saved = prepare(postgres_engine, portfolio.id)
    barrier = Barrier(2)
    intents = [PublishIntent(id=uuid4(), preview_id=saved.id) for _ in range(2)]

    def run(intent: PublishIntent) -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=15)
            try:
                with session.begin():
                    return publish(LedgerRepository(session), intent).version
            except ResearchConflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, intents))
    assert outcomes.count("conflict") == 1
    winner = next(intent for intent in intents if str(intent.id) in outcomes)
    with Session(postgres_engine) as session, session.begin():
        repo = LedgerRepository(session)
        assert publish(repo, winner) == read_public(repo)


def test_source_change_rejects_preview_and_preserves_published_content(
    postgres_engine: Engine,
) -> None:
    portfolio, receipt = setup(postgres_engine)
    saved = prepare(postgres_engine, portfolio.id)
    with Session(postgres_engine) as session, session.begin():
        original = publish(
            LedgerRepository(session), PublishIntent(id=uuid4(), preview_id=saved.id)
        )
    stale = prepare(postgres_engine, portfolio.id)
    # Mutable registry metadata is deliberately outside the immutable ledger.
    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE research_securities SET name = 'Private edited name' WHERE id = :id"),
            {"id": receipt.securities["harbor"]},
        )
    with Session(postgres_engine) as session, session.begin():
        repo = LedgerRepository(session)
        with pytest.raises(ResearchConflict, match="source changed"):
            publish(
                repo,
                PublishIntent(
                    id=uuid4(),
                    preview_id=stale.id,
                    correction_of=UUID(original.version),
                    public_reason="Changed source.",
                ),
            )
        assert read_public(repo) == original


def test_preview_holds_source_write_fence(postgres_engine: Engine) -> None:
    portfolio, receipt = setup(postgres_engine)

    def competing_edit() -> str:
        with postgres_engine.connect() as connection:
            connection.execute(text("SET LOCAL lock_timeout = '250ms'"))
            try:
                connection.execute(
                    text("UPDATE research_securities SET name = 'Concurrent edit' WHERE id = :id"),
                    {"id": receipt.securities["harbor"]},
                )
            except DBAPIError as exc:
                connection.rollback()
                return str(exc.orig)
            connection.rollback()
            return "unexpected write"

    with Session(postgres_engine) as session, session.begin():
        preview(
            LedgerRepository(session),
            PreviewIntent(
                id=uuid4(), portfolio_id=portfolio.id, selected_research=["harbor", "orchard"]
            ),
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert "lock timeout" in pool.submit(competing_edit).result(timeout=15)
