"""Convex, deterministic long-only construction alternatives with checked outputs."""

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import minimize

from src.portfolio.construction.contracts import PositionBounds, SolverInfo

FEASIBILITY_TOLERANCE = 1e-8
EQUALITY_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Candidate:
    weights: np.ndarray | None
    solver: SolverInfo
    reason: str | None = None


def positive_definite(covariance: np.ndarray) -> bool:
    """Reject singular or relatively ill-conditioned matrices for strict convex solves."""
    values = np.linalg.eigvalsh(covariance)
    return bool(values[0] > 1e-12 * max(float(values[-1]), np.finfo(float).tiny))


def violations(weights: np.ndarray, bounds: PositionBounds) -> list[str]:
    failures = []
    if not np.isfinite(weights).all():
        return ["Nonfinite portfolio weights"]
    if abs(float(weights.sum()) - 1) > FEASIBILITY_TOLERANCE:
        failures.append("Weights do not sum to one")
    for i, weight in enumerate(weights):
        if weight < bounds.min_position_weight - FEASIBILITY_TOLERANCE:
            failures.append(f"Position {i + 1} is below minimum position weight")
        if weight > bounds.max_position_weight + FEASIBILITY_TOLERANCE:
            failures.append(f"Position {i + 1} is above maximum position weight")
    return failures


def extreme_linear(coefficients: np.ndarray, bounds: PositionBounds) -> np.ndarray:
    """Exact bounded-simplex linear maximizer by descending coefficient order."""
    weights = np.full(len(coefficients), bounds.min_position_weight, dtype=float)
    remaining = 1 - float(weights.sum())
    for i in np.argsort(-coefficients, kind="stable"):
        addition = min(remaining, bounds.max_position_weight - weights[i])
        weights[i] += addition
        remaining -= addition
    return weights


def unavailable(method: str, reason: str, solver: SolverInfo | None = None) -> Candidate:
    return Candidate(
        None,
        solver or SolverInfo(method=method, converged=False, iterations=0, diagnostic=reason),
        reason,
    )


def information(method: str, result: Any, objective: float | None = None) -> SolverInfo:
    return SolverInfo(
        method=method,
        converged=bool(result.success),
        iterations=int(getattr(result, "nit", 0)),
        objective=objective if objective is not None and np.isfinite(objective) else None,
        diagnostic=str(result.message),
    )


def clean_weights(weights: np.ndarray) -> np.ndarray:
    """Remove only feasibility-roundoff outside [0, 1], then restore unit sum."""
    weights = np.clip(weights, 0, 1)
    return np.asarray(weights / weights.sum(), dtype=float)


def minimum_variance(covariance: np.ndarray, bounds: PositionBounds) -> Candidate:
    method = "SLSQP convex minimum variance with analytical gradient"
    n = len(covariance)
    scale = float(np.max(np.abs(covariance)))
    if (
        scale == 0
        or n == 1
        or bounds.min_position_weight * n == 1
        or bounds.max_position_weight * n == 1
    ):
        weights = np.full(n, 1 / n)
        return Candidate(
            weights,
            SolverInfo(
                method="Analytical constant objective or unique feasible weights",
                converged=True,
                iterations=0,
                objective=float(weights @ covariance @ weights),
                diagnostic="Global minimum; uniqueness is not asserted for singular covariance",
            ),
        )
    matrix = covariance / scale
    try:
        result = minimize(
            lambda w: float(w @ matrix @ w),
            np.full(n, 1 / n),
            jac=lambda w: 2 * matrix @ w,
            method="SLSQP",
            bounds=[(bounds.min_position_weight, bounds.max_position_weight)] * n,
            constraints={
                "type": "eq",
                "fun": lambda w: float(w.sum() - 1),
                "jac": lambda w: np.ones(n),
            },
            options={"ftol": 1e-12, "maxiter": 2000},
        )
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        return unavailable(method, f"Numerical solver failure: {exc}")
    raw = np.asarray(result.x, dtype=float)
    info = information(method, result)
    if not result.success or raw.shape != (n,) or violations(raw, bounds):
        return unavailable(method, "Solver did not converge to feasible finite weights", info)
    weights = clean_weights(raw)
    gradient = 2 * matrix @ weights
    best_linear = extreme_linear(-gradient, bounds)
    # Convex first-order gap: upper bound on scaled objective suboptimality.
    gap = float(gradient @ (weights - best_linear))
    if gap > 1e-7 or violations(weights, bounds):
        return unavailable(method, "Minimum-variance optimality or feasibility check failed", info)
    return Candidate(weights, information(method, result, float(weights @ covariance @ weights)))


def maximum_sharpe(
    covariance: np.ndarray,
    excess: np.ndarray,
    bounds: PositionBounds,
) -> Candidate:
    method = "SLSQP convex positive-excess Sharpe transformation with analytical gradient"
    if not positive_definite(covariance):
        return unavailable(
            method, "Positive-definite covariance required; singular/arbitrage cases unsupported"
        )
    max_weights = extreme_linear(excess, bounds)
    if float(max_weights @ excess) <= 0:
        return unavailable(method, "No feasible portfolio has positive expected excess return")
    n = len(excess)
    matrix = covariance / float(np.max(np.abs(covariance)))
    # Positive scaling preserves the optimizer and avoids large transformed weights.
    means = excess / float(np.max(np.abs(excess)))
    inequality = np.vstack(
        [
            np.eye(n) - bounds.min_position_weight * np.ones((n, n)),
            bounds.max_position_weight * np.ones((n, n)) - np.eye(n),
        ]
    )
    try:
        result = minimize(
            lambda y: float(y @ matrix @ y),
            max_weights / float(means @ max_weights),
            jac=lambda y: 2 * matrix @ y,
            method="SLSQP",
            bounds=[(0, None)] * n,
            constraints=[
                {"type": "eq", "fun": lambda y: float(means @ y - 1), "jac": lambda y: means},
                {"type": "ineq", "fun": lambda y: inequality @ y, "jac": lambda y: inequality},
            ],
            options={"ftol": 1e-12, "maxiter": 2000},
        )
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        return unavailable(method, f"Numerical solver failure: {exc}")
    y = np.asarray(result.x, dtype=float)
    info = information(method, result)
    if (
        not result.success
        or y.shape != (n,)
        or not np.isfinite(y).all()
        or float(y.sum()) <= 0
        or abs(float(means @ y) - 1) > FEASIBILITY_TOLERANCE
        or np.any(inequality @ y < -FEASIBILITY_TOLERANCE)
    ):
        return unavailable(
            method, "Solver did not converge to a feasible Sharpe transformation", info
        )
    raw = y / y.sum()
    if violations(raw, bounds):
        return unavailable(method, "Transformed Sharpe weights violate bounds", info)
    weights = clean_weights(raw)
    variance = float(weights @ matrix @ weights)
    mean = float(weights @ means)
    # First-order test for the convex equivalent on the simplex: minimum
    # variance / squared positive excess. Positive excess excludes the other branch.
    gradient = 2 * (matrix @ weights - variance / mean * means)
    gap = float(gradient @ (weights - extreme_linear(-gradient, bounds)))
    if gap > 1e-7 or violations(weights, bounds):
        return unavailable(method, "Maximum-Sharpe optimality or feasibility check failed", info)
    sharpe = float(weights @ excess / np.sqrt(weights @ covariance @ weights))
    return Candidate(weights, information(method, result, sharpe))


def risk_parity(covariance: np.ndarray, bounds: PositionBounds) -> Candidate:
    method = "L-BFGS-B convex equal risk budget with analytical gradient"
    if not positive_definite(covariance):
        return unavailable(
            method, "Positive-definite covariance required for equal risk contribution"
        )
    n = len(covariance)
    matrix = covariance / float(np.max(np.abs(covariance)))
    try:
        result = minimize(
            lambda x: float(0.5 * x @ matrix @ x - np.log(x).sum() / n),
            1 / np.sqrt(n * np.diag(matrix)),
            jac=lambda x: matrix @ x - 1 / (n * x),
            method="L-BFGS-B",
            bounds=[(np.finfo(float).eps, None)] * n,
            options={"ftol": 1e-15, "gtol": 1e-10, "maxiter": 2000, "maxls": 100},
        )
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        return unavailable(method, f"Numerical solver failure: {exc}")
    x = np.asarray(result.x, dtype=float)
    info = information(method, result)
    if not result.success or x.shape != (n,) or not np.isfinite(x).all() or np.any(x <= 0):
        return unavailable(
            method, "Solver did not converge to finite positive equal-risk weights", info
        )
    weights = x / x.sum()
    components = weights * (matrix @ weights)
    percentages = components / components.sum()
    if not np.allclose(percentages, 1 / n, atol=EQUALITY_TOLERANCE, rtol=0):
        return unavailable(method, "Solver result does not satisfy equal risk contribution", info)
    if violations(weights, bounds):
        return unavailable(
            method, "Equal risk contribution solution violates requested position bounds", info
        )
    return Candidate(
        weights, information(method, result, float(np.max(np.abs(percentages - 1 / n))))
    )
