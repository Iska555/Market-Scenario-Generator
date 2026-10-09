"""Offline contracts for immutable, owner-authored thesis history."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import StaticPool
from src.research import database
from src.research.tables import Base
from src.research.thesis import repository
from src.research.thesis.tables import ThesisRevision

KEY = "synthetic-owner-key-for-thesis-tests"
SECURITY = {
    "ticker": "aaa",
    "exchange": "xnas",
    "name": "Example",
    "currency": "USD",
    "country": "US",
}
CONTENT = {
    "status": "active",
    "horizon_months": 36,
    "conviction": "medium",
    "valuation_currency": "USD",
    "target_low": "80",
    "target_high": "120",
    "required_return": "0.08",
    "variant_perception": "Margins can recover",
    "business_quality": "Recurring sales",
    "earnings_drivers": "Renewals",
    "catalysts": "New contracts",
    "risks": "Competition",
    "bear_case": "Loss of renewals",
    "base_case": "Stable renewals",
    "bull_case": "Expanding renewals",
    "invalidation_conditions": "Renewal rate below 70%",
    "notes": "Owner judgment",
}
REVIEW = {
    "decision": "WATCH",
    "current_price": "95",
    "valuation_currency": "USD",
    "what_changed": "New filing",
    "what_was_correct": "Sales",
    "what_was_wrong": "Margins",
    "new_information": "Renewals",
    "thesis_still_valid": True,
    "updated_expected_return": "0.06",
    "notes": "Review judgment",
}


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False, "autocommit": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("RESEARCH_API_KEY", KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test@localhost/research")
    app.dependency_overrides[database.get_engine] = lambda: engine
    with TestClient(app, headers={"X-Research-Key": KEY}) as client:
        yield client
    app.dependency_overrides.clear()


def create_thesis(client: TestClient) -> dict:
    security = client.post("/api/research/securities", json=SECURITY).json()
    response = client.post("/api/research/theses", json={**CONTENT, "security_id": security["id"]})
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def test_history_is_immutable_as_of_and_retains_listing_labels(client: TestClient) -> None:
    thesis = create_thesis(client)
    first = thesis["latest"]
    url = f"/api/research/theses/{thesis['id']}"
    assert first["revision"] == 1 and first["ticker"] == "AAA"
    assert first["security_id"] == thesis["security_id"]
    client.put(
        f"/api/research/securities/{thesis['security_id']}", json={**SECURITY, "ticker": "NEW"}
    )
    second = client.post(
        url + "/revisions", json={**CONTENT, "expected_revision": 1, "notes": "Changed"}
    ).json()
    assert second["revision"] == 2 and second["ticker"] == "NEW"
    assert second["created_at"] > first["created_at"]
    assert client.get(url).json()["latest"] == second
    assert client.get(url, params={"as_of": first["created_at"]}).json()["latest"] == first
    early = datetime.fromisoformat(first["created_at"].replace("Z", "+00:00")) - timedelta(
        microseconds=1
    )
    assert client.get(url, params={"as_of": early.isoformat()}).status_code == 404
    assert client.get(url, params={"as_of": "2025-01-01"}).status_code == 422
    assert client.get(url + "/revisions").json() == [second, first]
    assert client.get(url + "/revisions", params={"limit": 1, "offset": 1}).json() == [first]
    assert (
        client.post(url + "/revisions", json={**CONTENT, "expected_revision": 1}).status_code == 409
    )
    assert client.get(url + "/revisions").json() == [second, first]
    assert (
        client.get("/api/research/theses", params={"security_id": thesis["security_id"]}).json()[0][
            "latest"
        ]
        == second
    )
    assert client.get("/api/research/theses", params={"security_id": str(uuid4())}).json() == []
    assert client.delete(url).status_code == 405


def test_review_records_manual_judgment_without_changing_status(client: TestClient) -> None:
    thesis = create_thesis(client)
    url = f"/api/research/theses/{thesis['id']}"
    before = datetime.now(UTC)
    response = client.post(url + "/reviews", json={**REVIEW, "revision_id": thesis["latest"]["id"]})
    assert response.status_code == 201, response.text
    review = response.json()
    assert datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00")) >= before
    assert review["revision_id"] == thesis["latest"]["id"]
    assert client.get(url + "/reviews").json() == [review]
    assert client.get(url).json() == thesis
    other = client.post(
        "/api/research/theses", json={**CONTENT, "security_id": thesis["security_id"]}
    ).json()
    assert (
        client.post(
            url + "/reviews", json={**REVIEW, "revision_id": other["latest"]["id"]}
        ).status_code
        == 422
    )
    assert (
        client.post(url + "/reviews", json={**REVIEW, "revision_id": str(uuid4())}).status_code
        == 422
    )
    assert (
        client.post(
            url + "/reviews",
            json={
                **REVIEW,
                "revision_id": thesis["latest"]["id"],
                "reviewed_at": "2020-01-01T00:00:00Z",
            },
        ).status_code
        == 422
    )
    assert client.get(url + "/reviews").json() == [review]


@pytest.mark.parametrize(
    "patch",
    [
        {"required_return": "-1"},
        {"required_return": "NaN"},
        {"target_low": "0"},
        {"target_low": "121"},
        {"target_high": None},
        {"horizon_months": 0},
        {"conviction": "certain"},
        {"status": "buy"},
        {"valuation_currency": "usd"},
        {"risks": " "},
        {"notes": "x" * 10001},
        {"created_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_invalid_thesis_is_rejected(client: TestClient, patch: dict) -> None:
    security = client.post("/api/research/securities", json=SECURITY).json()
    response = client.post(
        "/api/research/theses", json={**CONTENT, "security_id": security["id"], **patch}
    )
    assert response.status_code == 422
    assert client.get("/api/research/theses").json() == []


def test_draft_allows_partial_narratives_and_explicit_other_currency(client: TestClient) -> None:
    security = client.post("/api/research/securities", json=SECURITY).json()
    response = client.post(
        "/api/research/theses",
        json={
            "security_id": security["id"],
            "status": "draft",
            "horizon_months": 12,
            "conviction": "low",
            "valuation_currency": "EUR",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["latest"]["risks"] == ""


@pytest.mark.parametrize("suffix", ["", "/revisions", "/reviews"])
def test_missing_thesis_and_bounded_pagination(client: TestClient, suffix: str) -> None:
    assert client.get(f"/api/research/theses/{uuid4()}" + suffix).status_code == 404
    assert client.get("/api/research/theses", params={"limit": 101}).status_code == 422
    assert client.get("/api/research/theses", params={"offset": -1}).status_code == 422


def test_every_thesis_route_requires_key(client: TestClient) -> None:
    client.headers.pop("X-Research-Key")
    for method, path in [
        ("GET", ""),
        ("POST", ""),
        ("GET", "/prompts"),
        ("GET", "/{id}"),
        ("GET", "/{id}/revisions"),
        ("POST", "/{id}/revisions"),
        ("GET", "/{id}/reviews"),
        ("POST", "/{id}/reviews"),
    ]:
        assert (
            client.request(method, "/api/research/theses" + path.format(id=uuid4())).status_code
            == 401
        )


def test_unconfigured_and_unavailable_database_errors(
    client: TestClient,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Base.metadata.drop_all(engine)
    response = client.get("/api/research/theses")
    assert response.status_code == 503
    assert response.json() == {"detail": "Research database unavailable"}
    monkeypatch.delenv("RESEARCH_API_KEY")
    assert client.get("/api/research/theses/prompts").json() == {
        "detail": "Research API is not configured"
    }


def test_commit_failure_rolls_back_thesis_before_success(
    client: TestClient, engine: Engine
) -> None:
    security = client.post("/api/research/securities", json=SECURITY).json()

    def fail_commit(connection: object) -> None:
        raise SQLAlchemyError("password=synthetic-secret")

    event.listen(engine, "commit", fail_commit)
    try:
        response = client.post(
            "/api/research/theses", json={**CONTENT, "security_id": security["id"]}
        )
    finally:
        event.remove(engine, "commit", fail_commit)
    assert response.status_code == 503
    assert response.json() == {"detail": "Research database unavailable"}
    assert client.get("/api/research/theses").json() == []


def test_unique_constraint_fallback_is_a_conflict_and_preserves_history(client: TestClient) -> None:
    thesis = create_thesis(client)
    url = f"/api/research/theses/{thesis['id']}"

    def fail_insert(mapper: object, connection: object, target: object) -> None:
        raise IntegrityError("INSERT", None, Exception("Duplicate revision"))

    event.listen(ThesisRevision, "before_insert", fail_insert)
    try:
        response = client.post(url + "/revisions", json={**CONTENT, "expected_revision": 1})
    finally:
        event.remove(ThesisRevision, "before_insert", fail_insert)
    assert response.status_code == 409
    assert client.get(url).json() == thesis


def test_revisions_and_reviews_remain_monotonic_when_clock_moves_back(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thesis = create_thesis(client)
    url = f"/api/research/theses/{thesis['id']}"

    class EarlierClock(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "EarlierClock":
            return cls(2000, 1, 1, tzinfo=UTC)

    monkeypatch.setattr(repository, "datetime", EarlierClock)
    revision = client.post(url + "/revisions", json={**CONTENT, "expected_revision": 1}).json()
    assert revision["created_at"] > thesis["latest"]["created_at"]
    first = client.post(url + "/reviews", json={**REVIEW, "revision_id": revision["id"]}).json()
    second = client.post(
        url + "/reviews",
        json={**REVIEW, "revision_id": revision["id"], "valuation_currency": "EUR"},
    ).json()
    assert second["reviewed_at"] > first["reviewed_at"] >= revision["created_at"]
    assert second["valuation_currency"] == "EUR"
    assert client.get(url + "/reviews", params={"limit": 1, "offset": 1}).json() == [first]


@pytest.mark.parametrize(
    "patch",
    [
        {"decision": ""},
        {"current_price": "-1"},
        {"current_price": "Infinity"},
        {"updated_expected_return": "-1"},
        {"thesis_still_valid": "true"},
        {"valuation_currency": "usd"},
        {"new_information": "x" * 10001},
    ],
)
def test_invalid_reviews_are_not_recorded(client: TestClient, patch: dict) -> None:
    thesis = create_thesis(client)
    url = f"/api/research/theses/{thesis['id']}/reviews"
    response = client.post(url, json={**REVIEW, "revision_id": thesis["latest"]["id"], **patch})
    assert response.status_code == 422
    assert client.get(url).json() == []


def test_private_prompts_and_routes(client: TestClient) -> None:
    assert len(client.get("/api/research/theses/prompts").json()) == 5
    assert (
        client.get("/api/research/theses", headers={"X-Research-Key": "wrong"}).status_code == 401
    )
    assert (
        client.get("/api/research/theses/prompts", headers={"X-Research-Key": "wrong"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/research/theses", json={**CONTENT, "security_id": str(uuid4())}
        ).status_code
        == 404
    )
