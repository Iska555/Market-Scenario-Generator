"""Allowlist, analytical drawdown, original scope and safe anonymous preview tests."""

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.public_track_record import preview_routes
from src.public_track_record.snapshot import (
    PublicSnapshot,
    envelope,
    growth_and_drawdown,
    project_demo,
)

from tests.test_demo_launch import setup
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def test_analytical_growth_drawdown_gaps_zero_and_empty() -> None:
    result = growth_and_drawdown([Decimal(1), Decimal("1.2"), Decimal("0.9"), Decimal("1.1")])
    assert [r[0] for r in result] == [100, 120, 90, 110]
    assert result[2][1] == -0.25
    assert result[3][1] == pytest.approx(-1 / 12)
    assert growth_and_drawdown([Decimal(1), Decimal(0)]) == [(100, 0), (0, -1)]
    assert growth_and_drawdown([Decimal(1), None, Decimal(2)]) == [
        (100, 0),
        (None, None),
        (None, None),
    ]
    assert growth_and_drawdown([Decimal(0)]) == [(None, None)]
    assert growth_and_drawdown([Decimal(-1)]) == [(None, None)]
    assert growth_and_drawdown([]) == []


def test_original_projection_allows_only_sanitized_content_and_all_closed_losses(
    engine: Engine,
) -> None:
    portfolio, receipt = setup(engine)
    with Session(engine) as session, session.begin():
        snapshot = project_demo(LedgerRepository(session), portfolio.id)
        selected = project_demo(LedgerRepository(session), portfolio.id, ["harbor"])
    assert snapshot.nav == 10516 and snapshot.cash_value_base == 7876
    assert snapshot.holdings[0].value_base == 2640
    assert snapshot.holdings[0].risk_contribution.value is None
    assert snapshot.closed_positions[0].net_local_pnl == -400
    assert snapshot.closed_positions[0].linked_portfolio_return < 0
    assert selected.closed_positions == [
        snapshot.closed_positions[0].model_copy(update={"thesis_key": None})
    ]
    assert selected.twr == snapshot.twr and selected.series == snapshot.series
    assert selected.research[0].key == "harbor" and len(selected.research) == 1
    assert len(snapshot.research) == 2 and all(len(r.versions) == 2 for r in snapshot.research)
    assert all(r.actual_created_at.date() > r.example_date for r in snapshot.research)
    assert (
        snapshot.monthly[0].partial
        and not snapshot.monthly[1].partial
        and snapshot.monthly[2].partial
    )
    assert all(p.partial for p in snapshot.annual)
    assert len(snapshot.series) == 48 and snapshot.series[0].daily_return.value is None
    assert snapshot.series[-1].growth_index == pytest.approx(99.76059251874383)
    assert snapshot.series[-1].comparison_index == 102
    assert -min(
        p.drawdown_return for p in snapshot.series if p.drawdown_return is not None
    ) == pytest.approx(snapshot.max_drawdown.value)
    text = snapshot.model_dump_json()
    for private in [
        str(portfolio.id),
        *map(str, receipt.securities.values()),
        *map(str, receipt.transactions.values()),
    ]:
        assert private not in text
    for private in [
        "broker",
        "account_label",
        "external_reference",
        "reverses_id",
        "ledger_records",
        "known_at",
        "owner_key",
        "local_path",
    ]:
        assert f'"{private}":' not in text
    with pytest.raises(ValidationError):
        PublicSnapshot.model_validate(snapshot.model_dump() | {"owner_key": "secret-marker"})
    with pytest.raises(ValidationError):
        PublicSnapshot.model_validate(snapshot.model_dump() | {"mode": "real"})


def test_invalid_research_selection_and_unclassified_source_rejected(
    client: TestClient, engine: Engine
) -> None:
    from tests.test_accounting_api import account

    legacy = account(client)
    portfolio, _ = setup(engine)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        with pytest.raises(ValueError, match="demo identity"):
            project_demo(repo, UUID(legacy["id"]))
        for keys in (["private-thesis"], ["harbor", "harbor"]):
            with pytest.raises(ValueError, match="original"):
                project_demo(repo, portfolio.id, keys)


def test_safe_fixture_preview_has_no_database_proxy(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = "/api/public-preview/original"
    assert client.get(path, headers={"X-Research-Key": ""}).status_code == 404
    portfolio, _ = setup(engine)
    with Session(engine) as session, session.begin():
        snapshot = envelope(project_demo(LedgerRepository(session), portfolio.id))
    target = tmp_path / "preview.json"
    target.write_text(snapshot.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(preview_routes, "PREVIEW_FILE", target)
    monkeypatch.setenv("ENABLE_DEMO_PREVIEW", "1")
    response = client.get(path, headers={"X-Research-Key": ""})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.json()["published_at"] is None
    assert response.json()["status"] == "local_preview"
    downloaded = client.get(path + "/download", headers={"X-Research-Key": ""})
    assert downloaded.status_code == 200
    assert "attachment" in downloaded.headers["content-disposition"]
    assert downloaded.json() == response.json()
    assert (
        client.get(path + "/arbitrary-account", headers={"X-Research-Key": ""}).status_code == 404
    )
    assert client.post(path, json={"mode": "real"}).status_code == 405
    target.write_text(
        snapshot.model_copy(update={"content_sha256": "0" * 64}).model_dump_json(), encoding="utf-8"
    )
    assert client.get(path).status_code == 503
    target.write_text('{"owner_key":"secret-marker"}', encoding="utf-8")
    assert "secret-marker" not in client.get(path).text


def test_private_source_values_are_not_projected(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.public_track_record import snapshot as module

    original = module.demo_evidence
    portfolio, _ = setup(engine)

    def contaminated(repository: LedgerRepository, portfolio_id: UUID) -> dict:
        data = original(repository, portfolio_id)
        data["fixture"]["private_note"] = "PRIVATE_SECRET_MARKER"
        data["fixture"]["account_identifier"] = "PRIVATE_ACCOUNT_MARKER"
        data["fixture"]["local_path"] = "C:/PRIVATE_PATH_MARKER"
        return data

    monkeypatch.setenv("GIT_COMMIT_SHA", "PRIVATE_BUILD_MARKER")
    monkeypatch.setenv("BUILD_TIMESTAMP", "PRIVATE_TIMESTAMP_MARKER")
    monkeypatch.setattr(module, "demo_evidence", contaminated)
    with Session(engine) as session, session.begin():
        result = project_demo(LedgerRepository(session), portfolio.id).model_dump_json()
    assert "PRIVATE_" not in result
