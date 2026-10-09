"""Performance transport preserves PostgreSQL records and locks a coherent ledger."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.performance import routes
from src.performance.contracts import PerformanceReport, PerformanceRequest
from src.performance.replay import verify_replay
from src.research import database

from tests.test_accounting_api import account, cash
from tests.test_research_api import KEY
from tests.test_research_api import configured as configured
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_client(configured: None, postgres_engine: Engine) -> Iterator[TestClient]:
    app.dependency_overrides[database.get_engine] = lambda: postgres_engine
    try:
        with TestClient(app, headers={"X-Research-Key": KEY}) as client:
            yield client
    finally:
        app.dependency_overrides.pop(database.get_engine, None)


def snapshot(engine: Engine) -> dict[str, list[str]]:
    with engine.connect() as connection:
        return {
            table: sorted(
                connection.execute(text(f'SELECT row_to_json(t)::text FROM "{table}" t')).scalars()
            )
            for table in inspect(connection).get_table_names()
        }


def setup(client: TestClient) -> tuple[str, dict[str, Any]]:
    portfolio = account(client)
    root = f"/api/accounting/portfolios/{portfolio['id']}"
    result = client.post(
        root + "/transactions",
        json={
            "expected_version": 0,
            "transactions": [
                cash(),
                cash("fee", type="FEE", amount="10", effective_at="2025-01-02T12:00:00Z"),
            ],
        },
    )
    assert result.status_code == 200, result.text
    return f"/api/performance/portfolios/{portfolio['id']}/report", {
        "expected_version": 2,
        "known_at": datetime.now(UTC).isoformat(),
        "daily_marks": [{"date": "2025-01-01"}, {"date": "2025-01-02"}],
    }


def test_pg_report_and_replay_preserve_every_migrated_table(
    pg_client: TestClient, postgres_engine: Engine
) -> None:
    path, body = setup(pg_client)
    before = snapshot(postgres_engine)
    response = pg_client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    saved = PerformanceReport.model_validate_json(response.content)
    assert saved.daily[-1].nav == 990
    assert saved.twr.value == pytest.approx(-0.01)
    verify_replay(saved)
    assert snapshot(postgres_engine) == before
    repeated = pg_client.post(path, json=body)
    assert repeated.json() == response.json()


def test_pg_report_holds_lock_and_later_write_invalidates_version(
    pg_client: TestClient, postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, body = setup(pg_client)
    original = routes.build_report
    blocked = []

    def checked(
        portfolio_id: UUID, currency: str, rows: Any, data: PerformanceRequest
    ) -> PerformanceReport:
        # A separate connection must be unable to acquire the portfolio lock
        # while the actual report endpoint is calculating its snapshot.
        with Session(postgres_engine) as contender, contender.begin():
            contender.execute(text("SET LOCAL lock_timeout = '250ms'"))
            with pytest.raises(OperationalError) as failure:
                LedgerRepository(contender).portfolio(portfolio_id)
            assert getattr(failure.value.orig, "sqlstate", None) == "55P03"
            blocked.append(True)
        return original(portfolio_id, currency, rows, data)

    monkeypatch.setattr(routes, "build_report", checked)
    response = pg_client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert blocked == [True]
    monkeypatch.setattr(routes, "build_report", original)
    portfolio_id = response.json()["portfolio_id"]
    write = pg_client.post(
        f"/api/accounting/portfolios/{portfolio_id}/transactions",
        json={
            "expected_version": 2,
            "transactions": [
                cash("fee-2", type="FEE", amount="40", effective_at="2025-01-02T13:00:00Z")
            ],
        },
    )
    assert write.status_code == 200, write.text
    assert pg_client.post(path, json=body).status_code == 409
    refreshed = pg_client.post(
        path, json=body | {"expected_version": 3, "known_at": datetime.now(UTC).isoformat()}
    )
    assert refreshed.status_code == 200, refreshed.text
    assert Decimal(refreshed.json()["daily"][-1]["nav"]) == 950
    assert refreshed.json()["twr"]["value"] == pytest.approx(-0.05)
