from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict
import numpy as np

from src.data_download import download_price_data
from src.returns_preprocess import compute_log_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol, sample_ewma_returns

# NEW: Multi-asset imports
from src.correlation import (
    download_multi_asset_data,
    compute_correlation_matrix,
    cholesky_decomposition,
    simulate_correlated_returns,
    build_portfolio_paths,
    compute_portfolio_risk_stats
)

app = FastAPI(
    title="Market Scenario Generator API",
    description="Professional portfolio risk simulation with multi-asset correlation",
    version="2.0.0"
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

# NEW: Multi-Asset Models
class PortfolioSimulationRequest(BaseModel):
    tickers: List[str] = Field(..., description="List of tickers", min_items=2, max_items=10)
    weights: Optional[List[float]] = Field(None, description="Portfolio weights (must sum to 1)")
    years: int = Field(3, ge=1, le=10)
    horizon: int = Field(252, ge=1, le=1000)
    num_paths: int = Field(1000, ge=100, le=5000)
    model: Literal["gaussian", "gmm"] = Field("gaussian")
    random_seed: Optional[int] = Field(42)

class AssetStats(BaseModel):
    ticker: str
    start_price: float
    final_mean: float
    contribution: float

class PortfolioRiskStats(BaseModel):
    mean: float
    volatility: float
    VaR_95: float
    CVaR_95: float
    prob_loss: float
    sharpe_ratio: float
    max_return: float
    min_return: float

class PortfolioSimulationResponse(BaseModel):
    tickers: List[str]
    weights: List[float]
    model: str
    correlation_matrix: Dict[str, Dict[str, float]]
    portfolio_paths_sample: List[List[float]]
    asset_paths_sample: Dict[str, List[List[float]]]
    asset_stats: List[AssetStats]
    portfolio_stats: PortfolioRiskStats
    message: str

# ============================================================================
# Helper Functions (Single Asset)
# ============================================================================

def build_paths_from_returns(start_price: float, returns_matrix: np.ndarray) -> np.ndarray:
    cum_returns = returns_matrix.cumsum(axis=1)
    return start_price * np.exp(cum_returns)

def compute_risk_stats(final_returns: np.ndarray, annualized_vol: float) -> RiskStats:
    mean = float(final_returns.mean())
    var_95 = float(np.percentile(final_returns, 5))
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
        "version": "2.0.0",
        "features": ["single-asset", "multi-asset-portfolio", "correlation-modeling"]
    }

@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_scenarios(request: SimulationRequest):
    """Single asset simulation (existing endpoint)."""
    try:
        if request.random_seed is not None:
            np.random.seed(request.random_seed)
        
        df = download_price_data(request.ticker, request.years)
        if df.empty or len(df) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {request.ticker}")
        
        log_returns = compute_log_returns(df)
        log_returns_clean = log_returns[log_returns.abs() < 0.20]
        start_price = float(df["price"].iloc[-1])
        
        if request.model == "gaussian":
            mu, sigma = fit_gaussian(log_returns_clean)
            adj_mu = mu - 0.5 * (sigma ** 2)
            returns_matrix = sample_gaussian(adj_mu, sigma, request.horizon, request.num_paths, request.random_seed)
        elif request.model == "gmm":
            gmm = fit_gmm(log_returns_clean, n_components=3)
            returns_matrix = sample_gmm(gmm, request.horizon, request.num_paths)
            returns_matrix = np.clip(returns_matrix, -0.12, 0.12)
            returns_matrix = returns_matrix - np.mean(returns_matrix)
        elif request.model == "ewma":
            ewma_series = compute_ewma_vol(log_returns_clean)
            mu = float(log_returns_clean.mean())
            last_vol = float(ewma_series.iloc[-1])
            vol_forecast = forecast_ewma_vol(last_vol, lam=0.94, horizon=request.horizon)
            adj_mu = mu - 0.5 * np.mean(vol_forecast ** 2)
            returns_matrix = sample_ewma_returns(adj_mu, vol_forecast, request.num_paths)
        
        daily_std = float(np.std(returns_matrix))
        annualized_vol = daily_std * np.sqrt(252)
        paths = build_paths_from_returns(start_price, returns_matrix)
        final_prices = paths[:, -1]
        final_returns = final_prices / start_price - 1
        risk_stats = compute_risk_stats(final_returns, annualized_vol)
        
        return SimulationResponse(
            ticker=request.ticker,
            model=request.model,
            start_price=start_price,
            final_prices=final_prices.tolist(),
            final_returns=final_returns.tolist(),
            risk_stats=risk_stats,
            paths_sample=paths[:50].tolist(),
            message=f"Successfully simulated {request.num_paths} paths"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate-portfolio", response_model=PortfolioSimulationResponse)
async def simulate_portfolio(request: PortfolioSimulationRequest):
    """
    NEW: Multi-asset portfolio simulation with correlation.
    
    This is hedge fund grade technology using Cholesky decomposition
    to preserve historical correlation structure.
    """
    try:
        if request.random_seed is not None:
            np.random.seed(request.random_seed)
        
        # 1. Validate and set weights
        if request.weights is None:
            weights = np.ones(len(request.tickers)) / len(request.tickers)
        else:
            if len(request.weights) != len(request.tickers):
                raise HTTPException(status_code=400, detail="Weights must match number of tickers")
            weights = np.array(request.weights)
            if not np.isclose(weights.sum(), 1.0):
                raise HTTPException(status_code=400, detail="Weights must sum to 1.0")
        
        # 2. Download multi-asset data
        price_data = download_multi_asset_data(request.tickers, request.years)
        
        if len(price_data) < len(request.tickers):
            missing = set(request.tickers) - set(price_data.keys())
            raise HTTPException(status_code=404, detail=f"Failed to download: {missing}")
        
        # 3. Compute correlation matrix
        returns_df, corr_matrix = compute_correlation_matrix(price_data)
        
        # 4. Cholesky decomposition
        L = cholesky_decomposition(corr_matrix)
        
        # 5. Fit models for each asset
        means = []
        stds = []
        start_prices = []
        
        for ticker in request.tickers:
            log_rets = returns_df[ticker]
            clean_rets = log_rets[log_rets.abs() < 0.20]
            
            if request.model == "gaussian":
                mu, sigma = fit_gaussian(clean_rets)
                adj_mu = mu - 0.5 * (sigma ** 2)
                means.append(adj_mu)
                stds.append(sigma)
            elif request.model == "gmm":
                # For GMM, use empirical stats
                means.append(0.0)  # Risk-neutral
                stds.append(float(clean_rets.std()))
            
            start_prices.append(float(price_data[ticker]["price"].iloc[-1]))
        
        means = np.array(means)
        stds = np.array(stds)
        start_prices = np.array(start_prices)
        
        # 6. Generate correlated returns
        correlated_returns = simulate_correlated_returns(
            means, stds, L, request.horizon, request.num_paths, request.random_seed
        )
        
        # 7. Build asset and portfolio paths
        asset_paths, portfolio_paths = build_portfolio_paths(
            start_prices, correlated_returns, weights
        )
        
        # 8. Calculate portfolio statistics
        portfolio_final_returns = portfolio_paths[:, -1] / 1.0 - 1
        portfolio_daily_std = float(np.std(np.diff(np.log(portfolio_paths), axis=1)))
        portfolio_annualized_vol = portfolio_daily_std * np.sqrt(252)
        
        portfolio_stats_dict = compute_portfolio_risk_stats(
            portfolio_final_returns, portfolio_annualized_vol
        )
        
        portfolio_stats = PortfolioRiskStats(**portfolio_stats_dict)
        
        # 9. Calculate per-asset statistics
        asset_stats = []
        for i, ticker in enumerate(request.tickers):
            final_prices_asset = asset_paths[:, -1, i]
            final_mean = float((final_prices_asset / start_prices[i] - 1).mean())
            contribution = weights[i] * final_mean
            
            asset_stats.append(AssetStats(
                ticker=ticker,
                start_price=float(start_prices[i]),
                final_mean=final_mean,
                contribution=contribution
            ))
        
        # 10. Prepare response
        corr_dict = {
            ticker: {
                other: float(corr_matrix.loc[ticker, other])
                for other in request.tickers
            }
            for ticker in request.tickers
        }
        
        asset_paths_sample = {
            ticker: asset_paths[:30, :, i].tolist()
            for i, ticker in enumerate(request.tickers)
        }
        
        return PortfolioSimulationResponse(
            tickers=request.tickers,
            weights=weights.tolist(),
            model=request.model,
            correlation_matrix=corr_dict,
            portfolio_paths_sample=portfolio_paths[:30].tolist(),
            asset_paths_sample=asset_paths_sample,
            asset_stats=asset_stats,
            portfolio_stats=portfolio_stats,
            message=f"Successfully simulated {len(request.tickers)}-asset portfolio with {request.num_paths} paths"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}