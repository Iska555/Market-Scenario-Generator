"""Publication lifecycle and HTTP allowlist; no market or owner account fixtures."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.public_track_record import publication
from src.public_track_record.publication import (
    ChannelRow,
    PreviewIntent,
    PublicWithdrawn,
    PublishIntent,
    WithdrawIntent,
    preview,
    public_history,
    publish,
    read_public,
    withdraw,
)
from src.research.repository import ResearchConflict, ResearchNotFound

from tests.test_demo_launch import setup
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine


def channel(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        if session.get(ChannelRow, "demo") is None:
            session.add(ChannelRow(id="demo"))


def prepare(engine: Engine, portfolio_id, selected=None):  # type: ignore[no-untyped-def]
    with Session(engine) as session, session.begin():
        return preview(
            LedgerRepository(session),
            PreviewIntent(
                id=uuid4(),
                portfolio_id=portfolio_id,
                selected_research=["harbor", "orchard"] if selected is None else selected,
            ),
        )


def test_immutable_versions_correction_withdrawal_and_republication(engine: Engine) -> None:
    channel(engine)
    portfolio, _ = setup(engine)
    first = prepare(engine, portfolio.id, ["harbor"])
    intent = PublishIntent(id=uuid4(), preview_id=first.id)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        original = publish(repo, intent)
        assert publish(repo, intent) == original
        assert read_public(repo) == original
        assert original.published_at is not None
        assert original.published_at > original.snapshot.snapshot_at
        assert original.snapshot.closed_positions[0].net_local_pnl == -400
        with pytest.raises(ResearchConflict):
            publish(repo, intent.model_copy(update={"preview_id": uuid4()}))
    second = prepare(engine, portfolio.id)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        with pytest.raises(ValueError, match="public reason"):
            publish(repo, PublishIntent(id=uuid4(), preview_id=second.id))
        correction = publish(
            repo,
            PublishIntent(
                id=uuid4(),
                preview_id=second.id,
                correction_of=intent.id,
                public_reason="Include the original closed-loser research review.",
            ),
        )
        assert len(correction.snapshot.research) == 2
        assert correction.snapshot.twr == original.snapshot.twr
        assert read_public(repo, intent.id) == original
        assert read_public(repo).correction_of == str(intent.id)
    withdrawal = WithdrawIntent(
        id=uuid4(), expected_sequence=2, public_reason="Synthetic withdrawal rehearsal."
    )
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        result = withdraw(repo, withdrawal)
        assert result["sequence"] == 3 and withdraw(repo, withdrawal) == result
        for version in (None, intent.id):
            with pytest.raises(PublicWithdrawn):
                read_public(repo, version)
        assert publish(repo, intent) == original  # Owner retry retains audit result.
        with pytest.raises(ResearchConflict):
            withdraw(repo, withdrawal.model_copy(update={"public_reason": "changed"}))
    third = prepare(engine, portfolio.id)
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        reopened = publish(
            repo,
            PublishIntent(
                id=uuid4(),
                preview_id=third.id,
                correction_of=UUID(correction.version),
                public_reason="Restore availability following rehearsal.",
            ),
        )
        assert read_public(repo) == reopened
        with pytest.raises(PublicWithdrawn):
            read_public(repo, intent.id)
        assert public_history(repo)["events"][0]["withdrawn"] is True


def test_preview_identity_missing_stale_history_and_source(engine: Engine) -> None:
    channel(engine)
    portfolio, _ = setup(engine)
    request = PreviewIntent(id=uuid4(), portfolio_id=portfolio.id, selected_research=[])
    with Session(engine) as session, session.begin():
        repo = LedgerRepository(session)
        saved = preview(repo, request)
        assert preview(repo, request) == saved
        with pytest.raises(ResearchConflict):
            preview(repo, request.model_copy(update={"selected_research": ["harbor"]}))
        with pytest.raises(ResearchNotFound):
            publish(repo, PublishIntent(id=uuid4(), preview_id=uuid4()))
        with pytest.raises(ResearchNotFound):
            read_public(repo)
    other = prepare(engine, portfolio.id)
    with Session(engine) as session, session.begin():
        publish(LedgerRepository(session), PublishIntent(id=uuid4(), preview_id=other.id))
    with Session(engine) as session, session.begin():
        with pytest.raises(ResearchConflict, match="history changed"):
            publish(LedgerRepository(session), PublishIntent(id=uuid4(), preview_id=saved.id))


def test_http_owner_boundary_anonymous_download_withdrawal_and_release_mode(
    engine: Engine, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    channel(engine)
    portfolio, _ = setup(engine)
    payload = dict(id=str(uuid4()), portfolio_id=str(portfolio.id), selected_research=["harbor"])
    assert (
        client.post(
            "/api/publication/previews", json=payload, headers={"X-Research-Key": "wrong"}
        ).status_code
        == 401
    )
    result = client.post("/api/publication/previews", json=payload)
    assert result.status_code == 200
    captured = result.json()
    assert client.get(f"/api/public/demo/versions/{captured['id']}").status_code == 404
    intent = dict(id=str(uuid4()), preview_id=captured["id"])
    published = client.post("/api/publication/publish", json=intent)
    assert published.status_code == 200
    version = published.json()["version"]
    client.headers.pop("X-Research-Key")
    response = client.get("/api/public/demo")
    assert response.json() == published.json() and response.headers["cache-control"] == "no-store"
    download = client.get(f"/api/public/demo/versions/{version}/download")
    assert download.json() == response.json()
    assert "attachment" in download.headers["content-disposition"]
    for forbidden in (
        '"portfolio_id"',
        '"security_id"',
        '"request"',
        '"preview_id"',
        str(portfolio.id),
    ):
        assert forbidden not in download.text
    for path in (
        "/api/publication/history",
        "/api/accounting/portfolios",
        "/api/research/securities",
    ):
        assert client.get(path).status_code == 401
    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")
    for path in ("/api/simulate", "/api/simulate-portfolio"):
        assert client.post(path, json={}).status_code == 401
        assert (
            client.post(
                path, json={}, headers={"X-Research-Key": "synthetic-owner-key-for-research-tests"}
            ).status_code
            == 422
        )
    assert client.get("/api/public/demo").status_code == 200
    monkeypatch.setenv("ENABLE_PRIVATE_SIMULATIONS", "0")
    assert (
        client.post(
            "/api/simulate",
            json={},
            headers={"X-Research-Key": "synthetic-owner-key-for-research-tests"},
        ).status_code
        == 503
    )
    assert client.get("/api/public/demo").status_code == 200
    assert client.get("/api/public/demo/history").json()["sequence"] == 1
    withdrawn = client.post(
        "/api/publication/withdraw",
        json={
            "id": str(uuid4()),
            "expected_sequence": 1,
            "public_reason": "Local synthetic rehearsal.",
        },
        headers={"X-Research-Key": "synthetic-owner-key-for-research-tests"},
    )
    assert withdrawn.status_code == 200
    for path in (
        "/api/public/demo",
        f"/api/public/demo/versions/{version}",
        f"/api/public/demo/versions/{version}/download",
    ):
        response = client.get(path)
        assert response.status_code == 410 and response.headers["cache-control"] == "no-store"
        assert "snapshot" not in response.text


def test_changed_calculation_and_separate_identity_cannot_publish(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    channel(engine)
    portfolio, _ = setup(engine)
    saved = prepare(engine, portfolio.id)
    original_project = publication.project_demo
    monkeypatch.setattr(
        publication,
        "project_demo",
        lambda *args: original_project(*args).model_copy(
            update={"calculation_source_sha256": "a" * 64}
        ),
    )
    with Session(engine) as session, session.begin():
        with pytest.raises(ResearchConflict, match="calculation code changed"):
            publish(LedgerRepository(session), PublishIntent(id=uuid4(), preview_id=saved.id))
    monkeypatch.setattr(publication, "project_demo", original_project)
    with Session(engine) as session, session.begin():
        original = publish(
            LedgerRepository(session), PublishIntent(id=uuid4(), preview_id=saved.id)
        )
    other, _ = setup(engine)
    other_preview = prepare(engine, other.id)
    with Session(engine) as session, session.begin():
        with pytest.raises(ResearchConflict, match="same isolated demo identity"):
            publish(
                LedgerRepository(session),
                PublishIntent(
                    id=uuid4(),
                    preview_id=other_preview.id,
                    correction_of=UUID(original.version),
                    public_reason="Separate history must not splice.",
                ),
            )
