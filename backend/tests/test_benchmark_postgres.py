"""Actual migrated PostgreSQL read-only, lock and correction acceptance."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.attribution.contracts import ContributionReport
from src.benchmark import routes
from src.benchmark.contracts import BenchmarkEvidence, ComparisonReport
from src.benchmark.replay import verify_comparison
from src.performance.contracts import PerformanceReport

from tests.test_accounting_api import cash
from tests.test_benchmark_engine import evidence
from tests.test_performance_postgres import pg_client as pg_client
from tests.test_performance_postgres import setup, snapshot
from tests.test_research_api import configured as configured
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def comparison_setup(client: TestClient) -> tuple[str, dict[str, Any]]:
    path, performance = setup(client)
    return path.replace("/performance/", "/benchmark/").replace("/report", "/comparison"), dict(
        performance=performance,
        benchmark=evidence("100", "101").model_dump(mode="json"),
        include_contribution=True,
    )


def test_pg_comparison_preserves_every_table_repeats_and_replays(
    pg_client: TestClient, postgres_engine: Engine
) -> None:
    path, data = comparison_setup(pg_client)
    before = snapshot(postgres_engine)
    response = pg_client.post(path, json=data)
    assert response.status_code == 200, response.text
    result = ComparisonReport.model_validate_json(response.content)
    assert result.performance.daily[-1].nav == 990
    assert result.cumulative_active_return.value == -0.02
    assert result.contribution is not None
    assert result.contribution.performance == result.performance
    verify_comparison(result)
    assert snapshot(postgres_engine) == before
    assert response.headers["cache-control"] == "no-store"
    assert pg_client.post(path, json=data).json() == response.json()


def test_pg_comparison_lock_stale_rejection_then_changed_fee_report(
    pg_client: TestClient, postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = comparison_setup(pg_client)
    original = routes.build_comparison
    blocked = []

    def checked(
        performance: PerformanceReport,
        benchmark: BenchmarkEvidence,
        contribution: ContributionReport | None = None,
    ) -> ComparisonReport:
        with Session(postgres_engine) as other, other.begin():
            other.execute(text("SET LOCAL lock_timeout = '250ms'"))
            with pytest.raises(OperationalError) as failure:
                LedgerRepository(other).portfolio(performance.portfolio_id)
            assert getattr(failure.value.orig, "sqlstate", None) == "55P03"
            blocked.append(True)
        return original(performance, benchmark, contribution)

    monkeypatch.setattr(routes, "build_comparison", checked)
    response = pg_client.post(path, json=data)
    assert response.status_code == 200, response.text
    assert blocked == [True]
    monkeypatch.setattr(routes, "build_comparison", original)
    portfolio = UUID(response.json()["performance"]["portfolio_id"])
    response = pg_client.post(
        f"/api/accounting/portfolios/{portfolio}/transactions",
        json=dict(
            expected_version=2,
            transactions=[
                cash("fee-2", type="FEE", amount="40", effective_at="2025-01-02T13:00:00Z")
            ],
        ),
    )
    assert response.status_code == 200
    assert pg_client.post(path, json=data).status_code == 409
    data["performance"].update(expected_version=3, known_at=datetime.now(UTC).isoformat())
    response = pg_client.post(path, json=data)
    assert response.status_code == 200, response.text
    assert response.json()["performance"]["twr"]["value"] == -0.05
    assert response.json()["cumulative_active_return"]["value"] == pytest.approx(-0.06)
