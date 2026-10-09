"""Actual migrated PostgreSQL read-only and coherent attribution acceptance."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.attribution import routes
from src.attribution.contracts import ContributionReport
from src.attribution.replay import verify_contribution
from src.performance.contracts import PerformanceReport

from tests.test_accounting_api import cash
from tests.test_performance_postgres import pg_client as pg_client
from tests.test_performance_postgres import setup, snapshot
from tests.test_research_api import configured as configured
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def test_pg_contribution_preserves_all_tables_and_replays(
    pg_client: TestClient, postgres_engine: Engine
) -> None:
    path, data = setup(pg_client)
    path = path.replace("/performance/", "/attribution/").replace("/report", "/contribution")
    before = snapshot(postgres_engine)
    response = pg_client.post(path, json=data)
    assert response.status_code == 200, response.text
    result = ContributionReport.model_validate_json(response.content)
    assert result.performance.daily[-1].nav == 990
    assert result.reconciliation.component_total.value == Decimal("-.01")
    assert result.reconciliation.within_tolerance
    verify_contribution(result)
    assert snapshot(postgres_engine) == before
    assert response.headers["cache-control"] == "no-store"
    assert pg_client.post(path, json=data).json() == response.json()


def test_pg_contribution_retains_lock_until_complete_then_rejects_stale_version(
    pg_client: TestClient, postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = setup(pg_client)
    path = path.replace("/performance/", "/attribution/").replace("/report", "/contribution")
    original = routes.build_contribution
    blocked = []

    def checked(performance: PerformanceReport) -> ContributionReport:
        with Session(postgres_engine) as contender, contender.begin():
            contender.execute(text("SET LOCAL lock_timeout = '250ms'"))
            with pytest.raises(OperationalError) as failure:
                LedgerRepository(contender).portfolio(performance.portfolio_id)
            assert getattr(failure.value.orig, "sqlstate", None) == "55P03"
            blocked.append(True)
        return original(performance)

    monkeypatch.setattr(routes, "build_contribution", checked)
    response = pg_client.post(path, json=data)
    assert response.status_code == 200, response.text
    assert blocked == [True]
    monkeypatch.setattr(routes, "build_contribution", original)
    portfolio_id = UUID(response.json()["performance"]["portfolio_id"])
    written = pg_client.post(
        f"/api/accounting/portfolios/{portfolio_id}/transactions",
        json={
            "expected_version": 2,
            "transactions": [
                cash("fee-2", type="FEE", amount="40", effective_at="2025-01-02T13:00:00Z")
            ],
        },
    )
    assert written.status_code == 200, written.text
    assert pg_client.post(path, json=data).status_code == 409
    refreshed = pg_client.post(
        path, json=data | {"expected_version": 3, "known_at": datetime.now(UTC).isoformat()}
    )
    assert refreshed.status_code == 200, refreshed.text
    assert Decimal(refreshed.json()["reconciliation"]["component_total"]["value"]) == Decimal(
        "-.05"
    )
