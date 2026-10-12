"""Settings contracts, transaction boundaries and selection receipts, offline."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.benchmark.contracts import ComparisonReport, SettingCreate
from src.benchmark.replay import verify_comparison
from src.benchmark.settings import selection_hash
from src.factors.contracts import FactorReport, FactorRequest
from src.factors.replay import verify_factor_report

from tests.test_accounting_api import account, cash
from tests.test_benchmark_api import comparison_body
from tests.test_benchmark_engine import evidence
from tests.test_factors_api import factor_body
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def setting(**changes: Any) -> dict[str, Any]:
    return (
        dict(
            id=str(uuid4()),
            expected_revision=0,
            identity=evidence("100", "101").identity.model_dump(mode="json"),
            reason="Reviewed synthetic benchmark choice",
        )
        | changes
    )


def path(client: TestClient) -> tuple[str, str]:
    portfolio = account(client)["id"]
    assert (
        client.post(
            f"/api/accounting/portfolios/{portfolio}/transactions",
            json=dict(expected_version=0, transactions=[cash()]),
        ).status_code
        == 200
    )
    return portfolio, f"/api/benchmark/portfolios/{portfolio}/settings"


@pytest.mark.parametrize(
    "change",
    [
        dict(expected_revision=True),
        dict(expected_revision=-1),
        dict(reason=" "),
        dict(id="invalid"),
        dict(extra="private"),
    ],
)
def test_setting_contract_rejects_invalid_requests(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SettingCreate.model_validate(setting(**change))


def test_setting_append_retry_replace_clear_history_and_independent_ledger(
    client: TestClient,
) -> None:
    portfolio, url = path(client)
    empty = client.get(url).json()
    assert empty == dict(revision=0, total=0, latest=None, records=[])
    original = setting()
    response = client.post(url, json=original)
    assert response.status_code == 201, response.text
    first = response.json()
    assert first["revision"] == 1 and first["identity"] == original["identity"]
    assert client.post(url, json=original).json() == first
    assert client.post(url, json=original | dict(reason="Changed")).status_code == 409
    assert client.post(url, json=setting()).status_code == 409
    second = client.post(url, json=setting(expected_revision=1, reason="New review")).json()
    assert second["revision"] == 2 and second["recorded_at"] > first["recorded_at"]
    cleared = client.post(
        url, json=setting(expected_revision=2, identity=None, reason="Clear choice")
    )
    assert cleared.status_code == 201 and cleared.json()["identity"] is None
    assert client.post(url, json=original).json() == first
    history = client.get(url + "?limit=1&offset=1").json()
    assert history["revision"] == history["total"] == 3
    assert history["records"] == [second] and history["latest"]["identity"] is None
    assert client.get(f"/api/accounting/portfolios/{portfolio}/state").json()["version"] == 1
    for checked_response in (response, cleared, client.get(url), client.get(url + "?limit=0")):
        assert checked_response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "change",
    [
        dict(currency="USD"),
        dict(retrieved_at="2099-01-01T00:00:00Z"),
        dict(return_basis="price_return"),
        dict(calendar="trading_daily"),
    ],
)
def test_setting_invalid_identity_rolls_back(client: TestClient, change: dict[str, Any]) -> None:
    _, url = path(client)
    request = setting()
    request["identity"].update(change)
    response = client.post(url, json=request)
    assert response.status_code == 422, response.text
    assert response.headers["cache-control"] == "no-store"
    assert client.get(url).json()["revision"] == 0


def test_setting_private_not_found_cross_portfolio_id_and_sanitized_validation(
    client: TestClient,
) -> None:
    _, url = path(client)
    assert client.get(url, headers={"X-Research-Key": "wrong"}).status_code == 401
    assert client.get(f"/api/benchmark/portfolios/{uuid4()}/settings").status_code == 404
    request = setting()
    assert client.post(url, json=request).status_code == 201
    _, other = path(client)
    assert client.post(other, json=request).status_code == 409
    response = client.post(url, json=setting(expected_revision=True, reason="do-not-echo-private"))
    assert response.status_code == 422 and "do-not-echo-private" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_selected_receipt_replay_stale_clear_cutoff_mismatch_and_report_only(
    client: TestClient,
) -> None:
    portfolio, url = path(client)
    selected = client.post(url, json=setting()).json()
    body = comparison_body(saved_benchmark_revision=1)
    endpoint = f"/api/benchmark/portfolios/{portfolio}/comparison"
    response = client.post(endpoint, json=body)
    assert response.status_code == 200, response.text
    report = ComparisonReport.model_validate_json(response.content)
    assert report.selection is not None
    assert report.selection.content_sha256 == selection_hash(report.selection)
    verify_comparison(report)
    for field, value in (
        ("reason", "Tamper"),
        ("revision", 2),
        ("portfolio_id", uuid4()),
        ("recorded_at", datetime(2099, 1, 1, tzinfo=UTC)),
    ):
        tampered = report.model_copy(deep=True)
        setattr(tampered.selection, field, value)
        with pytest.raises(ValueError):
            verify_comparison(tampered)
    mismatch = comparison_body(saved_benchmark_revision=1)
    mismatch["benchmark"]["identity"]["name"] = "Different"
    assert client.post(endpoint, json=mismatch).status_code == 422
    earlier = comparison_body(saved_benchmark_revision=1)
    earlier["performance"]["known_at"] = "2025-02-01T00:00:00Z"
    assert client.post(endpoint, json=earlier).status_code == 422
    assert client.post(url, json=setting(expected_revision=1, identity=None)).status_code == 201
    assert client.post(endpoint, json=body).status_code == 409
    verify_comparison(report)  # offline receipt remains valid after later clear
    assert client.post(endpoint, json=comparison_body()).json()["selection"] is None
    assert client.get(url).json()["records"][-1] == selected


def test_factor_comparison_retains_saved_receipt_and_requires_evidence(client: TestClient) -> None:
    portfolio, url = path(client)
    benchmark = comparison_body()["benchmark"]
    assert client.post(url, json=setting()).status_code == 201
    data = factor_body(1) | dict(benchmark=benchmark, saved_benchmark_revision=1)
    data["performance"]["known_at"] = datetime.now(UTC).isoformat()
    response = client.post(f"/api/factors/portfolios/{portfolio}/report", json=data)
    assert response.status_code == 200, response.text
    result = FactorReport.model_validate_json(response.content)
    assert result.comparison is not None and result.comparison.selection is not None
    verify_factor_report(result)
    with pytest.raises(ValidationError, match="requires benchmark"):
        FactorRequest.model_validate(factor_body(1) | dict(saved_benchmark_revision=1))
