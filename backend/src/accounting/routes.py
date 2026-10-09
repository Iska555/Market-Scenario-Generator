"""Private ledger endpoints, without financial arithmetic in transport."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from src.accounting.contracts import (
    Batch,
    BatchResult,
    CsvImport,
    History,
    ImportResult,
    LedgerState,
    PortfolioCreate,
    PortfolioRead,
    ValuationRequest,
    ValuationResult,
)
from src.accounting.imports import parse_csv
from src.accounting.repository import LedgerRepository
from src.accounting.valuation import value_state
from src.research.database import get_session, require_research_access
from src.research.repository import ResearchConflict, ResearchNotFound


def private_response(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/accounting",
    tags=["accounting"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


def get_repository(
    session: Annotated[Session, Depends(get_session, scope="function")],
) -> Iterator[LedgerRepository]:
    try:
        yield LedgerRepository(session)
    except ResearchNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except ResearchConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


Repository = Annotated[LedgerRepository, Depends(get_repository, scope="function")]


@router.get("/portfolios", response_model=list[PortfolioRead])
def portfolios(repository: Repository) -> list[PortfolioRead]:
    return repository.portfolios()


@router.post("/portfolios", response_model=PortfolioRead, status_code=201)
def create_portfolio(data: PortfolioCreate, repository: Repository) -> PortfolioRead:
    return repository.create_portfolio(data)


@router.get("/portfolios/{portfolio_id}/transactions", response_model=History)
def history(
    portfolio_id: UUID,
    repository: Repository,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> History:
    return repository.history(portfolio_id, limit, offset)


@router.get("/portfolios/{portfolio_id}/state", response_model=LedgerState)
def state(
    portfolio_id: UUID,
    repository: Repository,
    as_of: AwareDatetime | None = None,
    known_at: AwareDatetime | None = None,
) -> LedgerState:
    return repository.state(portfolio_id, as_of, known_at)


@router.post("/portfolios/{portfolio_id}/transactions/preview", response_model=BatchResult)
def preview(portfolio_id: UUID, data: Batch, repository: Repository) -> BatchResult:
    return repository.evaluate(portfolio_id, data, save=False)


@router.post("/portfolios/{portfolio_id}/transactions", response_model=BatchResult)
def append(portfolio_id: UUID, data: Batch, repository: Repository) -> BatchResult:
    return repository.evaluate(portfolio_id, data, save=True)


@router.post("/portfolios/{portfolio_id}/imports/preview", response_model=ImportResult)
def import_preview(portfolio_id: UUID, data: CsvImport, repository: Repository) -> ImportResult:
    batch = parse_csv(data)
    result = repository.evaluate(portfolio_id, batch, save=False)
    return ImportResult(**result.model_dump(), normalized_request=batch)


@router.post("/portfolios/{portfolio_id}/valuation", response_model=ValuationResult)
def valuation(
    portfolio_id: UUID, data: ValuationRequest, repository: Repository
) -> ValuationResult:
    snapshot = repository.state(portfolio_id, data.as_of, data.known_at)
    return value_state(snapshot, data)
