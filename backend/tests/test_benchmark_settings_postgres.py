"""Migrated immutable settings and real competing transactions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.benchmark import routes
from src.benchmark.contracts import ComparisonReport, SettingCreate
from src.benchmark.replay import verify_comparison
from src.benchmark.settings import append
from src.research.repository import ResearchConflict

from tests.test_benchmark_api import comparison_body
from tests.test_benchmark_settings import path, setting
from tests.test_performance_postgres import pg_client as pg_client
from tests.test_performance_postgres import snapshot
from tests.test_research_api import configured as configured
from tests.test_research_migrations import migration_config
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def test_pg_settings_append_only_persisted_clear_history_and_no_ledger_writes(
    pg_client: TestClient,
    postgres_engine: Engine,
) -> None:
    _, url = path(pg_client)
    before = snapshot(postgres_engine)
    request = setting()
    saved = pg_client.post(url, json=request)
    assert saved.status_code == 201
    assert pg_client.post(url, json=request).json() == saved.json()
    assert pg_client.post(url, json=setting(expected_revision=1, identity=None)).status_code == 201
    after = snapshot(postgres_engine)
    assert len(after["portfolio_benchmark_settings"]) == 2
    assert {
        key: value for key, value in before.items() if key != "portfolio_benchmark_settings"
    } == {key: value for key, value in after.items() if key != "portfolio_benchmark_settings"}
    for sql in (
        "UPDATE portfolio_benchmark_settings SET reason='modified'",
        "DELETE FROM portfolio_benchmark_settings",
    ):
        with postgres_engine.connect() as connection:
            with pytest.raises(DBAPIError, match="append-only"):
                connection.execute(text(sql))
            connection.rollback()
    assert pg_client.get(url).json()["records"][-1] == saved.json()


def test_pg_competing_setting_writers_one_revision_wins(
    pg_client: TestClient,
    postgres_engine: Engine,
) -> None:
    portfolio, url = path(pg_client)
    barrier = Barrier(2)

    def write(reason: str) -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            try:
                with session.begin():
                    result = append(
                        LedgerRepository(session),
                        UUID(portfolio),
                        SettingCreate.model_validate(setting(reason=reason)),
                    )
                    assert result.revision == 1
                return "saved"
            except ResearchConflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(write, ("Review A", "Review B")))
    assert sorted(results) == ["conflict", "saved"]
    assert pg_client.get(url).json()["total"] == 1


def test_pg_report_retains_lock_selection_no_table_writes_and_stale_rejection(
    pg_client: TestClient,
    postgres_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio, url = path(pg_client)
    assert pg_client.post(url, json=setting()).status_code == 201
    original = routes.build_comparison
    checked = []

    def locked(*args: object, **kwargs: object) -> ComparisonReport:
        with Session(postgres_engine) as other, other.begin():
            other.execute(text("SET LOCAL lock_timeout='250ms'"))
            with pytest.raises(OperationalError) as failure:
                LedgerRepository(other).portfolio(UUID(portfolio))
            assert getattr(failure.value.orig, "sqlstate", None) == "55P03"
            checked.append(True)
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(routes, "build_comparison", locked)
    before = snapshot(postgres_engine)
    endpoint = f"/api/benchmark/portfolios/{portfolio}/comparison"
    body = comparison_body(saved_benchmark_revision=1)
    response = pg_client.post(endpoint, json=body)
    assert response.status_code == 200, response.text
    result = ComparisonReport.model_validate_json(response.content)
    verify_comparison(result)
    assert checked == [True] and snapshot(postgres_engine) == before
    assert pg_client.post(url, json=setting(expected_revision=1, identity=None)).status_code == 201
    assert pg_client.post(endpoint, json=body).status_code == 409
    verify_comparison(result)


def test_pg_settings_migration_up_down_preserves_existing_ledger(
    pg_client: TestClient,
    postgres_engine: Engine,
) -> None:
    path(pg_client)
    before = snapshot(postgres_engine)
    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "20260912_03")
        assert "portfolio_benchmark_settings" not in inspect(connection).get_table_names()
        command.upgrade(config, "head")
    after = snapshot(postgres_engine)
    assert before == after
