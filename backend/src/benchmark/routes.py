"""Private read-only comparison sharing the performance/contribution row lock."""

from uuid import UUID

from fastapi import APIRouter, Depends

from src.accounting.routes import Repository, private_response
from src.attribution.engine import build_contribution
from src.benchmark.contracts import ComparisonReport, ComparisonRequest
from src.benchmark.engine import build_comparison
from src.performance.routes import report
from src.research.database import require_research_access

router = APIRouter(
    prefix="/api/benchmark",
    tags=["benchmark"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


@router.post("/portfolios/{portfolio_id}/comparison", response_model=ComparisonReport)
def comparison(
    portfolio_id: UUID, data: ComparisonRequest, repository: Repository
) -> ComparisonReport:
    performance = report(portfolio_id, data.performance, repository)
    contribution = build_contribution(performance) if data.include_contribution else None
    return build_comparison(performance, data.benchmark, contribution)
