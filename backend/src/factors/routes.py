"""Private factor report using one locked performance/contribution/comparison snapshot."""

from uuid import UUID

from fastapi import APIRouter, Depends

from src.accounting.routes import Repository, private_response
from src.attribution.engine import build_contribution
from src.benchmark.engine import build_comparison
from src.factors.contracts import FactorReport, FactorRequest
from src.factors.engine import build_factor_report
from src.performance.routes import report
from src.research.database import require_research_access

router = APIRouter(
    prefix="/api/factors",
    tags=["factors"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


@router.post("/portfolios/{portfolio_id}/report", response_model=FactorReport)
def factor_report(portfolio_id: UUID, data: FactorRequest, repository: Repository) -> FactorReport:
    performance = report(portfolio_id, data.performance, repository)
    contribution = build_contribution(performance) if data.include_contribution else None
    comparison = (
        build_comparison(performance, data.benchmark, contribution) if data.benchmark else None
    )
    return build_factor_report(performance, data.factors, contribution, comparison)
