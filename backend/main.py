from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
import numpy as np
import pandas as pd

# Import your helper modules
# Ensure these files exist in your backend/src/ folder
from src.data_download import download_price_data
from src.returns_preprocess import compute_log_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol, sample_ewma_returns

app = FastAPI(
    title="Market Scenario Generator API",
    description="REST API for financial risk simulation and scenario generation",
    version="1.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local React Dev
        "https://market-scenario-generator.vercel.app", # Vercel Frontend
        "https://market-scenario-generator.onrender.com" # Render Backend (self)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class SimulationRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol", json_schema_extra={"example": "SPY"})
    years: int = Field(3, ge=1, le=10, description="Years of historical data")
    horizon: int = Field(252, ge=1, le=1000, description="Days to simulate forward")
    num_paths: int = Field(1000, ge=100, le=10000, description="Number of simulation paths")
    model: Literal["gaussian", "gmm", "ewma"] = Field("gaussian", description="Model type")
    random_seed: Optional[int] = Field(42, description="Random seed for reproducibility")

class RiskStats(BaseModel):
    mean: float
    vol: float  # Annualized Volatility
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

class ModelComparisonRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    years: int = Field(3, ge=1, le=10)
    horizon: int = Field(252, ge=1, le=1000)
    num_paths: int = Field(1000, ge=100, le=10000)
    models: List[Literal["gaussian", "gmm", "ewma"]] = Field(
        ["gaussian", "gmm", "ewma"],
        description="List of models to compare"
    )

# ============================================================================
# Helper Functions
# ============================================================================

def build_paths_from_returns(start_price: float, returns_matrix: np.ndarray) -> np.ndarray:
    """Convert simulated returns into price paths."""
    # cumsum along the time axis (axis 1)
    cumWy_returns = returns_matrix.cumsum(axis=1)
    return start_price * np.exp(cumWy_returns)

def compute_risk_stats(final_returns: np.ndarray, annualized_vol: float) -> RiskStats:
    """
    Compute risk statistics.
    annualized_vol: passed explicitly from the simulation matrix to be accurate.
    """
    mean = float(final_returns.mean())
    
    # VaR and CVaR (95%)
    var_95 = float(np.percentile(final_returns, 5))
    cvar_95 = float(final_returns[final_returns <= var_95].mean()) if len(final_returns[final_returns <= var_95]) > 0 else var_95
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
    return {"status": "running", "version": "1.0.1", "docs": "/docs"}

@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_scenarios(request: SimulationRequest):
    try:
        if request.random_seed is not None:
            np.random.seed(request.random_seed)
        
        # 1. Download historical data
        df = download_price_data(request.ticker, request.years)
        
        if df.empty or len(df) < 50:
            raise HTTPException(status_code=404, detail=f"Not enough data found for {request.ticker}")

        log_returns = compute_log_returns(df)
        
        # --- Safety: Clean Data ---
        # Remove any daily move > 30% (prevents bad data bugs, allows crypto)
        log_returns = log_returns[log_returns.abs() < 0.3]

        start_price = float(df["price"].iloc[-1])
        
        # 2. Generate returns based on model
        returns_matrix = None
        
        if request.model == "gaussian":
            mu, sigma = fit_gaussian(log_returns)
            # Adjust drift for geometric brownian motion: mu - 0.5*sigma^2
            adj_mu = mu - 0.5 * (sigma ** 2)
            returns_matrix = sample_gaussian(adj_mu, sigma, request.horizon, request.num_paths, request.random_seed)
        
        elif request.model == "gmm":
            gmm = fit_gmm(log_returns, n_components=3)
            returns_matrix = sample_gmm(gmm, request.horizon, request.num_paths)
            
            # --- CORRECTED FIX: Global Drift Adjustment ---
            # 1. Calculate the average drift across ALL paths and ALL days (a single number)
            overall_drift = np.mean(returns_matrix)
            
            # 2. Subtract that global trend from everything. 
            returns_matrix = returns_matrix - overall_drift
        
        elif request.model == "ewma":
            ewma_series = compute_ewma_vol(log_returns)
            mu = float(log_returns.mean())
            last_vol = float(ewma_series.iloc[-1])
            
            # Forecast constant volatility (Random Walk assumption for Vol)
            vol_forecast = forecast_ewma_vol(last_vol, lam=0.94, horizon=request.horizon)
            
            # Helper to sample with varying drift/vol
            returns_matrix = sample_ewma_returns(mu, vol_forecast, request.num_paths)
            # This ensures geometric returns don't drift upward artificially
            returns_matrix -= 0.5 * (vol_forecast ** 2)

        else:
            raise ValueError(f"Unknown model: {request.model}")
        
        # 3. Calculate Annualized Volatility (The number users expect)
        # Std dev of daily returns * sqrt(252)
        daily_std = np.std(returns_matrix)
        annualized_vol = float(daily_std * np.sqrt(252))

        # 4. Build price paths
        paths = build_paths_from_returns(start_price, returns_matrix)
        
        # 5. Calculate final returns
        final_prices = paths[:, -1]
        final_returns = final_prices / start_price - 1
        
        # 6. Compute stats passing the correct Vol
        risk_stats = compute_risk_stats(final_returns, annualized_vol)
        
        # 7. Sample paths (Send only 50 to frontend to keep JSON light)
        # The frontend chart uses these to draw the "cloud"
        paths_sample = paths[:50].tolist()
        
        return SimulationResponse(
            ticker=request.ticker,
            model=request.model,
            start_price=start_price,
            final_prices=final_prices.tolist(),
            final_returns=final_returns.tolist(),
            risk_stats=risk_stats,
            paths_sample=paths_sample,
            message=f"Success: {request.num_paths} paths, {request.model} model"
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc() # Print error to server logs for debugging
        raise HTTPException(status_code=500, detail=str(e))

# Placeholder endpoint for the "Compare" tab
@app.post("/api/compare")
async def compare_models(request: ModelComparisonRequest):
    return {
        "message": "Comparison feature coming soon!",
        "ticker": request.ticker,
        "models_requested": request.models
    }