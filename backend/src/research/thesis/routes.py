"""Private thesis transport; all investment decisions are entered by the owner."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from src.research.database import get_session, require_research_access
from src.research.repository import ResearchConflict, ResearchNotFound
from src.research.thesis.repository import ThesisRepository
from src.research.thesis.schemas import (
    ReviewCreate,
    ReviewRead,
    RevisionCreate,
    RevisionRead,
    ThesisCreate,
    ThesisRead,
)

router = APIRouter(
    prefix="/api/research/theses", tags=["thesis"], dependencies=[Depends(require_research_access)]
)
PROMPTS = [
    "If you did not own this security today, would you buy it at the current price?",
    "Has the investment thesis changed, or has only the price changed?",
    "What evidence would invalidate the thesis?",
    "Is the expected return from today's price still sufficient?",
    "Is another available investment now a better use of capital?",
]


def get_repository(
    session: Annotated[Session, Depends(get_session, scope="function")],
) -> Iterator[ThesisRepository]:
    try:
        yield ThesisRepository(session)
    except ResearchNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ResearchConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


Repository = Annotated[ThesisRepository, Depends(get_repository, scope="function")]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/prompts", response_model=list[str])
def prompts() -> list[str]:
    return PROMPTS


@router.post("", response_model=ThesisRead, status_code=201)
def create_thesis(data: ThesisCreate, repository: Repository) -> ThesisRead:
    return repository.create_thesis(data)


@router.get("", response_model=list[ThesisRead])
def theses(
    repository: Repository, security_id: UUID | None = None, limit: Limit = 100, offset: Offset = 0
) -> list[ThesisRead]:
    return repository.theses(security_id, limit, offset)


@router.get("/{thesis_id}", response_model=ThesisRead)
def thesis(
    thesis_id: UUID, repository: Repository, as_of: Annotated[AwareDatetime | None, Query()] = None
) -> ThesisRead:
    return repository.get_thesis(thesis_id, as_of)


@router.post("/{thesis_id}/revisions", response_model=RevisionRead, status_code=201)
def append_revision(thesis_id: UUID, data: RevisionCreate, repository: Repository) -> RevisionRead:
    return repository.append_revision(thesis_id, data)


@router.get("/{thesis_id}/revisions", response_model=list[RevisionRead])
def revisions(
    thesis_id: UUID, repository: Repository, limit: Limit = 100, offset: Offset = 0
) -> list[RevisionRead]:
    return repository.revisions(thesis_id, limit, offset)


@router.post("/{thesis_id}/reviews", response_model=ReviewRead, status_code=201)
def create_review(thesis_id: UUID, data: ReviewCreate, repository: Repository) -> ReviewRead:
    return repository.create_review(thesis_id, data)


@router.get("/{thesis_id}/reviews", response_model=list[ReviewRead])
def reviews(
    thesis_id: UUID, repository: Repository, limit: Limit = 100, offset: Offset = 0
) -> list[ReviewRead]:
    return repository.reviews(thesis_id, limit, offset)
