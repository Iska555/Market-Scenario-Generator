"""Read-only contribution transport sharing a locked Phase 8 snapshot."""

from uuid import UUID

from fastapi import APIRouter, Depends

from src.accounting.routes import Repository, private_response
from src.attribution.contracts import ContributionReport
from src.attribution.engine import build_contribution
from src.performance.contracts import PerformanceRequest
from src.performance.routes import report
from src.research.database import require_research_access

router = APIRouter(
    prefix="/api/attribution",
    tags=["attribution"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


@router.post("/portfolios/{portfolio_id}/contribution", response_model=ContributionReport)
def contribution(
    portfolio_id: UUID, data: PerformanceRequest, repository: Repository
) -> ContributionReport:
    return build_contribution(report(portfolio_id, data, repository))
