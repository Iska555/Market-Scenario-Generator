"""Actual PostgreSQL immutability, retained lock and stale correction acceptance."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.factors import routes
from src.factors.contracts import FactorReport
from src.factors.replay import verify_factor_report

from tests.test_accounting_api import account, cash
from tests.test_factors_api import factor_body
from tests.test_performance_postgres import pg_client as pg_client
from tests.test_performance_postgres import snapshot
from tests.test_research_api import configured as configured
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def setup(client: TestClient) -> tuple[str, str, dict[str, Any]]:
    portfolio = account(client)["id"]
    path = f"/api/accounting/portfolios/{portfolio}/transactions"
    response = client.post(
        path,
        json=dict(
            expected_version=0,
            transactions=[
                cash(),
                cash("fee", type="FEE", amount="10", effective_at="2025-01-02T13:00:00Z"),
            ],
        ),
    )
    assert response.status_code == 200, response.text
    return portfolio, path, factor_body(2)


def test_pg_every_table_unchanged_repeated_complete_fit_and_replay(
    pg_client: TestClient, postgres_engine: Engine
) -> None:
    portfolio, _, body = setup(pg_client)
    before = snapshot(postgres_engine)
    path = f"/api/factors/portfolios/{portfolio}/report"
    response = pg_client.post(path, json=body)
    assert response.status_code == 200, response.text
    result = FactorReport.model_validate_json(response.content)
    assert result.performance.daily[-1].nav == 990 and result.fit_reason is None
    verify_factor_report(result)
    assert snapshot(postgres_engine) == before
    assert pg_client.post(path, json=body).json() == response.json()
    assert response.headers["cache-control"] == "no-store"


def test_pg_locked_calculation_stale_then_corrected_fee_changes_fit(
    pg_client: TestClient, postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    portfolio, ledger, body = setup(pg_client)
    original = routes.build_factor_report
    blocked = []

    def checked(*args: Any, **kwargs: Any) -> FactorReport:
        with Session(postgres_engine) as other, other.begin():
            other.execute(text("SET LOCAL lock_timeout='250ms'"))
            with pytest.raises(OperationalError) as failure:
                LedgerRepository(other).portfolio(args[0].portfolio_id)
            assert getattr(failure.value.orig, "sqlstate", None) == "55P03"
            blocked.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(routes, "build_factor_report", checked)
    path = f"/api/factors/portfolios/{portfolio}/report"
    response = pg_client.post(path, json=body)
    assert response.status_code == 200 and blocked == [True]
    old = response.json()["coefficients"]["alpha"]["coefficient"]["value"]
    monkeypatch.setattr(routes, "build_factor_report", original)
    response = pg_client.post(
        ledger,
        json=dict(
            expected_version=2,
            transactions=[
                cash("fee-2", type="FEE", amount="40", effective_at="2025-01-02T14:00:00Z")
            ],
        ),
    )
    assert response.status_code == 200
    assert pg_client.post(path, json=body).status_code == 409
    response = pg_client.post(path, json=factor_body(3))
    assert response.status_code == 200, response.text
    assert response.json()["performance"]["daily"][-1]["nav"] == "950.0000000000"
    assert response.json()["coefficients"]["alpha"]["coefficient"]["value"] != old
    verify_factor_report(FactorReport.model_validate_json(response.content))
