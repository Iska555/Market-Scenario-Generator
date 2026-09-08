"""Symmetric covariance estimation and local-generator sampling."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.covariance import LedoitWolf


@dataclass(frozen=True)
class CovarianceEstimate:
    matrix: np.ndarray
    shrinkage: float


@dataclass(frozen=True)
class RiskContributions:
    volatility: float
    marginal: np.ndarray | None
    component: np.ndarray
    percentage: np.ndarray | None


def symmetric_matrix(matrix: np.ndarray) -> np.ndarray:
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or x.shape[0] != x.shape[1] or not x.size or not np.isfinite(x).all():
        raise ValueError("Expected a finite square matrix")
    if not np.allclose(x, x.T, rtol=1e-10, atol=1e-12):
        raise ValueError("Matrix must be symmetric")
    return np.asarray((x + x.T) / 2, dtype=float)


def psd_factor(matrix: np.ndarray) -> np.ndarray:
    x = symmetric_matrix(matrix)
    values, vectors = np.linalg.eigh(x)
    tolerance = 1e-12 * max(float(np.max(np.abs(values))), np.finfo(float).tiny)
    if values.min() < -tolerance:
        raise ValueError("Matrix is not positive semidefinite")
    # Only roundoff eigenvalues are set to zero. This never clips return samples.
    return np.asarray(vectors * np.sqrt(np.maximum(values, 0)), dtype=float)


def nearest_correlation(matrix: np.ndarray, tolerance: float = 1e-11) -> np.ndarray:
    """Higham alternating projections with Dykstra correction, Frobenius norm."""
    y = symmetric_matrix(matrix)
    correction = np.zeros_like(y)
    for _ in range(1000):
        previous = y.copy()
        residual = y - correction
        values, vectors = np.linalg.eigh(residual)
        projected = (vectors * np.maximum(values, 0)) @ vectors.T
        correction = projected - residual
        y = projected.copy()
        np.fill_diagonal(y, 1)
        if np.linalg.norm(y - previous, "fro") <= tolerance:
            # Final roundoff cleanup by PSD projection and diagonal normalization.
            values, vectors = np.linalg.eigh(y)
            y = (vectors * np.maximum(values, 0)) @ vectors.T
            scale = np.sqrt(np.diag(y))
            return np.asarray(y / np.outer(scale, scale), dtype=float)
    raise ValueError("Nearest-correlation projection did not converge")


def estimate_covariance(
    observations: np.ndarray, estimator: Literal["ledoit_wolf", "sample"] = "ledoit_wolf"
) -> CovarianceEstimate:
    x = np.asarray(observations, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 1 or not np.isfinite(x).all():
        raise ValueError("Covariance requires at least two finite joint observations")
    if estimator == "ledoit_wolf":
        fitted = LedoitWolf().fit(x)
        return CovarianceEstimate(np.asarray(fitted.covariance_), float(fitted.shrinkage_))
    if estimator == "sample":
        return CovarianceEstimate(np.atleast_2d(np.cov(x, rowvar=False, ddof=1)), 0.0)
    raise ValueError("Unsupported covariance estimator")


def risk_contributions(covariance: np.ndarray, weights: np.ndarray) -> RiskContributions:
    covariance = symmetric_matrix(covariance)
    psd_factor(covariance)
    if weights.shape != (len(covariance),) or not np.isfinite(weights).all():
        raise ValueError("Weights must match covariance dimensions")
    variance = float(weights @ covariance @ weights)
    volatility = float(np.sqrt(max(variance, 0)))
    if volatility == 0:
        return RiskContributions(0, None, np.zeros_like(weights), None)
    marginal = covariance @ weights / volatility
    component = weights * marginal
    return RiskContributions(volatility, marginal, component, component / volatility)


def simulate_correlated_returns(
    means: np.ndarray,
    stds: np.ndarray,
    cholesky_factor: np.ndarray,
    horizon: int,
    num_paths: int,
    *,
    rng: np.random.Generator,
) -> np.ndarray:
    shocks = rng.standard_normal((num_paths, horizon, len(means)))
    return np.asarray(means + stds * (shocks @ cholesky_factor.T), dtype=float)
