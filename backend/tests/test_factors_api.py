"""Private coherent report transport and sanitized invalid/stale requests."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from src.factors.contracts import FactorReport
from src.factors.replay import verify_factor_report

from tests.test_accounting_api import account, cash
from tests.test_factors_engine import factor_evidence
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def factor_body(version: int = 1, n: int = 32) -> dict[str, Any]:
    return dict(
        performance=dict(
            expected_version=version,
            known_at=datetime.now(UTC).isoformat(),
            daily_marks=[
                dict(date=(date(2025, 1, 1) + timedelta(days=i)).isoformat()) for i in range(n + 1)
            ],
        ),
        factors=factor_evidence(n).model_dump(mode="json"),
        include_contribution=True,
    )


def test_private_coherent_repeatable_read_only_report_and_replay(client: TestClient) -> None:
    p = account(client)
    accounting = f"/api/accounting/portfolios/{p['id']}"
    client.post(accounting + "/transactions", json=dict(expected_version=0, transactions=[cash()]))
    path = f"/api/factors/portfolios/{p['id']}/report"
    data = factor_body()
    response = client.post(path, json=data)
    assert response.status_code == 200, response.text
    result = FactorReport.model_validate_json(response.content)
    assert result.fit_reason is None and result.paired_intervals == 32
    assert result.contribution is not None and result.contribution.performance == result.performance
    verify_factor_report(result)
    assert response.headers.get("cache-control") == "no-store", response.text
    assert client.post(path, json=data).json() == response.json()
    assert client.get(accounting + "/transactions").json()["total"] == 1
    data["include_contribution"] = False
    assert client.post(path, json=data).json()["contribution"] is None


def test_auth_missing_account_stale_version_and_sanitized_invalid_evidence(
    client: TestClient,
) -> None:
    path = f"/api/factors/portfolios/{uuid4()}/report"
    assert (
        client.post(path, json=factor_body(), headers={"X-Research-Key": "bad"}).status_code == 401
    )
    assert client.post(path, json=factor_body()).status_code == 404
    p = account(client)
    path = f"/api/factors/portfolios/{p['id']}/report"
    assert client.post(path, json=factor_body()).status_code == 409
    for field in ("currency", "future", "invalid"):
        body = factor_body(0)
        if field == "currency":
            body["factors"]["identity"]["currency"] = "USD"
        elif field == "future":
            body["factors"]["identity"]["retrieved_at"] = "2999-01-01T00:00:00Z"
        else:
            body["factors"]["rows"][0]["risk_free_return"] = "private-invalid-payload"
        response = client.post(path, json=body)
        assert response.status_code == 422
        assert response.headers.get("cache-control") == "no-store", response.text
        assert "private-invalid-payload" not in response.text


def test_empty_factor_coverage_keeps_performance_and_no_invented_fit(client: TestClient) -> None:
    p = account(client)
    client.post(
        f"/api/accounting/portfolios/{p['id']}/transactions",
        json=dict(expected_version=0, transactions=[cash()]),
    )
    body = factor_body()
    body["factors"]["rows"] = []
    response = client.post(f"/api/factors/portfolios/{p['id']}/report", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["performance"]["twr"]["value"] == 0
    assert data["paired_intervals"] == 0 and data["fit_reason"] == "incomplete_paired_coverage"
    assert data["coefficients"]["alpha"]["coefficient"]["value"] is None
    verify_factor_report(FactorReport.model_validate(data))
