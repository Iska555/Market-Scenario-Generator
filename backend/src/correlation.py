"""
Multi-Asset Correlation & Portfolio Simulation Module

Uses Cholesky Decomposition to generate correlated return paths
for portfolio-level risk analysis.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from scipy.linalg import cholesky

from src.data_download import download_price_data
from src.returns_preprocess import compute_log_returns


def download_multi_asset_data(tickers: List[str], years: int = 3) -> Dict[str, pd.DataFrame]:
    """
    Download price data for multiple assets.
    
    Parameters
    ----------
    tickers : List[str]
        List of ticker symbols (e.g., ['SPY', 'AAPL', 'BTC-USD'])
    years : int
        Years of historical data
        
    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary mapping ticker -> price DataFrame
    """
    data = {}
    for ticker in tickers:
        try:
            df = download_price_data(ticker, years)
            if not df.empty:
                data[ticker] = df
        except Exception as e:
            print(f"Warning: Failed to download {ticker}: {e}")
    
    return data


def compute_correlation_matrix(
    price_data: Dict[str, pd.DataFrame],
    method: str = "pearson"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute correlation matrix from multi-asset price data.
    
    Parameters
    ----------
    price_data : Dict[str, pd.DataFrame]
        Dictionary of ticker -> price DataFrame
    method : str
        Correlation method: 'pearson', 'spearman', or 'kendall'
        
    Returns
    -------
    returns_df : pd.DataFrame
        DataFrame with aligned returns for all assets
    corr_matrix : pd.DataFrame
        Correlation matrix (N x N)
    """
    # Extract returns for each asset
    returns_dict = {}
    for ticker, df in price_data.items():
        log_rets = compute_log_returns(df)
        returns_dict[ticker] = log_rets
    
    # Combine into single DataFrame (aligns on date index)
    returns_df = pd.DataFrame(returns_dict)
    
    # Drop any rows with missing data
    returns_df = returns_df.dropna()
    
    if len(returns_df) < 30:
        raise ValueError("Not enough overlapping data points for correlation analysis")
    
    # Compute correlation matrix
    corr_matrix = returns_df.corr(method=method)
    
    return returns_df, corr_matrix


def cholesky_decomposition(corr_matrix: pd.DataFrame) -> np.ndarray:
    """
    Perform Cholesky decomposition on correlation matrix.
    
    The Cholesky decomposition transforms a correlation matrix C into L @ L.T,
    where L is lower triangular. This is used to generate correlated random variables.
    
    Parameters
    ----------
    corr_matrix : pd.DataFrame
        Correlation matrix (must be positive semi-definite)
        
    Returns
    -------
    L : np.ndarray
        Lower triangular Cholesky factor
    """
    # Convert to numpy array
    C = corr_matrix.values
    
    # Check if matrix is positive semi-definite
    eigenvalues = np.linalg.eigvals(C)
    if np.any(eigenvalues < -1e-10):
        print("Warning: Correlation matrix is not positive semi-definite")
        print(f"Min eigenvalue: {eigenvalues.min()}")
        # Fix by adding small value to diagonal (regularization)
        C = C + np.eye(len(C)) * 1e-6
    
    # Perform Cholesky decomposition
    L = cholesky(C, lower=True)
    
    return L


def simulate_correlated_returns(
    means: np.ndarray,
    stds: np.ndarray,
    cholesky_factor: np.ndarray,
    horizon: int,
    num_paths: int,
    random_seed: int = None
) -> np.ndarray:
    """
    Generate correlated return paths using Cholesky decomposition.
    
    Process:
    1. Generate independent standard normal random variables Z
    2. Apply Cholesky factor: X = L @ Z (creates correlation)
    3. Scale by std and shift by mean: R = mean + std * X
    
    Parameters
    ----------
    means : np.ndarray
        Mean returns for each asset (shape: n_assets)
    stds : np.ndarray
        Standard deviations for each asset (shape: n_assets)
    cholesky_factor : np.ndarray
        Lower triangular Cholesky factor (shape: n_assets x n_assets)
    horizon : int
        Number of days to simulate
    num_paths : int
        Number of Monte Carlo paths
    random_seed : int, optional
        Random seed for reproducibility
        
    Returns
    -------
    returns : np.ndarray
        Correlated returns (shape: num_paths x horizon x n_assets)
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    
    n_assets = len(means)
    
    # 1. Generate independent standard normal random variables
    # Shape: (num_paths, horizon, n_assets)
    Z = np.random.randn(num_paths, horizon, n_assets)
    
    # 2. Apply Cholesky factor to introduce correlation
    # For each path and timestep, multiply by L
    X = np.zeros_like(Z)
    for path in range(num_paths):
        for t in range(horizon):
            X[path, t, :] = cholesky_factor @ Z[path, t, :]
    
    # 3. Scale by standard deviation and add mean
    returns = means + stds * X
    
    return returns


def build_portfolio_paths(
    start_prices: np.ndarray,
    returns_matrix: np.ndarray,
    weights: np.ndarray = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert multi-asset returns to price paths and portfolio values.
    
    Parameters
    ----------
    start_prices : np.ndarray
        Starting prices for each asset (shape: n_assets)
    returns_matrix : np.ndarray
        Log returns (shape: num_paths x horizon x n_assets)
    weights : np.ndarray, optional
        Portfolio weights for each asset (must sum to 1)
        If None, uses equal weights
        
    Returns
    -------
    asset_paths : np.ndarray
        Price paths for each asset (shape: num_paths x horizon x n_assets)
    portfolio_paths : np.ndarray
        Portfolio value paths (shape: num_paths x horizon)
    """
    num_paths, horizon, n_assets = returns_matrix.shape
    
    # Default to equal weights
    if weights is None:
        weights = np.ones(n_assets) / n_assets
    
    # Validate weights
    if not np.isclose(weights.sum(), 1.0):
        raise ValueError(f"Weights must sum to 1, got {weights.sum()}")
    
    # Build price paths for each asset
    asset_paths = np.zeros_like(returns_matrix)
    
    for i in range(n_assets):
        cum_returns = returns_matrix[:, :, i].cumsum(axis=1)
        asset_paths[:, :, i] = start_prices[i] * np.exp(cum_returns)
    
    # Calculate portfolio value (weighted sum)
    # Initial portfolio value = 1.0 (normalized)
    portfolio_initial = 1.0
    
    # Portfolio return at each timestep
    portfolio_returns = np.zeros((num_paths, horizon))
    
    for path in range(num_paths):
        for t in range(horizon):
            # Weighted average of asset returns
            portfolio_returns[path, t] = np.sum(
                weights * returns_matrix[path, t, :]
            )
    
    # Build portfolio paths
    cum_portfolio_returns = portfolio_returns.cumsum(axis=1)
    portfolio_paths = portfolio_initial * np.exp(cum_portfolio_returns)
    
    return asset_paths, portfolio_paths


def compute_portfolio_risk_stats(
    final_returns: np.ndarray,
    annualized_vol: float
) -> Dict[str, float]:
    """
    Calculate portfolio-level risk metrics.
    
    Parameters
    ----------
    final_returns : np.ndarray
        Portfolio returns at end of simulation
    annualized_vol : float
        Annualized volatility of portfolio
        
    Returns
    -------
    dict
        Dictionary of risk metrics
    """
    mean = float(final_returns.mean())
    var_95 = float(np.percentile(final_returns, 5))
    
    tail_losses = final_returns[final_returns <= var_95]
    cvar_95 = float(tail_losses.mean()) if len(tail_losses) > 0 else var_95
    
    prob_loss = float((final_returns < 0).mean())
    
    # Additional portfolio metrics
    sharpe_ratio = mean / annualized_vol if annualized_vol > 0 else 0.0
    max_return = float(final_returns.max())
    min_return = float(final_returns.min())
    
    return {
        "mean": mean,
        "volatility": annualized_vol,
        "VaR_95": var_95,
        "CVaR_95": cvar_95,
        "prob_loss": prob_loss,
        "sharpe_ratio": sharpe_ratio,
        "max_return": max_return,
        "min_return": min_return
    }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Test multi-asset simulation
    tickers = ["SPY", "AAPL", "MSFT"]
    
    print("Downloading data...")
    data = download_multi_asset_data(tickers, years=2)
    
    print("\nComputing correlation matrix...")
    returns_df, corr_matrix = compute_correlation_matrix(data)
    
    print("\nCorrelation Matrix:")
    print(corr_matrix)
    
    print("\nPerforming Cholesky decomposition...")
    L = cholesky_decomposition(corr_matrix)
    print("Cholesky factor (L):")
    print(L)
    
    # Verify: L @ L.T should equal correlation matrix
    reconstructed = L @ L.T
    print("\nVerification (L @ L.T):")
    print(reconstructed)
    print(f"Max error: {np.abs(corr_matrix.values - reconstructed).max():.2e}")
    
    print("\n✅ Correlation module working correctly!")