"""Pure supplied-data portfolio construction; no provider, persistence or decisions."""

import math

import numpy as np

from src.portfolio.construction import algorithms
from src.portfolio.construction.contracts import (
    AssetContribution,
    ConstructionRequest,
    ConstructionResult,
    CovarianceReport,
    PortfolioRiskReport,
    StrategyResult,
)
from src.risk.covariance import estimate_covariance, psd_factor, risk_contributions
from src.valuation.contracts import Metric, UserViewRequest
from src.views.expected_return import user_view


def metric(value: float | None, reason: str) -> Metric:
    if value is not None and not math.isfinite(value):
        raise ValueError("Numerical result is not finite")
    return Metric(value=value, reason=reason if value is None else None)


def adopted_return(view: UserViewRequest | None) -> float | None:
    if view is None:
        return None
    returns = user_view(view).returns
    assert returns is not None  # Validated user-specified views always have a return pair.
    return returns.cumulative_return


def risk_report(
    request: ConstructionRequest,
    covariance: np.ndarray,
    weights: np.ndarray,
    views: list[float | None],
) -> PortfolioRiskReport:
    risk = risk_contributions(covariance, weights)
    missing = any(view is None for view in views)
    expected = (
        None
        if missing
        else math.fsum(
            float(weight) * view
            for weight, view in zip(weights, views, strict=True)
            if view is not None
        )
    )
    excess = None if expected is None else expected - request.risk_free_rate
    sharpe = None if excess is None or risk.volatility == 0 else excess / risk.volatility
    total_absolute = float(np.abs(risk.component).sum())
    risk_hhi = (
        None
        if total_absolute == 0
        else float(np.sum((np.abs(risk.component) / total_absolute) ** 2))
    )
    weight_hhi = float(weights @ weights)
    return PortfolioRiskReport(
        current_covariance_volatility=risk.volatility,
        expected_portfolio_return=metric(expected, "missing_investor_view"),
        expected_excess_return=metric(excess, "missing_investor_view"),
        expected_sharpe_ratio=metric(
            sharpe, "missing_investor_view" if missing else "zero_portfolio_volatility"
        ),
        weight_concentration_hhi=weight_hhi,
        effective_number_of_positions=1 / weight_hhi,
        absolute_risk_concentration_hhi=metric(risk_hhi, "zero_absolute_risk_contribution"),
        assets=[
            AssetContribution(
                security_id=asset.security_id,
                weight=float(weights[i]),
                annualized_asset_volatility=math.sqrt(float(covariance[i, i])),
                marginal_risk_contribution=metric(
                    None if risk.marginal is None else float(risk.marginal[i]),
                    "zero_portfolio_volatility",
                ),
                component_risk_contribution=float(risk.component[i]),
                percentage_risk_contribution=metric(
                    None if risk.percentage is None else float(risk.percentage[i]),
                    "zero_portfolio_volatility",
                ),
                expected_return_assumption=metric(view, "missing_investor_view"),
                expected_return_contribution=metric(
                    None if view is None else float(weights[i]) * view,
                    "missing_investor_view",
                ),
            )
            for i, (asset, view) in enumerate(zip(request.assets, views, strict=True))
        ],
    )


def construct(request: ConstructionRequest) -> ConstructionResult:
    history = request.history
    observations = np.array([row.returns for row in history.observations], dtype=float)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        estimate = estimate_covariance(observations, request.covariance_estimator)
        covariance = estimate.matrix * history.periods_per_year
    if not np.isfinite(covariance).all():
        raise ValueError("Numerical covariance is not finite")
    psd_factor(covariance)
    volatilities = np.sqrt(np.diag(covariance))
    correlation = [
        [
            None
            if volatilities[i] == 0 or volatilities[j] == 0
            else float(covariance[i, j] / volatilities[i] / volatilities[j])
            for j in range(len(covariance))
        ]
        for i in range(len(covariance))
    ]
    views = [adopted_return(asset.investor_view) for asset in request.assets]
    comparisons = []
    for strategy in request.strategies:
        solver = None
        if strategy == "current":
            weights = np.array([asset.current_weight for asset in request.assets])
        elif strategy == "equal_weight":
            weights = np.full(len(request.assets), 1 / len(request.assets))
        else:
            if strategy == "minimum_variance":
                candidate = algorithms.minimum_variance(covariance, request.constraints)
            elif strategy == "risk_parity":
                candidate = algorithms.risk_parity(covariance, request.constraints)
            elif any(view is None for view in views):
                candidate = algorithms.unavailable(
                    "Positive-excess Sharpe transformation", "missing_investor_view"
                )
            else:
                excess = np.array(views, dtype=float) - request.risk_free_rate
                candidate = algorithms.maximum_sharpe(covariance, excess, request.constraints)
            if candidate.weights is None:
                comparisons.append(
                    StrategyResult(
                        strategy=strategy,
                        status="unavailable",
                        reason=candidate.reason,
                        solver=candidate.solver,
                    )
                )
                continue
            weights, solver = candidate.weights, candidate.solver
        failures = algorithms.violations(weights, request.constraints)
        comparisons.append(
            StrategyResult(
                strategy=strategy,
                status="available",
                weights=weights.tolist(),
                report=risk_report(request, covariance, weights, views),
                constraints_satisfied=not failures,
                constraint_violations=failures,
                solver=solver,
            )
        )
    return ConstructionResult(
        currency=request.currency,
        valuation_date=request.valuation_date,
        covariance=CovarianceReport(
            annualized_simple_return_covariance=covariance.tolist(),
            correlation=correlation,
            estimator=request.covariance_estimator,
            shrinkage=estimate.shrinkage,
            periods_per_year=history.periods_per_year,
            frequency=history.frequency,
            observation_count=len(observations),
            window_start=history.observations[0].start,
            window_end=history.observations[-1].end,
            positive_definite=algorithms.positive_definite(covariance),
        ),
        comparisons=comparisons,
    )
