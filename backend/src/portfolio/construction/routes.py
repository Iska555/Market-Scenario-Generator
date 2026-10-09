"""Thin private construction endpoint; no mathematics in transport."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.portfolio.construction.contracts import ConstructionRequest
from src.portfolio.construction.service import ConstructionResponse, evaluate_construction
from src.research.database import get_session, require_research_access
from src.research.repository import ResearchNotFound

router = APIRouter(
    prefix="/api/research/construction",
    tags=["construction"],
    dependencies=[Depends(require_research_access)],
)


@router.post("/evaluate", response_model=ConstructionResponse)
def evaluate(
    request: ConstructionRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session, scope="function")],
) -> ConstructionResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return evaluate_construction(session, request)
    except ResearchNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(
            status_code=422, detail="Invalid portfolio domain, data or evidence context"
        ) from exc
