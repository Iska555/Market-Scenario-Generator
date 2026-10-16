"""Authenticated owner commands and separate allowlisted anonymous reads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.accounting.repository import LedgerRepository
from src.accounting.routes import Repository, private_response
from src.public_track_record.publication import (
    OwnerPreview,
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
from src.public_track_record.snapshot import SnapshotEnvelope
from src.research.database import get_session, require_research_access
from src.research.repository import ResearchConflict, ResearchNotFound

owner_router = APIRouter(
    prefix="/api/publication",
    tags=["owner-publication"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)
public_router = APIRouter(
    prefix="/api/public/demo", tags=["public-demo"], dependencies=[Depends(private_response)]
)
PublicSession = Annotated[Session, Depends(get_session, scope="function")]


@owner_router.post("/previews", response_model=OwnerPreview)
def create_preview(intent: PreviewIntent, repository: Repository) -> OwnerPreview:
    return preview(repository, intent)


@owner_router.post("/publish", response_model=SnapshotEnvelope)
def publish_version(intent: PublishIntent, repository: Repository) -> SnapshotEnvelope:
    return publish(repository, intent)


@owner_router.post("/withdraw")
def withdraw_version(intent: WithdrawIntent, repository: Repository) -> dict:
    return withdraw(repository, intent)


@owner_router.get("/history")
def owner_history(repository: Repository) -> dict:
    return public_history(repository)


def safe_read(session: Session, version: UUID | None = None) -> SnapshotEnvelope:
    try:
        return read_public(LedgerRepository(session), version)
    except ResearchNotFound as exc:
        raise HTTPException(404, "Published demonstration not found") from exc
    except PublicWithdrawn as exc:
        raise HTTPException(410, "Demonstration withdrawn from public availability") from exc
    except (ResearchConflict, ValueError) as exc:
        raise HTTPException(503, "Published demonstration is unavailable") from exc


@public_router.get("/history")
def history(session: PublicSession) -> dict:
    return public_history(LedgerRepository(session))


@public_router.get("", response_model=SnapshotEnvelope)
def latest(session: PublicSession) -> SnapshotEnvelope:
    return safe_read(session)


@public_router.get("/versions/{version}", response_model=SnapshotEnvelope)
def versioned(version: UUID, session: PublicSession) -> SnapshotEnvelope:
    return safe_read(session, version)


@public_router.get("/versions/{version}/download")
def download(version: UUID, session: PublicSession) -> JSONResponse:
    envelope = safe_read(session, version)
    return JSONResponse(
        content=envelope.model_dump(mode="json"),
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'attachment; filename="synthetic-demo-{version}.json"',
        },
    )
