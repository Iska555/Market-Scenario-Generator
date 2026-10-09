"""One private calculation resource; no financial calculations in transport."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.research.database import get_session, require_research_access
from src.research.repository import ResearchNotFound
from src.valuation.contracts import EvaluationRequest
from src.valuation.service import EvaluationResponse, evaluate

router = APIRouter(
    prefix="/api/research/valuation",
    tags=["valuation"],
    dependencies=[Depends(require_research_access)],
)


@router.post("/evaluate", response_model=EvaluationResponse)
def evaluate_model(
    request: EvaluationRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session, scope="function")],
) -> EvaluationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return evaluate(session, request)
    except ResearchNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(
            status_code=422, detail="Invalid model domain, evidence, or numerical calculation"
        ) from exc
