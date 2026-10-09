"""Private stateless supplied-data stress transport."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.research.database import get_session, require_research_access
from src.research.repository import ResearchNotFound
from src.risk.scenarios.historical_contracts import StressRequest
from src.risk.scenarios.historical_service import StressResponse, evaluate

router = APIRouter(
    prefix="/api/research/stress", tags=["stress"], dependencies=[Depends(require_research_access)]
)


@router.post("/evaluate", response_model=StressResponse)
def evaluate_stress(
    request: StressRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session, scope="function")],
) -> StressResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return evaluate(session, request)
    except ResearchNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid scenario domain, currency, sample alignment or numerical calculation",
        ) from exc
