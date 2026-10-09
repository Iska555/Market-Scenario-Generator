"""Read-only private performance transport; all arithmetic stays in domain code."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.accounting.routes import Repository, private_response
from src.performance.contracts import PerformanceReport, PerformanceRequest
from src.performance.engine import build_report, close
from src.research.database import require_research_access
from src.research.repository import ResearchConflict

router = APIRouter(
    prefix="/api/performance",
    tags=["performance"],
    dependencies=[Depends(require_research_access), Depends(private_response)],
)


@router.post("/portfolios/{portfolio_id}/report", response_model=PerformanceReport)
def report(
    portfolio_id: UUID, data: PerformanceRequest, repository: Repository
) -> PerformanceReport:
    portfolio = repository.portfolio(portfolio_id)
    rows = repository.rows(portfolio_id)
    current_version = max((r.sequence for r in rows), default=0)
    if data.expected_version != current_version:
        raise ResearchConflict("Ledger changed; reload the account and prepare the report again")
    now = datetime.now(UTC)
    if data.known_at > now or close(data.daily_marks[-1].date) > now:
        raise HTTPException(
            422, "Performance requires completed days and a non-future knowledge cutoff"
        )
    return build_report(portfolio_id, portfolio.base_currency, rows, data)
