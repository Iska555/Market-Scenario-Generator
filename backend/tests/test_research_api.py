"""Private research API behavior with synthetic, offline persistence."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from src.research import database
from src.research.tables import Base

KEY = "synthetic-owner-key-for-research-tests"
URL = "postgresql+psycopg://test:synthetic-secret@localhost/research"
SECURITY = {
    "ticker": "aaa",
    "exchange": "xnas",
    "name": "Example",
    "currency": "USD",
    "country": "US",
}
FACT = {
    "metric": "net_margin",
    "value": "0.125",
    "unit": "fraction",
    "period_kind": "annual",
    "period_start": "2024-01-01",
    "period_end": "2024-12-31",
    "reported_at": "2025-02-01T12:00:00Z",
    "fetched_at": "2025-02-02T00:00:00Z",
    "source": "synthetic",
    "source_record_id": "filing-1",
    "source_document": "fixture",
    "basis": "GAAP",
}


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_API_KEY", KEY)
    monkeypatch.setenv("DATABASE_URL", URL)


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
def client(configured: None, engine: Engine) -> Iterator[TestClient]:
    # Override only engine acquisition so real session commit/rollback is exercised.
    app.dependency_overrides[database.get_engine] = lambda: engine
    with TestClient(app, headers={"X-Research-Key": KEY}) as client:
        yield client
    app.dependency_overrides.clear()


def test_research_is_disabled_without_owner_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCH_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/research/metrics")
    assert response.status_code == 503
    assert response.json() == {"detail": "Research API is not configured"}


@pytest.mark.parametrize("key", [None, "too-short", " " * 32])
def test_missing_or_weak_key_disables_research(
    configured: None, monkeypatch: pytest.MonkeyPatch, key: str | None
) -> None:
    if key is None:
        monkeypatch.delenv("RESEARCH_API_KEY")
    else:
        monkeypatch.setenv("RESEARCH_API_KEY", key)
    assert TestClient(app).get("/api/research/metrics").status_code == 503


@pytest.mark.parametrize("url", ["", "sqlite://", "postgresql://test@localhost/test", "garbage"])
def test_non_psycopg_configuration_is_disabled(
    configured: None, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", url)
    response = TestClient(app).get("/api/research/metrics", headers={"X-Research-Key": KEY})
    assert response.status_code == 503
    assert "synthetic-secret" not in response.text


@pytest.mark.parametrize("key", ["", "wrong", "é" * 32])
def test_private_catalogue_rejects_missing_and_wrong_keys(configured: None, key: str) -> None:
    headers = {"X-Research-Key": key} if key else {}
    # Header transport is ASCII; byte input exercises non-ASCII comparison safely.
    response = TestClient(app).get(
        "/api/research/metrics",
        headers={name.encode(): value.encode() for name, value in headers.items()},
    )
    assert response.status_code == 401


def test_catalogue_is_typed_and_does_not_require_database_connection(configured: None) -> None:
    response = TestClient(app).get("/api/research/metrics", headers={"X-Research-Key": KEY})
    assert response.status_code == 200
    assert {
        "key": "pe",
        "label": "P/E",
        "category": "valuation",
        "unit": "ratio",
    } in response.json()
    assert "/api/research/securities/{security_id}/fundamentals" in app.openapi()["paths"]


def test_security_create_read_rename_and_pagination(client: TestClient) -> None:
    response = client.post("/api/research/securities", json=SECURITY)
    assert response.status_code == 201
    asset = response.json()
    url = f"/api/research/securities/{asset['id']}"
    assert asset["ticker"] == "AAA"
    assert client.get(url).json() == asset
    changed = client.put(url, json={**SECURITY, "ticker": "NEW"}).json()
    assert changed["id"] == asset["id"]
    assert changed["created_at"] == asset["created_at"]
    assert client.get(url).json()["ticker"] == "NEW"
    assert client.get("/api/research/securities", params={"limit": 1}).json() == [changed]
    assert client.get("/api/research/securities", params={"offset": 1}).json() == []


def test_import_is_idempotent_and_as_of_does_not_leak_restatement(client: TestClient) -> None:
    asset = client.post("/api/research/securities", json=SECURITY).json()
    url = f"/api/research/securities/{asset['id']}/fundamentals"
    saved = client.post(url, json={"observations": [FACT]}).json()[0]
    repeated = client.post(url, json={"observations": [FACT]}).json()[0]
    assert repeated["id"] == saved["id"]
    assert repeated["fetched_at"] == saved["fetched_at"]
    assert Decimal(repeated["value"]) == Decimal(saved["value"])
    revised = {
        **FACT,
        "source_record_id": "revision-2",
        "value": "0.25",
        "reported_at": "2025-04-01T00:00:00Z",
        "fetched_at": "2025-04-02T00:00:00Z",
    }
    assert client.post(url, json={"observations": [revised]}).status_code == 201
    early = client.get(url, params={"as_of": "2025-03-01T00:00:00Z"}).json()
    assert [row["id"] for row in early["items"]] == [saved["id"]]
    assert datetime.fromisoformat(early["known_at"].replace("Z", "+00:00")) <= datetime.now(UTC)
    assert early["limit"] == 100 and early["offset"] == 0
    later = client.get(url, params={"as_of": "2025-05-01T00:00:00Z"}).json()
    assert float(later["items"][0]["value"]) == 0.25
    historical = client.get(
        url, params={"as_of": "2025-03-01T00:00:00Z", "known_at": "2025-03-01T00:00:00Z"}
    ).json()
    assert historical["items"] == []
    assert (
        client.get(url, params={"as_of": "2025-05-01T00:00:00Z", "source": "other"}).json()["items"]
        == []
    )
    assert (
        client.get(url, params={"as_of": "2025-05-01T00:00:00Z", "offset": 1}).json()["items"] == []
    )


def test_missing_conflicting_and_invalid_data_are_client_errors(client: TestClient) -> None:
    missing = f"/api/research/securities/{uuid4()}"
    assert client.get(missing).status_code == 404
    assert client.put(missing, json=SECURITY).status_code == 404
    assert client.post(missing + "/fundamentals", json={"observations": [FACT]}).status_code == 404
    asset = client.post("/api/research/securities", json=SECURITY).json()
    assert client.post("/api/research/securities", json=SECURITY).status_code == 409
    url = f"/api/research/securities/{asset['id']}/fundamentals"
    assert client.post(url, json={"observations": []}).status_code == 422
    assert (
        client.post(url, json={"observations": [{**FACT, "reported_at": "2025-02-01"}]}).status_code
        == 422
    )
    assert (
        client.post(
            url, json={"observations": [{**FACT, "fetched_at": "2100-01-01T00:00:00Z"}]}
        ).status_code
        == 422
    )
    assert client.post(url, json={"observations": [FACT]}).status_code == 201
    assert client.post(url, json={"observations": [{**FACT, "value": "0.5"}]}).status_code == 409
    assert len(client.get(url, params={"as_of": "2025-03-01T00:00:00Z"}).json()["items"]) == 1


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"as_of": "2025-03-01"},
        {"as_of": "2025-03-01T00:00:00Z", "known_at": "2025-03-01"},
        {"as_of": "2025-03-01T00:00:00Z", "limit": 501},
        {"as_of": "2025-03-01T00:00:00Z", "offset": -1},
        {"as_of": "2025-03-01T00:00:00Z", "source": "x" * 201},
    ],
)
def test_observation_query_bounds_and_aware_cutoffs(
    client: TestClient, query: dict[str, str | int]
) -> None:
    response = client.get(f"/api/research/securities/{uuid4()}/fundamentals", params=query)
    assert response.status_code == 422


@pytest.mark.parametrize("query", [{"limit": 0}, {"limit": 501}, {"offset": -1}])
def test_security_pagination_bounds(client: TestClient, query: dict[str, int]) -> None:
    assert client.get("/api/research/securities", params=query).status_code == 422


def test_database_failure_is_sanitized(client: TestClient, engine: Engine) -> None:
    Base.metadata.drop_all(engine)
    response = client.get("/api/research/securities")
    assert response.status_code == 503
    assert response.json() == {"detail": "Research database unavailable"}


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/securities"),
        ("POST", "/securities"),
        ("GET", "/securities/{id}"),
        ("PUT", "/securities/{id}"),
        ("GET", "/securities/{id}/fundamentals"),
        ("POST", "/securities/{id}/fundamentals"),
    ],
)
def test_every_research_operation_requires_owner_key(
    configured: None, method: str, path: str
) -> None:
    response = TestClient(app).request(method, "/api/research" + path.format(id=uuid4()))
    assert response.status_code == 401


def test_commit_failure_returns_503_before_response(client: TestClient, engine: Engine) -> None:
    def fail_commit(connection: object) -> None:
        raise SQLAlchemyError("SELECT private-data; password=synthetic-secret")

    event.listen(engine, "commit", fail_commit)
    try:
        response = client.post("/api/research/securities", json=SECURITY)
    finally:
        event.remove(engine, "commit", fail_commit)
    assert response.status_code == 503
    assert response.json() == {"detail": "Research database unavailable"}
    assert client.get("/api/research/securities").json() == []


def test_conflicting_batch_rolls_back_new_fact(client: TestClient) -> None:
    asset = client.post("/api/research/securities", json=SECURITY).json()
    url = f"/api/research/securities/{asset['id']}/fundamentals"
    assert client.post(url, json={"observations": [FACT]}).status_code == 201
    batch = [{**FACT, "source": "other"}, {**FACT, "value": "0.5"}]
    assert client.post(url, json={"observations": batch}).status_code == 409
    assert (
        client.get(url, params={"as_of": "2025-03-01T00:00:00Z", "source": "other"}).json()["items"]
        == []
    )


def test_lazy_engine_creation_is_cached_without_connecting(configured: None) -> None:
    engine = database.build_engine(URL)
    assert engine is database.build_engine(URL)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    assert database.get_engine() is engine
    engine.dispose()
    database.build_engine.cache_clear()


def test_engine_configuration_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    with pytest.raises(HTTPException) as raised:
        database.get_engine()
    assert raised.value.status_code == 503
    assert raised.value.detail == "Research database unavailable"
