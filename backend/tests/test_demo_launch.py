"""Original demo acceptance with independent economic checks and failure coverage."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.accounting.contracts import Batch
from src.accounting.repository import LedgerRepository
from src.accounting.tables import Portfolio, Transaction
from src.attribution.engine import build_contribution
from src.attribution.replay import verify_contribution
from src.benchmark.contracts import BenchmarkEvidence
from src.benchmark.engine import build_comparison
from src.benchmark.replay import verify_comparison
from src.performance.contracts import PerformanceRequest
from src.performance.engine import build_report
from src.performance.replay import verify_replay
from src.public_track_record.contracts import DemoCreate
from src.public_track_record.demo import (
    checked_receipt,
    demo_evidence,
    fixture,
    interpolate,
    load_demo,
)
from src.public_track_record.repository import create_demo
from src.research.repository import ResearchConflict
from src.research.tables import Security
from src.research.thesis.tables import Thesis, ThesisReview, ThesisRevision

from tests.test_accounting_api import account, cash
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def setup(engine: Engine):  # type: ignore[no-untyped-def]
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        portfolio = create_demo(
            repo,
            DemoCreate(
                id=uuid4(), name="Synthetic original demo", base_currency="GBP", mode="demo"
            ),
        )
        receipt = load_demo(repo, portfolio.id)
    return portfolio, receipt


def counts(engine: Engine) -> list[int | None]:
    with Session(engine) as session:
        return [
            session.scalar(select(func.count()).select_from(table))
            for table in (Portfolio, Security, Transaction, Thesis, ThesisRevision, ThesisReview)
        ]


def test_fixture_load_idempotent_cash_positions_dates_and_closed_loser(engine: Engine) -> None:
    portfolio, receipt = setup(engine)
    before = counts(engine)
    assert before == [1, 2, 13, 2, 4, 2]
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        assert load_demo(repo, portfolio.id) == receipt
        state = repo.state(portfolio.id)
        assert {c.currency: c.amount for c in state.cash} == {
            "GBP": Decimal("6154"),
            "USD": Decimal("2100"),
        }
        assert len(state.positions) == 1
        assert state.positions[0].security_id == receipt.securities["harbor"]
        assert state.positions[0].quantity == 40 and state.positions[0].cost_basis == 2404
        rows = repo.rows(portfolio.id)
        orchard = [r for r in rows if r.security_id == receipt.securities["orchard"]]
        assert orchard[0].quantity is not None and orchard[0].price is not None
        assert orchard[1].amount is not None
        assert orchard[2].quantity is not None and orchard[2].price is not None
        # Independently: -20*100-5 + 10 + 20*80-5 = -400 USD.
        assert -orchard[0].quantity * orchard[0].price - orchard[0].fees + orchard[
            1
        ].amount + orchard[2].quantity * orchard[2].price - orchard[2].fees == Decimal("-400")
        assert all(r.recorded_at.date() > r.effective_at.date() for r in rows)
        evidence = demo_evidence(repo, portfolio.id)
        assert evidence["performance"]["known_at"] == receipt.loaded_at.isoformat().replace(
            "+00:00", "Z"
        )
        assert evidence == demo_evidence(repo, portfolio.id)
    assert counts(engine) == before


def test_complete_demo_reports_reconcile_and_replay(engine: Engine) -> None:
    portfolio, receipt = setup(engine)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        evidence = demo_evidence(repo, portfolio.id)
        request = PerformanceRequest.model_validate(evidence["performance"])
        report = build_report(portfolio.id, "GBP", repo.rows(portfolio.id), request)
        contribution = build_contribution(report)
        comparison = build_comparison(
            report, BenchmarkEvidence.model_validate(evidence["benchmark"]), contribution
        )
    assert report.daily[0].nav == 10000 and report.daily[-1].nav == 10516
    assert report.daily[1].nav == Decimal("9985.88125")
    assert report.daily[1].daily_return.value == pytest.approx(-0.001411875)
    assert len(report.daily) == 48 and len(report.external_flows) == 2
    drawdown = report.statistics["max_drawdown"].value
    assert drawdown is not None and drawdown > 0
    assert report.statistics["annualized_return"].value is None
    assert contribution.reconciliation.within_tolerance is True
    residual = contribution.reconciliation.residual.value
    assert residual is not None and abs(residual) <= Decimal("1e-12")
    assert any(
        c.security_id == receipt.securities["orchard"]
        and c.total.value is not None
        and c.total.value < 0
        for c in contribution.components
    )
    verify_replay(report)
    verify_contribution(contribution)
    verify_comparison(comparison)


@pytest.mark.parametrize("damage", ["missing_price", "invalid_fx", "incomplete_benchmark"])
def test_fixture_negative_coverage_stays_visible(engine: Engine, damage: str) -> None:
    portfolio, _ = setup(engine)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        evidence = demo_evidence(repo, portfolio.id)
        if damage == "missing_price":
            evidence["performance"]["daily_marks"][5]["prices"] = []
        elif damage == "invalid_fx":
            evidence["performance"]["daily_marks"][5]["fx"][0]["rate"] = "0"
            with pytest.raises(ValueError):
                PerformanceRequest.model_validate(evidence["performance"])
            return
        else:
            evidence["benchmark"]["levels"].pop(5)
        report = build_report(
            portfolio.id,
            "GBP",
            repo.rows(portfolio.id),
            PerformanceRequest.model_validate(evidence["performance"]),
        )
        if damage == "missing_price":
            assert report.twr.value is None and report.daily[5].reason is not None
        else:
            comparison = build_comparison(
                report, BenchmarkEvidence.model_validate(evidence["benchmark"])
            )
            assert comparison.benchmark_return.value is None
            assert comparison.statistics["beta"].value is None


def test_loader_refuses_legacy_non_gbp_demo_and_existing_history(
    client: TestClient, engine: Engine
) -> None:
    legacy = account(client)
    path = "/api/portfolio-identity/portfolios"
    assert client.post(f"{path}/{legacy['id']}/demo/load").status_code == 422
    data = dict(id=str(uuid4()), name="Demo", base_currency="USD", mode="demo")
    foreign = client.post(path, json=data).json()
    assert client.post(f"{path}/{foreign['id']}/demo/load").status_code == 422
    created = client.post(path, json=data | {"id": str(uuid4()), "base_currency": "GBP"}).json()
    ledger_path = f"/api/accounting/portfolios/{created['id']}/transactions"
    assert (
        client.post(ledger_path, json=dict(expected_version=0, transactions=[cash()])).status_code
        == 200
    )
    before = counts(engine)
    assert client.post(f"{path}/{created['id']}/demo/load").status_code == 409
    assert counts(engine) == before


def test_changed_demo_history_invalidates_fixture_receipt(engine: Engine) -> None:
    portfolio, _ = setup(engine)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        repo.evaluate(
            portfolio.id,
            Batch.model_validate(dict(expected_version=13, transactions=[cash("new", amount="1")])),
            save=True,
        )
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        with pytest.raises(ResearchConflict, match="ledger changed"):
            load_demo(repo, portfolio.id)
        with pytest.raises(ResearchConflict):
            checked_receipt(repo, portfolio.id)


def test_demo_owner_api_empty_evidence_loader_and_privacy(client: TestClient) -> None:
    path = "/api/portfolio-identity/portfolios"
    created = client.post(
        path, json=dict(id=str(uuid4()), name="Synthetic", base_currency="GBP", mode="demo")
    ).json()
    root = f"{path}/{created['id']}/demo"
    assert client.get(root + "/evidence").status_code == 422
    assert client.post(root + "/load", headers={"X-Research-Key": "wrong"}).status_code == 401
    response = client.post(root + "/load")
    assert response.status_code == 200, response.text
    assert client.post(root + "/load").json() == response.json()
    evidence = client.get(root + "/evidence")
    assert evidence.status_code == 200 and evidence.headers["cache-control"] == "no-store"
    assert evidence.json()["mode"] == "demo"


def test_anchor_generation_bounds_and_endpoints() -> None:
    points = fixture()["fx_points"]
    assert interpolate(points, date(2025, 12, 20)) == Decimal("0.8")
    assert interpolate(points, date(2026, 2, 5)) == Decimal("0.82")
    with pytest.raises(ValueError, match="coverage"):
        interpolate(points, date(2026, 2, 6))
