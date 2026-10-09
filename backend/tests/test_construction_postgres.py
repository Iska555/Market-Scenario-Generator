"""Construction evidence on migrated PostgreSQL is read-only and exact."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.portfolio.construction.contracts import ConstructionRequest
from src.portfolio.construction.service import evaluate_construction
from src.research.repository import ResearchRepository
from src.research.schemas import SecurityCreate
from src.research.thesis.repository import ThesisRepository
from src.research.thesis.schemas import ThesisCreate

from tests.test_construction_contracts import adopted_view, construction_payload
from tests.test_research_contracts import fact
from tests.test_thesis_backend import CONTENT, SECURITY
from tests.test_valuation_postgres import database_snapshot
from tests.test_valuation_postgres import postgres_engine as postgres_engine

pytestmark = pytest.mark.postgres


def test_construction_preserves_database_and_exact_evidence(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as session, session.begin():
        repo = ResearchRepository(session)
        securities = [
            repo.create_security(SecurityCreate.model_validate({**SECURITY, "ticker": ticker}))
            for ticker in ("AAA", "BBB")
        ]
        observation = repo.import_observations(securities[0].id, [fact(value="0.1234567890")])[0]
        thesis = ThesisRepository(session).create_thesis(
            ThesisCreate.model_validate({**CONTENT, "security_id": securities[0].id})
        )
    now = datetime.now(UTC) + timedelta(seconds=1)
    payload = construction_payload(valuation_date=now.date(), as_of=now, known_at=now)
    for asset, security in zip(payload["assets"], securities, strict=True):
        asset["security_id"] = security.id
        asset["investor_view"] = adopted_view(
            security.id, valuation_date=now.date(), as_of=now, known_at=now
        )
    payload["history"]["security_ids"] = [s.id for s in securities]
    payload["assets"][0]["investor_view"]["context"].update(
        observation_ids=[observation.id], thesis_revision_id=thesis.latest.id
    )
    request = ConstructionRequest.model_validate(payload)
    before = database_snapshot(postgres_engine)
    with Session(postgres_engine) as session, session.begin():
        response = evaluate_construction(session, request)
        assert str(response.manifest.evidence[0].observations[0].value) == "0.1234567890"
        assert response.manifest.evidence[0].thesis_revision is not None
        repeated = evaluate_construction(
            session, ConstructionRequest.model_validate(response.manifest.resolved_inputs)
        )
        assert response.result == repeated.result
    assert database_snapshot(postgres_engine) == before
