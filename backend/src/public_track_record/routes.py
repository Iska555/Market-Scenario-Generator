"""Owner-only identity adapters; no anonymous access or publication in L1."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from src.accounting.routes import Repository, private_response
from src.public_track_record.contracts import DemoCreate, PortfolioContext
from src.public_track_record.demo import DemoEvidence, DemoReceipt, demo_evidence, load_demo
from src.public_track_record.repository import create_demo, portfolios
from src.research.database import require_research_access

router = APIRouter(
    prefix="/api/portfolio-identity",
    tags=["portfolio-identity"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


@router.get("/portfolios", response_model=list[PortfolioContext])
def list_portfolios(repository: Repository) -> list[PortfolioContext]:
    return portfolios(repository)


@router.post("/portfolios", response_model=PortfolioContext, status_code=201)
def new_demo(data: DemoCreate, repository: Repository) -> PortfolioContext:
    return create_demo(repository, data)


@router.post("/portfolios/{portfolio_id}/demo/load", response_model=DemoReceipt)
def load_example(portfolio_id: UUID, repository: Repository) -> DemoReceipt:
    return load_demo(repository, portfolio_id)


@router.get("/portfolios/{portfolio_id}/demo/evidence", response_model=DemoEvidence)
def example_evidence(portfolio_id: UUID, repository: Repository) -> dict[str, Any]:
    return demo_evidence(repository, portfolio_id)
