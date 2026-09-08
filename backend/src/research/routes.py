"""Typed research transport, with no financial calculations."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from src.research.database import get_session, require_research_access
from src.research.metrics import METRICS, MetricDefinition
from src.research.repository import ResearchConflict, ResearchNotFound, ResearchRepository
from src.research.schemas import (
    ObservationBatch,
    ObservationPage,
    ObservationRead,
    SecurityCreate,
    SecurityRead,
)

router = APIRouter(
    prefix="/api/research", tags=["research"], dependencies=[Depends(require_research_access)]
)


def get_repository(
    session: Annotated[Session, Depends(get_session, scope="function")],
) -> Iterator[ResearchRepository]:
    try:
        yield ResearchRepository(session)
    except ResearchNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ResearchConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


Repository = Annotated[ResearchRepository, Depends(get_repository, scope="function")]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/metrics", response_model=list[MetricDefinition])
def metrics() -> list[MetricDefinition]:
    return list(METRICS.values())


@router.post("/securities", response_model=SecurityRead, status_code=201)
def create_security(data: SecurityCreate, repository: Repository) -> SecurityRead:
    return repository.create_security(data)


@router.get("/securities", response_model=list[SecurityRead])
def securities(
    repository: Repository, limit: Limit = 100, offset: Offset = 0
) -> list[SecurityRead]:
    return repository.securities(limit=limit, offset=offset)


@router.get("/securities/{security_id}", response_model=SecurityRead)
def security(security_id: UUID, repository: Repository) -> SecurityRead:
    return repository.get_security(security_id)


@router.put("/securities/{security_id}", response_model=SecurityRead)
def update_security(
    security_id: UUID, data: SecurityCreate, repository: Repository
) -> SecurityRead:
    return repository.update_security(security_id, data)


@router.post(
    "/securities/{security_id}/fundamentals", response_model=list[ObservationRead], status_code=201
)
def import_observations(
    security_id: UUID,
    data: ObservationBatch,
    repository: Repository,
) -> list[ObservationRead]:
    return repository.import_observations(security_id, data.observations)


@router.get("/securities/{security_id}/fundamentals", response_model=ObservationPage)
def observations(
    security_id: UUID,
    repository: Repository,
    as_of: Annotated[AwareDatetime, Query()],
    known_at: Annotated[AwareDatetime | None, Query()] = None,
    source: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> ObservationPage:
    cutoff = known_at or datetime.now(UTC)
    items = repository.observations(
        security_id, as_of, known_at=cutoff, source=source, limit=limit, offset=offset
    )
    return ObservationPage(items=items, as_of=as_of, known_at=cutoff, limit=limit, offset=offset)
