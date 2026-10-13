"""Native source reviews retain no payload or changes in the real database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from src.factors.source import SourceReview, verify_source_review

from tests.test_accounting_api import account
from tests.test_factor_source import body
from tests.test_performance_postgres import pg_client as pg_client
from tests.test_performance_postgres import snapshot
from tests.test_research_api import configured as configured
from tests.test_thesis_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def test_source_review_leaves_every_table_unchanged(
    pg_client: TestClient, postgres_engine: Engine
) -> None:
    portfolio = account(pg_client)
    before = snapshot(postgres_engine)
    path = f"/api/factors/portfolios/{portfolio['id']}/source-review"
    for _ in range(2):
        response = pg_client.post(path, json=body())
        assert response.status_code == 200, response.text
        assert response.headers["Cache-Control"] == "no-store"
        result = SourceReview.model_validate_json(response.content)
        assert result.account_currency == "GBP" and not result.regression_ready
        verify_source_review(result)
    assert pg_client.post(path, json=body() | dict(csv_text="bad format")).status_code == 422
    assert snapshot(postgres_engine) == before
