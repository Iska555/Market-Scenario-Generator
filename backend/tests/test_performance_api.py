"""Private performance uses one ledger snapshot and never writes records."""

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_accounting_api import account, cash
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def body(version: int = 1) -> dict[str, Any]:
    return dict(
        expected_version=version,
        known_at="2025-12-31T23:59:59Z",
        daily_marks=[dict(date="2025-01-01"), dict(date="2025-01-02")],
    )


def test_report_cash_account_no_write_and_replay_evidence(client: TestClient) -> None:
    portfolio = account(client)
    root = f"/api/accounting/portfolios/{portfolio['id']}"
    saved = client.post(
        root + "/transactions", json=dict(expected_version=0, transactions=[cash()])
    )
    assert saved.status_code == 200
    # Knowledge cutoff must include the just-recorded row.
    data = body()
    data["known_at"] = saved.json()["transactions"][0]["recorded_at"]
    response = client.post(f"/api/performance/portfolios/{portfolio['id']}/report", json=data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["twr"]["value"] == 0
    assert result["daily"][-1]["nav"] == "1000"
    assert result["xirr"]["value"] == 0
    assert response.headers["cache-control"] == "no-store"
    assert result["manifest"]["inputs"]["price_convention"] == "unadjusted"
    assert result["manifest"]["ledger_records"][0]["id"] == saved.json()["transactions"][0]["id"]
    assert client.get(root + "/transactions").json()["total"] == 1


def test_auth_missing_portfolio_version_and_future_dates(client: TestClient) -> None:
    path = f"/api/performance/portfolios/{uuid4()}/report"
    assert client.post(path, json=body(), headers={"X-Research-Key": "wrong"}).status_code == 401
    assert client.post(path, json=body()).status_code == 404
    portfolio = account(client)
    path = f"/api/performance/portfolios/{portfolio['id']}/report"
    assert client.post(path, json=body()).status_code == 409
    assert client.post(path, json=body(0) | {"known_at": "2999-01-01T00:00:00Z"}).status_code == 422
    assert (
        client.post(
            path, json=body(0) | {"daily_marks": [dict(date="2999-01-01"), dict(date="2999-01-02")]}
        ).status_code
        == 422
    )


def test_invalid_calendar_and_adjusted_quotes_rejected_without_echo(client: TestClient) -> None:
    portfolio = account(client)
    path = f"/api/performance/portfolios/{portfolio['id']}/report"
    for changes in (
        {"price_convention": "total_return_adjusted"},
        {"calendar": "trading"},
        {"periods_per_year": 252},
        {"confidence": 1},
        {"risk_free_rate": -1},
    ):
        response = client.post(path, json=body(0) | changes)
        assert response.status_code == 422
        assert "input" not in response.json()["detail"][0]


def test_empty_account_has_no_fabricated_zero_return(client: TestClient) -> None:
    portfolio = account(client)
    response = client.post(f"/api/performance/portfolios/{portfolio['id']}/report", json=body(0))
    assert response.status_code == 200, response.text
    assert response.json()["twr"]["value"] is None
    assert response.json()["xirr"]["value"] is None
