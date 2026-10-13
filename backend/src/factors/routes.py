"""Private factor report using one locked performance/contribution/comparison snapshot."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from src.accounting.routes import Repository, private_response
from src.attribution.engine import build_contribution
from src.benchmark.engine import build_comparison
from src.benchmark.settings import selected
from src.factors.contracts import FactorReport, FactorRequest
from src.factors.engine import build_factor_report
from src.factors.source import SourceRequest, SourceReview, review_source
from src.performance.routes import report
from src.research.database import require_research_access

router = APIRouter(
    prefix="/api/factors",
    tags=["factors"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


@router.post("/portfolios/{portfolio_id}/source-review", response_model=SourceReview)
def source_review(portfolio_id: UUID, data: SourceRequest, repository: Repository) -> SourceReview:
    portfolio = repository.portfolio(portfolio_id)
    return review_source(data, portfolio_id, portfolio.base_currency, datetime.now(UTC))


@router.post("/portfolios/{portfolio_id}/report", response_model=FactorReport)
def factor_report(portfolio_id: UUID, data: FactorRequest, repository: Repository) -> FactorReport:
    performance = report(portfolio_id, data.performance, repository)
    contribution = build_contribution(performance) if data.include_contribution else None
    selection = (
        selected(
            repository,
            portfolio_id,
            data.saved_benchmark_revision,
            data.benchmark.identity,
            data.performance.known_at,
        )
        if data.benchmark
        else None
    )
    comparison = (
        build_comparison(performance, data.benchmark, contribution, selection)
        if data.benchmark
        else None
    )
    return build_factor_report(performance, data.factors, contribution, comparison)
