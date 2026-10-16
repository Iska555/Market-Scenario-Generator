"""Real PostgreSQL verifies immutable demo receipts and serialized isolated loads."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.public_track_record.contracts import DemoCreate
from src.public_track_record.demo import DemoReceipt, load_demo
from src.public_track_record.repository import create_demo

from tests.test_demo_launch import counts, setup
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def test_postgres_fixture_idempotency_and_immutable_receipt(postgres_engine: Engine) -> None:
    portfolio, receipt = setup(postgres_engine)
    before = counts(postgres_engine)
    with Session(postgres_engine) as session, session.begin():
        assert load_demo(LedgerRepository(session), portfolio.id) == receipt
    assert counts(postgres_engine) == before == [1, 2, 13, 2, 4, 2]
    for sql in (
        "UPDATE demo_load_receipts SET receipt = receipt",
        "DELETE FROM demo_load_receipts",
    ):
        with postgres_engine.connect() as connection:
            with pytest.raises(DBAPIError, match="append-only"):
                connection.execute(text(sql))
            connection.rollback()


def test_concurrent_loads_create_one_complete_history(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as session, session.begin():
        portfolio = create_demo(
            LedgerRepository(session),
            DemoCreate(id=uuid4(), name="Synthetic", base_currency="GBP", mode="demo"),
        )
    barrier = Barrier(2)

    def load(_: int) -> DemoReceipt:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=15)
            with session.begin():
                return load_demo(LedgerRepository(session), portfolio.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(load, [1, 2]))
    assert receipts[0] == receipts[1]
    assert counts(postgres_engine) == [1, 2, 13, 2, 4, 2]
