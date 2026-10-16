"""Actual migrations and competing identity writers in isolated PostgreSQL schemas."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from src.accounting.contracts import Batch, PortfolioCreate
from src.accounting.repository import LedgerRepository
from src.accounting.tables import Portfolio
from src.public_track_record.contracts import DemoCreate, PortfolioContext
from src.public_track_record.repository import create_demo, portfolios
from src.public_track_record.tables import PortfolioIdentityRow
from src.research.repository import ResearchConflict
from src.research.tables import Base

from tests.test_accounting_api import cash
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_migrations import migration_config
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


@pytest.fixture
def engine(postgres_engine: Engine) -> Engine:
    return postgres_engine


def test_actual_postgres_owner_api_creation_and_legacy_isolation(client: TestClient) -> None:
    from tests.test_accounting_api import account

    legacy = account(client)
    body = demo().model_dump(mode="json")
    path = "/api/portfolio-identity/portfolios"
    response = client.post(path, json=body)
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    created = response.json()
    assert client.post(path, json=body).json() == created
    assert client.post(path, json=body | {"id": legacy["id"]}).status_code == 409
    assert client.get(path, headers={"X-Research-Key": "wrong"}).status_code == 401
    listed = client.get(path).json()
    assert len(listed) == 2
    assert listed[0]["identity"]["mode"] == "unclassified"
    assert listed[1]["identity"]["mode"] == "demo"


def demo() -> DemoCreate:
    return DemoCreate(
        id=uuid4(), name="Synthetic migration example", base_currency="GBP", mode="demo"
    )


def test_empty_head_and_upgrade_existing_ledger_preserve_private_history(
    postgres_engine: Engine,
) -> None:
    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        command.downgrade(config, "20261011_04")
        assert "portfolio_identities" not in inspect(connection).get_table_names()
    with Session(postgres_engine) as session, session.begin():
        repo = LedgerRepository(session)
        legacy = repo.create_portfolio(
            PortfolioCreate(
                id=uuid4(),
                name="Legacy called demo or real",
                base_currency="GBP",
                broker="Lightyear",
                account_label="Unverified label",
            )
        )
        saved = repo.evaluate(
            legacy.id,
            Batch.model_validate(dict(expected_version=0, transactions=[cash()])),
            save=True,
        )
        empty = repo.create_portfolio(
            PortfolioCreate(
                id=uuid4(),
                name="Empty old record",
                base_currency="GBP",
                broker="Unverified",
                account_label="Private",
            )
        )
    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        assert connection.execute(text("SELECT count(*) FROM portfolio_identities")).scalar() == 0
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    with Session(postgres_engine) as session, session.begin():
        repo = LedgerRepository(session)
        assert repo.history(legacy.id, 100, 0).transactions == saved.transactions
        assert repo.state(legacy.id).cash[0].amount == 1000
        assert all(row.identity.mode == "unclassified" for row in portfolios(repo))
        for portfolio_id in (legacy.id, empty.id):
            with pytest.raises(ResearchConflict, match="relabelled"):
                create_demo(repo, demo().model_copy(update={"id": portfolio_id}))
        created = create_demo(repo, demo())
        assert created.identity.recorded_at == created.created_at
        assert created.version == 0
    # Database guard also rejects retroactive classification, even a backdated
    # timestamp on the empty legacy row; application checks are not the sole fence.
    for portfolio_id in (legacy.id, empty.id):
        with postgres_engine.connect() as connection:
            with pytest.raises(DBAPIError, match="at birth"):
                connection.execute(
                    text("""INSERT INTO portfolio_identities
                    SELECT id, 'demo', created_at FROM accounting_portfolios WHERE id = :id"""),
                    {"id": portfolio_id},
                )
            connection.rollback()


def test_storage_rejects_relabelling_deletion_and_invalid_mode(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as session, session.begin():
        created = create_demo(LedgerRepository(session), demo())
    for sql in (
        "UPDATE portfolio_identities SET mode = 'real'",
        "UPDATE portfolio_identities SET mode = 'paper'",
        "DELETE FROM portfolio_identities",
    ):
        with postgres_engine.connect() as connection:
            with pytest.raises(DBAPIError, match="append-only"):
                connection.execute(text(sql))
            connection.rollback()
    with Session(postgres_engine) as session, session.begin():
        row = session.get(PortfolioIdentityRow, created.id)
        assert row is not None and row.mode == "demo"
        legacy = Portfolio(
            id=uuid4(),
            name="Invalid identity fixture",
            base_currency="GBP",
            broker="Synthetic",
            account_label="Test",
            created_at=datetime.now(UTC),
        )
        session.add(legacy)
        session.flush()
        legacy_id = legacy.id
        with pytest.raises(DBAPIError, match="ck_portfolio_mode"), session.begin_nested():
            session.add(
                PortfolioIdentityRow(
                    portfolio_id=legacy.id, mode="unknown", recorded_at=legacy.created_at
                )
            )
            session.flush()
    with Session(postgres_engine) as session, session.begin():
        assert session.get(PortfolioIdentityRow, legacy_id) is None


def test_concurrent_demo_creation_is_atomic_and_retryable(postgres_engine: Engine) -> None:
    data = demo()
    barrier = Barrier(2)

    def create(_: int) -> PortfolioContext | None:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=15)
            try:
                with session.begin():
                    return create_demo(LedgerRepository(session), data)
            except ResearchConflict:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert any(result is not None for result in results)
    with Session(postgres_engine) as session, session.begin():
        repo = LedgerRepository(session)
        retried = create_demo(repo, data)
        assert len(portfolios(repo)) == 1 and retried.identity.mode == "demo"
        assert session.get(PortfolioIdentityRow, UUID(str(data.id))) is not None
        for result in results:
            if result is not None:
                assert result == retried
