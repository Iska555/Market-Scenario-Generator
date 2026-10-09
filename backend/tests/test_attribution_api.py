"""Read-only contribution API retains performance auth/version/data boundaries."""

from uuid import uuid4

from fastapi.testclient import TestClient
from src.attribution.contracts import ContributionReport
from src.attribution.replay import verify_contribution

from tests.test_accounting_api import account, cash
from tests.test_performance_api import body
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def test_cash_contribution_same_snapshot_private_and_replayable(client: TestClient) -> None:
    portfolio = account(client)
    root = f"/api/accounting/portfolios/{portfolio['id']}"
    saved = client.post(
        root + "/transactions", json=dict(expected_version=0, transactions=[cash()])
    )
    data = body()
    data["known_at"] = saved.json()["transactions"][0]["recorded_at"]
    path = f"/api/attribution/portfolios/{portfolio['id']}/contribution"
    response = client.post(path, json=data)
    assert response.status_code == 200, response.text
    result = ContributionReport.model_validate_json(response.content)
    assert result.performance.twr.value == 0
    assert result.reconciliation.component_total.value == 0
    assert result.reconciliation.within_tolerance
    assert response.headers["cache-control"] == "no-store"
    verify_contribution(result)
    assert client.get(root + "/transactions").json()["total"] == 1
    assert client.post(path, json=data).json() == response.json()


def test_contribution_auth_stale_future_and_missing_portfolio(client: TestClient) -> None:
    path = f"/api/attribution/portfolios/{uuid4()}/contribution"
    assert client.post(path, json=body(), headers={"X-Research-Key": "bad"}).status_code == 401
    assert client.post(path, json=body()).status_code == 404
    portfolio = account(client)
    path = f"/api/attribution/portfolios/{portfolio['id']}/contribution"
    assert client.post(path, json=body()).status_code == 409
    for changes in (
        {"known_at": "2999-01-01T00:00:00Z"},
        {"price_convention": "total_return_adjusted"},
        {"confidence": 1},
    ):
        response = client.post(path, json=body(0) | changes)
        assert response.status_code == 422
        assert "input" not in str(response.json())


def test_empty_contribution_is_typed_undefined(client: TestClient) -> None:
    portfolio = account(client)
    path = f"/api/attribution/portfolios/{portfolio['id']}/contribution"
    result = client.post(path, json=body(0))
    assert result.status_code == 200
    assert result.json()["reconciliation"]["within_tolerance"] is None
    assert result.json()["top_contributors"] == []
