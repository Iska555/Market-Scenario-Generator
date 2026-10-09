"""Private construction transport, adopted evidence and stateless replay."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_construction_contracts import adopted_view, construction_payload
from tests.test_thesis_backend import CONTENT, SECURITY
from tests.test_thesis_backend import client as client
from tests.test_thesis_backend import engine as engine

URL = "/api/research/construction/evaluate"


def request_for(client: TestClient) -> dict[str, Any]:
    securities = [
        client.post("/api/research/securities", json={**SECURITY, "ticker": ticker}).json()
        for ticker in ("AAA", "BBB")
    ]
    payload = construction_payload()
    for asset, security in zip(payload["assets"], securities, strict=True):
        asset["security_id"] = security["id"]
    payload["history"]["security_ids"] = [s["id"] for s in securities]
    return payload


def test_construction_private_risk_only_and_replay(client: TestClient) -> None:
    payload = request_for(client)
    assert client.post(URL, json=payload, headers={"X-Research-Key": "wrong"}).status_code == 401
    response = client.post(URL, json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert body["result"]["kind"] == "portfolio_construction"
    current = next(row for row in body["result"]["comparisons"] if row["strategy"] == "current")
    assert current["report"]["expected_portfolio_return"]["value"] is None
    assert [row["security"]["id"] for row in body["manifest"]["evidence"]] == payload["history"][
        "security_ids"
    ]
    repeated = client.post(URL, json=body["manifest"]["resolved_inputs"]).json()
    assert repeated["result"] == body["result"]
    assert repeated["manifest"]["input_sha256"] == body["manifest"]["input_sha256"]


def test_adopted_views_link_only_eligible_revisions(client: TestClient) -> None:
    payload = request_for(client)
    now = datetime.now(UTC) + timedelta(seconds=1)
    payload.update(
        valuation_date=now.date().isoformat(), as_of=now.isoformat(), known_at=now.isoformat()
    )
    identifier = payload["assets"][0]["security_id"]
    thesis = client.post("/api/research/theses", json={**CONTENT, "security_id": identifier}).json()
    for asset in payload["assets"]:
        asset["investor_view"] = adopted_view(
            asset["security_id"], valuation_date=now.date(), as_of=now, known_at=now
        )
    payload["assets"][0]["investor_view"]["context"]["thesis_revision_id"] = thesis["latest"]["id"]
    response = client.post(URL, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["manifest"]["evidence"][0]["adopted_view"]["kind"] == "investor_view"
    assert (
        response.json()["manifest"]["evidence"][0]["thesis_revision"]["id"]
        == thesis["latest"]["id"]
    )
    payload["assets"][0]["investor_view"]["context"]["thesis_revision_id"] = str(uuid4())
    assert client.post(URL, json=payload).status_code == 422


def test_construction_invalid_security_currency_and_domain(client: TestClient) -> None:
    payload = request_for(client)
    assert client.post(URL, json={**payload, "currency": "EUR"}).status_code == 422
    payload["assets"][0]["security_id"] = str(uuid4())
    payload["history"]["security_ids"][0] = payload["assets"][0]["security_id"]
    assert client.post(URL, json=payload).status_code == 404
    assert (
        client.post(URL, json={**payload, "constraints": {"cash_minimum": 0.1}}).status_code == 422
    )
