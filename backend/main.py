from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
import numpy as np

from src.data_download import download_price_data
from src.returns_preprocess import compute_log_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol, sample_ewma_returns

app = FastAPI(
    title="Market Scenario Generator API",
    description="REST API for financial risk simulation and scenario generation",
    version="1.0.3"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://market-scenario-generator.vercel.app",
        "https://market-scenario-generator.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class SimulationRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    years: int = Field(3, ge=1, le=10)
    horizon: int = Field(252, ge=1, le=1000)
    num_paths: int = Field(1000, ge=100, le=10000)
    model: Literal["gaussian", "gmm", "ewma"] = Field("gaussian")
    random_seed: Optional[int] = Field(42)

class RiskStats(BaseModel):
    mean: float
    vol: float
    VaR_95: float
    CVaR_95: float
    prob_loss: float

class SimulationResponse(BaseModel):
    ticker: str
    model: str
    start_price: float
    final_prices: List[float]
    final_returns: List[float]
    risk_stats: RiskStats
    paths_sample: List[List[float]]
    message: str

# ============================================================================
# Helper Functions
# ============================================================================

def build_paths_from_returns(start_price: float, returns_matrix: np.ndarray) -> np.ndarray:
    """Convert log returns to price paths using cumulative sum."""
    cum_returns = returns_matrix.cumsum(axis=1)
    return start_price * np.exp(cum_returns)

def compute_risk_stats(final_returns: np.ndarray, annualized_vol: float) -> RiskStats:
    """Calculate risk metrics from final returns."""
    mean = float(final_returns.mean())
    var_95 = float(np.percentile(final_returns, 5))
    
    # CVaR: Average of worst 5% outcomes
    tail_losses = final_returns[final_returns <= var_95]
    cvar_95 = float(tail_losses.mean()) if len(tail_losses) > 0 else var_95
    
    prob_loss = float((final_returns < 0).mean())
    
    return RiskStats(
        mean=mean,
        vol=annualized_vol,
        VaR_95=var_95,
        CVaR_95=cvar_95,
        prob_loss=prob_loss
    )

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def root():
    return {
        "status": "running",
        "version": "1.0.3",
        "message": "Market Scenario Generator API"
    }

@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_scenarios(request: SimulationRequest):
    """
    Run Monte Carlo simulation with specified model.
    Returns risk metrics and sample paths.
    """
    try:
        if request.random_seed is not None:
            np.random.seed(request.random_seed)
        
        # 1. Download and validate data
        df = download_price_data(request.ticker, request.years)
        if df.empty or len(df) < 50:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient data for {request.ticker}"
            )
        
        log_returns = compute_log_returns(df)
        
        # Remove extreme outliers (data errors, stock splits)
        # Keep returns within -20% to +20% daily
        log_returns_clean = log_returns[log_returns.abs() < 0.20]
        
        if len(log_returns_clean) < 30:
            raise HTTPException(
                status_code=400,
                detail="Not enough clean data after filtering outliers"
            )

        start_price = float(df["price"].iloc[-1])
        
        # 2. Generate returns based on model
        if request.model == "gaussian":
            mu, sigma = fit_gaussian(log_returns_clean)
            # Drift adjustment for geometric Brownian motion
            adj_mu = mu - 0.5 * (sigma ** 2)
            returns_matrix = sample_gaussian(
                adj_mu, sigma, request.horizon, request.num_paths, request.random_seed
            )
        
        elif request.model == "gmm":
            gmm = fit_gmm(log_returns_clean, n_components=3)
            returns_matrix = sample_gmm(gmm, request.horizon, request.num_paths)
            
            # CRITICAL FIX: GMM can sample extreme tail events
            # Apply realistic daily return limits
            returns_matrix = np.clip(returns_matrix, -0.12, 0.12)  # ±12% daily limit
            
            # Remove drift to make it risk-neutral
            sample_mean = np.mean(returns_matrix)
            returns_matrix = returns_matrix - sample_mean
        
        elif request.model == "ewma":
            ewma_series = compute_ewma_vol(log_returns_clean)
            mu = float(log_returns_clean.mean())
            last_vol = float(ewma_series.iloc[-1])
            
            vol_forecast = forecast_ewma_vol(last_vol, lam=0.94, horizon=request.horizon)
            
            # Drift adjustment
            adj_mu = mu - 0.5 * np.mean(vol_forecast ** 2)
            returns_matrix = sample_ewma_returns(adj_mu, vol_forecast, request.num_paths)
        
        else:
            raise ValueError(f"Unknown model: {request.model}")
        
        # 3. Calculate annualized volatility
        daily_std = float(np.std(returns_matrix))
        annualized_vol = daily_std * np.sqrt(252)
        
        # 4. Build price paths
        paths = build_paths_from_returns(start_price, returns_matrix)
        
        # 5. Calculate final returns
        final_prices = paths[:, -1]
        final_returns = final_prices / start_price - 1
        
        # 6. Compute risk statistics
        risk_stats = compute_risk_stats(final_returns, annualized_vol)
        
        # 7. Sample paths for visualization
        paths_sample = paths[:50].tolist()
        
        return SimulationResponse(
            ticker=request.ticker,
            model=request.model,
            start_price=start_price,
            final_prices=final_prices.tolist(),
            final_returns=final_returns.tolist(),
            risk_stats=risk_stats,
            paths_sample=paths_sample,
            message=f"Successfully simulated {request.num_paths} paths using {request.model} model"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.3"}