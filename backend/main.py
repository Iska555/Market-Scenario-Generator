"""FastAPI transport: validation and orchestration, without financial formulas."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.accounting.routes import router as accounting_router
from src.api.models import (
    PortfolioSimulationRequest,
    PortfolioSimulationResponse,
    SimulationRequest,
    SimulationResponse,
)
from src.attribution.routes import router as attribution_router
from src.benchmark.routes import router as benchmark_router
from src.data.providers import CachedPriceProvider, PriceDataError
from src.factors.routes import router as factors_router
from src.performance.routes import router as performance_router
from src.portfolio.construction.routes import router as construction_router
from src.research.routes import router as research_router
from src.research.thesis.routes import router as thesis_router
from src.risk.scenarios.historical_routes import router as historical_router
from src.risk.scenarios.service import run_portfolio, run_single
from src.valuation.routes import router as valuation_router
from starlette.middleware.base import RequestResponseEndpoint

API_VERSION = "3.0.0"
app = FastAPI(title="Investment Management Workspace — Risk & Scenario Lab", version=API_VERSION)
app.include_router(research_router)
app.include_router(thesis_router)
app.include_router(valuation_router)
app.include_router(construction_router)
app.include_router(historical_router)
app.include_router(accounting_router)
app.include_router(performance_router)
app.include_router(attribution_router)
app.include_router(benchmark_router)
app.include_router(factors_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        s.strip() for s in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)
get_cached_price_data = CachedPriceProvider()


@app.middleware("http")
async def factor_private_cache(request: Request, call_next: RequestResponseEndpoint) -> Response:
    response = await call_next(request)
    if request.url.path.startswith("/api/factors/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# The two-cell limit bounds simultaneous tensor memory in this process. Waiting
# requests allocate no simulation tensors and never block the ASGI event loop.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="scenario")


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic's original input/context may contain NaN/Infinity or exception
    # objects. Return just serializable diagnostic fields; never echo raw inputs.
    errors = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "running", "version": API_VERSION}


@app.get("/ping")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": API_VERSION}


@app.get("/api/version")
def version() -> dict[str, str | None]:
    return {
        "api_version": API_VERSION,
        "git_commit_sha": os.getenv("GIT_COMMIT_SHA"),
        "build_timestamp": os.getenv("BUILD_TIMESTAMP"),
    }


def price_provider(ticker: str, years: int) -> pd.DataFrame:
    return get_cached_price_data(ticker, years)


@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_scenarios(request: SimulationRequest) -> SimulationResponse:
    try:
        return await asyncio.get_running_loop().run_in_executor(
            _executor, run_single, request, price_provider
        )
    except PriceDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, FloatingPointError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/simulate-portfolio", response_model=PortfolioSimulationResponse)
async def simulate_portfolio(request: PortfolioSimulationRequest) -> PortfolioSimulationResponse:
    try:
        return await asyncio.get_running_loop().run_in_executor(
            _executor, run_portfolio, request, price_provider
        )
    except PriceDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, FloatingPointError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
