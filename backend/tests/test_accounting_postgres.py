"""Real PostgreSQL persistence and serialization guarantees, in disposable schemas."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from src.accounting.contracts import Batch, PortfolioCreate
from src.accounting.repository import LedgerRepository
from src.research.repository import ResearchConflict

from tests.test_accounting_api import cash
from tests.test_research_migrations import migration_config
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def create(engine: Engine):  # type: ignore[no-untyped-def]
    with Session(engine) as session, session.begin():
        return LedgerRepository(session).create_portfolio(
            PortfolioCreate(
                id=uuid4(),
                name="Synthetic",
                base_currency="GBP",
                broker="Lightyear",
                account_label="Test ISA",
            )
        )


def test_exact_pg_amount_and_all_rows_immutable(postgres_engine: Engine) -> None:
    portfolio = create(postgres_engine)
    amount = "12345678901234567890.1234567890"
    batch = Batch.model_validate(dict(expected_version=0, transactions=[cash(amount=amount)]))
    with Session(postgres_engine) as session, session.begin():
        result = LedgerRepository(session).evaluate(portfolio.id, batch, save=True)
    with Session(postgres_engine) as session, session.begin():
        repo = LedgerRepository(session)
        assert repo.state(portfolio.id).cash[0].amount == Decimal(amount)
        assert repo.history(portfolio.id, 100, 0).transactions == result.transactions
        retry = repo.evaluate(portfolio.id, batch, save=True)
        assert retry.inserted == 0 and retry.duplicates == 1
    for table in ("accounting_portfolios", "accounting_transactions"):
        for sql in (f"UPDATE {table} SET id = id", f"DELETE FROM {table}"):
            with postgres_engine.connect() as connection:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(sql))
                connection.rollback()


def test_simultaneous_identical_imports_record_cash_once(postgres_engine: Engine) -> None:
    portfolio = create(postgres_engine)
    barrier = Barrier(2)
    batch = Batch.model_validate(dict(expected_version=0, transactions=[cash()]))

    def append(_: int) -> int:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=15)
            with session.begin():
                return LedgerRepository(session).evaluate(portfolio.id, batch, save=True).inserted

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(append, [1, 2])) == [0, 1]
    with Session(postgres_engine) as session, session.begin():
        assert LedgerRepository(session).state(portfolio.id).cash[0].amount == 1000


def test_concurrent_different_writers_cannot_overspend(postgres_engine: Engine) -> None:
    portfolio = create(postgres_engine)
    with Session(postgres_engine) as session, session.begin():
        LedgerRepository(session).evaluate(
            portfolio.id,
            Batch.model_validate(dict(expected_version=0, transactions=[cash()])),
            save=True,
        )
    barrier = Barrier(2)

    def append(ref: str) -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=15)
            try:
                with session.begin():
                    LedgerRepository(session).evaluate(
                        portfolio.id,
                        Batch.model_validate(
                            dict(
                                expected_version=1,
                                transactions=[cash(ref, type="WITHDRAWAL", amount="800")],
                            )
                        ),
                        save=True,
                    )
                return "saved"
            except ResearchConflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(append, ["a", "b"])) == ["conflict", "saved"]
    with Session(postgres_engine) as session, session.begin():
        assert LedgerRepository(session).state(portfolio.id).cash[0].amount == 200


def test_ledger_downgrade_preserves_research_and_reupgrade(postgres_engine: Engine) -> None:
    from src.research.repository import ResearchRepository

    from tests.test_research_repository import security

    with Session(postgres_engine) as session, session.begin():
        asset = security(ResearchRepository(session))
    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "20260909_02")
        assert connection.execute(text("SELECT count(*) FROM research_securities")).scalar() == 1
        command.upgrade(config, "head")
    with Session(postgres_engine) as session:
        from src.research.tables import Security

        assert session.get(Security, asset.id) is not None
