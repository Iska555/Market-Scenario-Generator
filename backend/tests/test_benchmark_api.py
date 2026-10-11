"""Private benchmark transport and inherited ledger/evidence boundaries."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from src.benchmark.contracts import ComparisonReport
from src.benchmark.replay import verify_comparison

from tests.test_accounting_api import account, cash
from tests.test_benchmark_engine import evidence
from tests.test_performance_api import body
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def comparison_body(version: int = 1, **changes: Any) -> dict[str, Any]:
    return (
        dict(
            performance=body(version) | {"known_at": datetime.now(UTC).isoformat()},
            benchmark=evidence("100", "101").model_dump(mode="json"),
            include_contribution=True,
        )
        | changes
    )


def test_comparison_private_no_store_one_snapshot_no_write_and_offline_replay(
    client: TestClient,
) -> None:
    portfolio = account(client)
    accounting = f"/api/accounting/portfolios/{portfolio['id']}"
    response = client.post(
        accounting + "/transactions", json=dict(expected_version=0, transactions=[cash()])
    )
    assert response.status_code == 200
    path = f"/api/benchmark/portfolios/{portfolio['id']}/comparison"
    data = comparison_body()
    response = client.post(path, json=data)
    assert response.status_code == 200, response.text
    result = ComparisonReport.model_validate_json(response.content)
    assert result.performance.twr.value == 0
    assert result.benchmark_return.value == 0.01
    assert result.cumulative_active_return.value == -0.01
    assert result.contribution is not None
    assert result.contribution.performance == result.performance
    assert result.statistics["beta"].reason == "insufficient_observations"
    verify_comparison(result)
    assert response.headers["cache-control"] == "no-store"
    assert client.get(accounting + "/transactions").json()["total"] == 1
    assert client.post(path, json=data).json() == response.json()
    without = client.post(path, json=comparison_body(include_contribution=False))
    assert without.status_code == 200 and without.json()["contribution"] is None


def test_comparison_auth_missing_account_stale_version_and_invalid_metadata(
    client: TestClient,
) -> None:
    path = f"/api/benchmark/portfolios/{uuid4()}/comparison"
    assert (
        client.post(path, json=comparison_body(), headers={"X-Research-Key": "bad"}).status_code
        == 401
    )
    assert client.post(path, json=comparison_body()).status_code == 404
    portfolio = account(client)
    path = f"/api/benchmark/portfolios/{portfolio['id']}/comparison"
    assert client.post(path, json=comparison_body()).status_code == 409
    for change in ("currency", "price_only", "calendar", "future"):
        data = comparison_body(0)
        if change == "currency":
            data["benchmark"]["identity"]["currency"] = "USD"
        elif change == "price_only":
            data["benchmark"]["identity"]["return_basis"] = "price_return"
        elif change == "calendar":
            data["benchmark"]["identity"]["calendar"] = "trading_daily"
        else:
            data["benchmark"]["identity"]["retrieved_at"] = "2999-01-01T00:00:00Z"
        response = client.post(path, json=data)
        assert response.status_code == 422, response.text
        assert '"input"' not in response.text


def test_empty_account_or_benchmark_has_typed_gaps_without_fabricated_zero(
    client: TestClient,
) -> None:
    portfolio = account(client)
    path = f"/api/benchmark/portfolios/{portfolio['id']}/comparison"
    data = comparison_body(0)
    data["benchmark"]["levels"] = []
    response = client.post(path, json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["performance"]["twr"]["value"] is None
    assert result["benchmark_return"]["value"] is None
    assert result["cumulative_active_return"]["value"] is None
    assert result["paired_intervals"] == 0
    assert result["statistics"]["annualized_tracking_error"]["value"] is None
