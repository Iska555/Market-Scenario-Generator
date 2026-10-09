"""Ledger API uses real transaction boundaries and synthetic exact-decimal inputs."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine

ROOT = "/api/accounting/portfolios"


def account(client: TestClient) -> dict[str, Any]:
    response = client.post(
        ROOT,
        json={
            "id": str(uuid4()),
            "name": "Test ISA",
            "base_currency": "GBP",
            "broker": "Lightyear",
            "account_label": "Stocks & Shares ISA",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def cash(ref: str = "dep", **changes: object) -> dict[str, Any]:
    return (
        dict(
            type="DEPOSIT",
            effective_at="2025-01-01T12:00:00Z",
            currency="GBP",
            amount="1000",
            source="manual",
            external_reference=ref,
        )
        | changes
    )


def test_account_list_remains_accessible_after_101_creations(client: TestClient) -> None:
    ids = {account(client)["id"] for _ in range(101)}
    response = client.get(ROOT)
    assert response.status_code == 200, response.text
    assert {p["id"] for p in response.json()} == ids


def test_account_creation_idempotent_and_preview_is_read_only(client: TestClient) -> None:
    p = account(client)
    body = {k: v for k, v in p.items() if k not in ("created_at", "version")}
    assert client.post(ROOT, json=body).json() == p
    assert client.post(ROOT, json=body | {"name": "Different"}).status_code == 409
    path = f"{ROOT}/{p['id']}"
    batch = dict(expected_version=0, transactions=[cash()])
    preview = client.post(path + "/transactions/preview", json=batch)
    assert preview.status_code == 200, preview.text
    assert preview.json()["state"]["cash"][0]["amount"] == "1000"
    assert client.get(path + "/transactions").json()["total"] == 0
    saved = client.post(path + "/transactions", json=batch)
    assert saved.status_code == 200, saved.text
    retry = client.post(path + "/transactions", json=batch)
    assert retry.json()["inserted"] == 0
    assert retry.json()["duplicates"] == 1
    assert saved.json()["transactions"] == retry.json()["transactions"]
    assert retry.headers["cache-control"] == "no-store"
    assert client.get(path + "/state").json()["cash"][0]["amount"] == "1000"


def test_conflicts_and_failed_batch_leave_no_partial_rows(client: TestClient) -> None:
    p = account(client)
    path = f"{ROOT}/{p['id']}/transactions"
    response = client.post(
        path,
        json=dict(
            expected_version=0, transactions=[cash(), cash("out", type="WITHDRAWAL", amount="2000")]
        ),
    )
    assert response.status_code == 422, response.text
    assert client.get(path).json()["total"] == 0
    assert (
        client.post(path, json=dict(expected_version=0, transactions=[cash()])).status_code == 200
    )
    assert (
        client.post(path, json=dict(expected_version=0, transactions=[cash("new")])).status_code
        == 409
    )
    assert (
        client.post(
            path, json=dict(expected_version=1, transactions=[cash(amount="1")])
        ).status_code
        == 409
    )
    assert client.get(path).json()["total"] == 1


def test_correction_is_append_only_and_historical_knowledge_preserved(client: TestClient) -> None:
    p = account(client)
    path = f"{ROOT}/{p['id']}"
    original = client.post(
        path + "/transactions", json=dict(expected_version=0, transactions=[cash()])
    ).json()["transactions"][0]
    reversal = dict(
        type="REVERSAL",
        effective_at=original["effective_at"],
        currency="GBP",
        reverses_id=original["id"],
        source="manual",
        external_reference="correction",
    )
    result = client.post(
        path + "/transactions",
        json=dict(expected_version=1, transactions=[reversal, cash("replacement", amount="500")]),
    )
    assert result.status_code == 200, result.text
    assert result.json()["state"]["cash"][0]["amount"] == "500"
    history = client.get(path + "/transactions").json()
    assert history["total"] == 3
    old = client.get(path + "/state", params={"known_at": original["recorded_at"]})
    assert old.json()["cash"][0]["amount"] == "1000"
    assert (
        client.post(
            path + "/transactions",
            json=dict(
                expected_version=3, transactions=[reversal | {"external_reference": "again"}]
            ),
        ).status_code
        == 422
    )


def test_canonical_csv_is_all_or_nothing_and_exact(client: TestClient) -> None:
    p = account(client)
    path = f"{ROOT}/{p['id']}"
    body = dict(
        expected_version=0,
        source="lightyear_reviewed",
        csv_text="type,effective_at,currency,amount,external_reference\nDEPOSIT,2025-01-01T00:00:00Z,GBP,123.1234567890,one\n",
    )
    preview = client.post(path + "/imports/preview", json=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()["normalized_request"]["transactions"][0]["amount"] == "123.1234567890"
    assert client.get(path + "/transactions").json()["total"] == 0
    saved = client.post(path + "/transactions", json=preview.json()["normalized_request"])
    assert saved.json()["state"]["cash"][0]["amount"] == "123.1234567890"
    invalid = body | {
        "csv_text": str(body["csv_text"]) + "INTEREST,2025-01-02T00:00:00Z,GBP,1,two\n"
    }
    assert client.post(path + "/imports/preview", json=invalid).status_code == 422
    assert client.get(path + "/transactions").json()["total"] == 1


def test_private_unknown_portfolio_and_unknown_security(client: TestClient) -> None:
    assert client.get(ROOT, headers={"X-Research-Key": "wrong"}).status_code == 401
    assert client.get(f"{ROOT}/{uuid4()}/state").status_code == 404
    p = account(client)
    row = cash(type="BUY", security_id=str(uuid4()), quantity="1", price="1")
    del row["amount"]
    assert (
        client.post(
            f"{ROOT}/{p['id']}/transactions", json=dict(expected_version=0, transactions=[row])
        ).status_code
        == 404
    )


def test_trade_currency_and_backdate_validation(client: TestClient) -> None:
    from tests.test_research_api import SECURITY

    asset = client.post("/api/research/securities", json=SECURITY | {"currency": "GBP"}).json()
    p = account(client)
    path = f"{ROOT}/{p['id']}"
    buy = dict(
        type="BUY",
        effective_at="2025-01-02T12:00:00Z",
        currency="GBP",
        security_id=asset["id"],
        quantity="1",
        price="100",
        source="s",
        external_reference="b",
    )
    saved = client.post(
        path + "/transactions", json=dict(expected_version=0, transactions=[cash(), buy])
    )
    assert saved.status_code == 200
    wrong = client.post(
        path + "/transactions",
        json=dict(
            expected_version=2,
            transactions=[buy | {"currency": "USD", "external_reference": "bad"}],
        ),
    )
    assert wrong.status_code == 422
    backdate = client.post(
        path + "/transactions",
        json=dict(
            expected_version=2,
            transactions=[
                cash("earlier", effective_at="2024-12-31T00:00:00Z", type="WITHDRAWAL", amount="1")
            ],
        ),
    )
    assert backdate.status_code == 422
    canceled_deposit = saved.json()["transactions"][0]
    reversed_funding = dict(
        type="REVERSAL",
        effective_at=canceled_deposit["effective_at"],
        currency="GBP",
        reverses_id=canceled_deposit["id"],
        source="s",
        external_reference="undo",
    )
    assert (
        client.post(
            path + "/transactions", json=dict(expected_version=2, transactions=[reversed_funding])
        ).status_code
        == 422
    )
    assert client.get(path + "/transactions").json()["total"] == 2
    valued = client.post(
        path + "/valuation",
        json=dict(
            as_of="2025-01-03T00:00:00Z",
            prices=[
                dict(
                    security_id=asset["id"],
                    currency="GBP",
                    price="120",
                    observed_at="2025-01-03T00:00:00Z",
                    source="synthetic",
                )
            ],
        ),
    )
    assert valued.status_code == 200, valued.text
    assert valued.json()["nav"] == "1020"


@pytest.mark.parametrize("field", ["as_of", "known_at"])
def test_future_cutoffs_rejected(client: TestClient, field: str) -> None:
    p = account(client)
    assert (
        client.get(f"{ROOT}/{p['id']}/state", params={field: "2999-01-01T00:00:00Z"}).status_code
        == 422
    )


def test_idempotency_canonicalizes_decimals_and_timezone(client: TestClient) -> None:
    p = account(client)
    path = f"{ROOT}/{p['id']}/transactions"
    batch = dict(expected_version=0, transactions=[cash()])
    saved = client.post(path, json=batch).json()
    retry = client.post(
        path,
        json=dict(
            expected_version=0,
            transactions=[cash(amount="1000.0000000000", effective_at="2025-01-01T16:00:00+04:00")],
        ),
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["transactions"] == saved["transactions"]
    assert retry.json()["inserted"] == 0


@pytest.mark.parametrize(
    "text",
    [
        "type,type,effective_at,currency,external_reference\n",
        "garbage\n",
        "type,effective_at,currency,external_reference\nDEPOSIT,2025-01-01T00:00:00Z,GBP\n",
        "type,effective_at,currency,external_reference\nDEPOSIT,2025-01-01T00:00:00Z,GBP,one,extra\n",
        'type,effective_at,currency,external_reference\n"unclosed',
    ],
)
def test_malformed_csv_cannot_write_or_echo_input(client: TestClient, text: str) -> None:
    p = account(client)
    path = f"{ROOT}/{p['id']}"
    response = client.post(
        path + "/imports/preview", json=dict(expected_version=0, source="test", csv_text=text)
    )
    assert response.status_code == 422
    assert client.get(path + "/transactions").json()["total"] == 0
