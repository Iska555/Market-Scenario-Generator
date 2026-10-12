"""Private read-only comparison sharing the performance/contribution row lock."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.accounting.routes import Repository, private_response
from src.attribution.engine import build_contribution
from src.benchmark.contracts import (
    ComparisonReport,
    ComparisonRequest,
    Selection,
    SettingCreate,
    SettingsHistory,
)
from src.benchmark.engine import build_comparison
from src.benchmark.settings import append, history, selected
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
    selection = selected(
        repository,
        portfolio_id,
        data.saved_benchmark_revision,
        data.benchmark.identity,
        data.performance.known_at,
    )
    return build_comparison(performance, data.benchmark, contribution, selection)


@router.get("/portfolios/{portfolio_id}/settings", response_model=SettingsHistory)
def settings_history(
    portfolio_id: UUID,
    repository: Repository,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SettingsHistory:
    return history(repository, portfolio_id, limit, offset)


@router.post("/portfolios/{portfolio_id}/settings", response_model=Selection, status_code=201)
def save_setting(portfolio_id: UUID, data: SettingCreate, repository: Repository) -> Selection:
    return append(repository, portfolio_id, data)
