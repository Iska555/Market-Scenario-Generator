"""Identity separation and old API compatibility using committed private requests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.accounting.tables import Portfolio
from src.public_track_record.contracts import DemoCreate, PortfolioIdentity
from src.public_track_record.tables import PortfolioIdentityRow

from tests.test_accounting_api import ROOT as LEGACY
from tests.test_accounting_api import account, cash
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine

ROOT = "/api/portfolio-identity/portfolios"


def demo_body() -> dict[str, str]:
    return dict(id=str(uuid4()), name="Fictional demonstration", base_currency="GBP", mode="demo")


@pytest.mark.parametrize("mode", ["demo", "paper", "real", "unclassified"])
def test_mode_meaning_and_private_defaults(mode: str) -> None:
    identity = PortfolioIdentity.model_validate(
        dict(
            mode=mode,
            recorded_at=None if mode == "unclassified" else datetime.now(UTC),
            publication_eligible=mode == "demo",
        )
    )
    assert identity.visibility == "private" and identity.broker_verified is False


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "fund"},
        {"publication_eligible": False},
        {"recorded_at": None},
        {"broker_verified": True},
        {"visibility": "public"},
        {"mode": "real"},
    ],
)
def test_inconsistent_identity_claims_rejected(changes: dict) -> None:
    with pytest.raises(ValidationError):
        PortfolioIdentity.model_validate(
            dict(mode="demo", recorded_at=datetime.now(UTC), publication_eligible=True) | changes
        )


def test_unclassified_identity_cannot_claim_recorded_mode() -> None:
    with pytest.raises(ValidationError):
        PortfolioIdentity.model_validate(
            dict(mode="unclassified", recorded_at=datetime.now(UTC), publication_eligible=False)
        )


def test_demo_creation_retry_and_legacy_contract_unchanged(client: TestClient) -> None:
    original = account(client)
    assert client.get(LEGACY).json() == [original]
    legacy = client.get(ROOT).json()[0]
    assert {k: v for k, v in legacy.items() if k != "identity"} == original
    assert legacy["identity"] == dict(
        mode="unclassified",
        recorded_at=None,
        publication_eligible=False,
        visibility="private",
        broker_verified=False,
    )
    body = demo_body()
    response = client.post(ROOT, json=body)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["identity"]["mode"] == "demo"
    assert created["identity"]["publication_eligible"] is True
    assert created["identity"]["visibility"] == "private"
    assert created["identity"]["recorded_at"] == created["created_at"]
    assert created["broker"] == "Synthetic demonstration"
    assert created["account_label"] == "No real money invested"
    assert client.post(ROOT, json=body).json() == created
    assert client.post(ROOT, json=body | {"name": "Changed"}).status_code == 409
    assert len(client.get(ROOT).json()) == 2
    assert all("identity" not in row for row in client.get(LEGACY).json())
    path = f"{LEGACY}/{created['id']}"
    assert (
        client.post(
            path + "/transactions", json=dict(expected_version=0, transactions=[cash()])
        ).status_code
        == 200
    )
    retry = client.post(ROOT, json=body).json()
    assert retry["version"] == 1 and retry["identity"] == created["identity"]
    assert client.get(f"{LEGACY}/{original['id']}/state").json()["cash"] == []


@pytest.mark.parametrize("funded", [False, True])
def test_legacy_even_empty_cannot_become_demo(client: TestClient, funded: bool) -> None:
    original = account(client)
    if funded:
        assert (
            client.post(
                f"{LEGACY}/{original['id']}/transactions",
                json=dict(expected_version=0, transactions=[cash()]),
            ).status_code
            == 200
        )
    body = demo_body() | {"id": original["id"]}
    response = client.post(ROOT, json=body)
    assert response.status_code == 409 and "relabelled" in response.text
    assert client.get(ROOT).json()[0]["identity"]["mode"] == "unclassified"


@pytest.mark.parametrize("mode", ["paper", "real", "unclassified", "unknown"])
def test_non_demo_creation_and_relabelling_rejected(client: TestClient, mode: str) -> None:
    body = demo_body()
    created = client.post(ROOT, json=body).json()
    assert client.post(ROOT, json=body | {"mode": mode}).status_code == 422
    assert client.post(ROOT, json=demo_body() | {"mode": mode}).status_code == 422
    assert client.put(ROOT + "/" + created["id"], json={"mode": mode}).status_code == 404
    assert len(client.get(ROOT).json()) == 1


def test_no_mode_injection_through_old_creation(client: TestClient) -> None:
    body = account(client)
    body = {k: v for k, v in body.items() if k not in ("created_at", "version")}
    assert client.post(LEGACY, json=body | {"mode": "real"}).status_code == 422
    assert client.post(ROOT, json=demo_body() | {"broker": "Lightyear"}).status_code == 422


def test_future_reserved_modes_never_imply_verification(client: TestClient, engine: Engine) -> None:
    # Deliberate DB-only fixture: no paper/real creation workflow is exposed.
    for mode in ("paper", "real"):
        original = account(client)
        with Session(engine) as session, session.begin():
            row = session.get(Portfolio, UUID(original["id"]))
            assert row is not None
            session.add(
                PortfolioIdentityRow(portfolio_id=row.id, mode=mode, recorded_at=row.created_at)
            )
        assert client.post(ROOT, json=demo_body() | {"id": original["id"]}).status_code == 409
    for row in client.get(ROOT).json():
        assert row["identity"]["publication_eligible"] is False
        assert row["identity"]["broker_verified"] is False


def test_owner_access_no_store_and_sanitized_errors(client: TestClient) -> None:
    for method in ("GET", "POST"):
        response = client.request(
            method,
            ROOT,
            headers={"X-Research-Key": "invalid"},
            json=demo_body() if method == "POST" else None,
        )
        assert response.status_code == 401 and response.headers["cache-control"] == "no-store"
    response = client.post(ROOT, json=demo_body() | {"private_note": "secret-marker"})
    assert response.status_code == 422 and "secret-marker" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert client.get(ROOT).headers["cache-control"] == "no-store"


def test_creation_contract_requires_explicit_demo_intent() -> None:
    body = demo_body()
    del body["mode"]
    with pytest.raises(ValidationError):
        DemoCreate.model_validate(body)
