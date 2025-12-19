from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
import numpy as np

# Import your helper modules
from src.data_download import download_price_data
from src.returns_preprocess import compute_log_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol, sample_ewma_returns

app = FastAPI(
    title="Market Scenario Generator API",
    description="REST API for financial risk simulation and scenario generation",
    version="1.0.2"
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
    cumWy_returns = returns_matrix.cumsum(axis=1)
    return start_price * np.exp(cumWy_returns)

def compute_risk_stats(final_returns: np.ndarray, annualized_vol: float) -> RiskStats:
    mean = float(final_returns.mean())
    var_95 = float(np.percentile(final_returns, 5))
    
    # Calculate CVaR (Expected Shortfall)
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
    return {"status": "running", "version": "1.0.2"}

@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_scenarios(request: SimulationRequest):
    try:
        if request.random_seed is not None:
            np.random.seed(request.random_seed)
        
        # 1. Download & Clean Data
        df = download_price_data(request.ticker, request.years)
        if df.empty or len(df) < 50:
            raise HTTPException(status_code=404, detail=f"Not enough data found for {request.ticker}")
        
        log_returns = compute_log_returns(df)
        
        # Crypto Safety: Remove extreme daily outliers > 30% to prevent blown-up variance
        log_returns = log_returns[log_returns.abs() < 0.3]

        start_price = float(df["price"].iloc[-1])
        returns_matrix = None
        
        # 2. Run Models (With FORCED ZERO DRIFT for Risk Analysis)
        
        if request.model == "gaussian":
            mu, sigma = fit_gaussian(log_returns)
            
            # FORCE DRIFT TO ZERO: We ignore historical 'mu' and set it to 0.0
            adj_mu = 0.0 - 0.5 * (sigma ** 2)
            
            returns_matrix = sample_gaussian(adj_mu, sigma, request.horizon, request.num_paths, request.random_seed)
        
        elif request.model == "gmm":
            gmm = fit_gmm(log_returns, n_components=3)
            returns_matrix = sample_gmm(gmm, request.horizon, request.num_paths)
            
            global_mean = np.mean(returns_matrix)
            returns_matrix = returns_matrix - global_mean
        
        elif request.model == "ewma":
            ewma_series = compute_ewma_vol(log_returns)
            last_vol = float(ewma_series.iloc[-1])
            vol_forecast = forecast_ewma_vol(last_vol, lam=0.94, horizon=request.horizon)
            
            # FORCE DRIFT TO ZERO: Pass mu=0.0 instead of historical mean
            returns_matrix = sample_ewma_returns(0.0, vol_forecast, request.num_paths)
            returns_matrix -= 0.5 * (vol_forecast ** 2)

        else:
            raise ValueError(f"Unknown model: {request.model}")
        
        # 3. Calculate Stats
        daily_std = np.std(returns_matrix)
        annualized_vol = float(daily_std * np.sqrt(252))

        paths = build_paths_from_returns(start_price, returns_matrix)
        final_prices = paths[:, -1]
        final_returns = final_prices / start_price - 1
        
        risk_stats = compute_risk_stats(final_returns, annualized_vol)
        paths_sample = paths[:50].tolist()
        
        return SimulationResponse(
            ticker=request.ticker,
            model=request.model,
            start_price=start_price,
            final_prices=final_prices.tolist(),
            final_returns=final_returns.tolist(),
            risk_stats=risk_stats,
            paths_sample=paths_sample,
            message="Success - Drift fixed"
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))