"""Offline analytical construction cases with exactly known covariance."""

from datetime import UTC, date, datetime, timedelta
from importlib import import_module
from typing import Any
from uuid import UUID

import numpy as np
import pytest
from src.portfolio.construction.contracts import ConstructionRequest, StrategyResult


def request_for(
    covariance: np.ndarray | None = None,
    views: tuple[float | None, ...] = (0.08, 0.12),
    weights: tuple[float, ...] = (0.5, 0.5),
    **overrides: Any,
) -> ConstructionRequest:
    covariance = np.diag([0.04, 0.16]) if covariance is None else covariance
    n = len(covariance)
    eigenvalues, vectors = np.linalg.eigh(covariance)
    factor = vectors * np.sqrt(np.maximum(eigenvalues, 0))
    rows = np.vstack([factor.T, -factor.T]) * np.sqrt((2 * n - 1) / (2 * 252))
    ids = [UUID(int=i + 1) for i in range(n)]
    cutoff = datetime(2026, 9, 10, tzinfo=UTC)
    start = date(2026, 1, 1)
    context = {
        "valuation_date": cutoff.date(),
        "horizon_years": 1,
        "return_basis": "total",
        "money_basis": "nominal",
        "currency_basis": "local",
        "valuation_currency": "USD",
        "local_currency": "USD",
        "valuation_calendar": "XNYS; 16:00 New York",
        "as_of": cutoff,
        "known_at": cutoff,
    }
    payload = {
        "assets": [
            {
                "security_id": identifier,
                "current_weight": weights[i],
                "investor_view": None
                if views[i] is None
                else {
                    "context": {**context, "security_id": identifier},
                    "annualized_return": str(views[i]),
                    "rationale": "Explicit analytical test view",
                },
            }
            for i, identifier in enumerate(ids)
        ],
        "history": {
            "security_ids": ids,
            "observations": [
                {
                    "start": start + timedelta(days=i),
                    "end": start + timedelta(days=i + 1),
                    "returns": row.tolist(),
                }
                for i, row in enumerate(rows)
            ],
            "frequency": "daily",
            "periods_per_year": 252,
            "source": "Analytical fixture",
            "retrieved_at": cutoff,
            "adjustment_policy": "Supplied nominal total returns",
            "interval_alignment": "identical_start_end_and_valuation_cutoff",
        },
        "valuation_date": cutoff.date(),
        "currency": "USD",
        "valuation_calendar": context["valuation_calendar"],
        "as_of": cutoff,
        "known_at": cutoff,
        "risk_free_rate": 0.02,
        "covariance_estimator": "sample",
        **overrides,
    }
    return ConstructionRequest.model_validate(payload)


def calculate(request: ConstructionRequest) -> dict[str, StrategyResult]:
    module = import_module("src.portfolio.construction.analytics")
    return {item.strategy: item for item in module.construct(request).comparisons}


def test_diagonal_analytical_minimum_variance_erc_and_tangency() -> None:
    results = calculate(request_for())
    for name in ("minimum_variance", "risk_parity", "maximum_sharpe"):
        assert results[name].status == "available", results[name].reason
        assert results[name].constraints_satisfied
        solver = results[name].solver
        assert solver is not None and solver.converged
    assert results["minimum_variance"].weights == pytest.approx([0.8, 0.2], abs=1e-6)
    assert results["risk_parity"].weights == pytest.approx([2 / 3, 1 / 3], abs=1e-6)
    # Normalized inverse covariance times excess means: (1.5, 0.625).
    assert results["maximum_sharpe"].weights == pytest.approx([12 / 17, 5 / 17], abs=1e-6)


def test_expected_return_and_euler_contributions_reconcile() -> None:
    report = calculate(request_for(weights=(0.8, 0.2)))["current"].report
    assert report is not None
    assert report.expected_portfolio_return.value == pytest.approx(0.088)
    assert report.expected_excess_return.value == pytest.approx(0.068)
    assert report.current_covariance_volatility == pytest.approx(np.sqrt(0.032))
    assert report.expected_sharpe_ratio.value == pytest.approx(0.068 / np.sqrt(0.032))
    assert sum(a.component_risk_contribution for a in report.assets) == pytest.approx(
        report.current_covariance_volatility, abs=1e-12
    )
    assert sum(a.expected_return_contribution.value or 0 for a in report.assets) == pytest.approx(
        report.expected_portfolio_return.value
    )
    assert report.weight_concentration_hhi == pytest.approx(0.68)
    assert report.effective_number_of_positions == pytest.approx(1 / 0.68)


def test_negative_risk_contributions_are_preserved_and_absolute_hhi_is_distinct() -> None:
    covariance = np.array([[0.04, -0.06], [-0.06, 0.16]])
    report = calculate(request_for(covariance, weights=(0.8, 0.2)))["current"].report
    assert report is not None
    components = np.array([a.component_risk_contribution for a in report.assets])
    assert components[1] < 0
    percentage = report.assets[1].percentage_risk_contribution.value
    assert percentage is not None and percentage < 0
    assert components.sum() == pytest.approx(report.current_covariance_volatility)
    shares = np.abs(components) / np.abs(components).sum()
    assert report.absolute_risk_concentration_hhi.value == pytest.approx(shares @ shares)


def test_missing_view_does_not_impute_even_at_zero_weight() -> None:
    results = calculate(request_for(views=(0.08, None), weights=(1, 0)))
    report = results["current"].report
    assert report is not None
    assert report.expected_portfolio_return.value is None
    assert report.expected_portfolio_return.reason == "missing_investor_view"
    assert report.expected_excess_return.value is None
    assert report.expected_sharpe_ratio.value is None
    assert report.assets[0].expected_return_contribution.value == pytest.approx(0.08)
    assert report.assets[1].expected_return_contribution.value is None
    assert results["maximum_sharpe"].status == "unavailable"
    assert results["minimum_variance"].status == "available"


def test_constraints_preserve_reference_weights_and_bound_minimum_variance() -> None:
    results = calculate(
        request_for(
            weights=(0.9, 0.1), constraints={"min_position_weight": 0.2, "max_position_weight": 0.6}
        )
    )
    assert results["current"].weights == [0.9, 0.1]
    assert results["current"].constraints_satisfied is False
    assert results["current"].constraint_violations
    assert results["minimum_variance"].weights == pytest.approx([0.6, 0.4], abs=1e-6)
    assert results["risk_parity"].status == "unavailable"
    assert "bound" in str(results["risk_parity"].reason).lower()


def test_sample_covariance_and_correlation_provenance() -> None:
    request = request_for()
    result = import_module("src.portfolio.construction.analytics").construct(request)
    report = result.covariance
    np.testing.assert_allclose(report.annualized_simple_return_covariance, np.diag([0.04, 0.16]))
    np.testing.assert_allclose(report.correlation, np.eye(2))
    assert report.estimator == "sample"
    assert report.shrinkage == 0
    assert report.positive_definite
    assert report.observation_count == 4
    assert report.window_start == request.history.observations[0].start
    assert report.periods_per_year == 252


def test_expected_excess_zero_has_zero_sharpe() -> None:
    report = calculate(request_for(views=(0.02, 0.02)))["current"].report
    assert report is not None
    assert report.expected_sharpe_ratio.value == pytest.approx(0)


def test_single_asset_and_forced_equal_bounds() -> None:
    result = calculate(request_for(np.array([[0.04]]), views=(0.08,), weights=(1,)))
    for item in result.values():
        assert item.status == "available", item.reason
        assert item.weights == [1]
    forced = calculate(request_for(constraints={"min_position_weight": 0.5}))
    assert forced["minimum_variance"].weights == [0.5, 0.5]
    assert forced["maximum_sharpe"].weights == [0.5, 0.5]
    assert forced["risk_parity"].status == "unavailable"


def test_binding_nonnegative_weights_allow_a_corner_optimum() -> None:
    covariance = np.array([[0.04, 0.08], [0.08, 0.25]])
    result = calculate(request_for(covariance, views=(0.20, 0.03)))
    assert result["minimum_variance"].weights == pytest.approx([1, 0], abs=1e-7)
    assert result["maximum_sharpe"].weights == pytest.approx([1, 0], abs=1e-7)


def test_shrinkage_is_reported_without_turning_history_into_a_view() -> None:
    result = import_module("src.portfolio.construction.analytics").construct(
        request_for(views=(None, None), covariance_estimator="ledoit_wolf")
    )
    assert result.covariance.estimator == "ledoit_wolf"
    # Population diagonal = (.03, .12), mu = .075. Fourth-moment beta =
    # .0019125; delta = .002025, so shrinkage = beta/delta = 17/18.
    assert result.covariance.shrinkage == pytest.approx(17 / 18)
    np.testing.assert_allclose(
        result.covariance.annualized_simple_return_covariance, np.diag([0.0725, 0.0775]), atol=1e-12
    )
    for item in result.comparisons:
        if item.report is not None:
            assert item.report.expected_portfolio_return.value is None


def test_correlated_equal_risk_solution_and_scale_invariance() -> None:
    covariance = np.array([[0.04, 0.03], [0.03, 0.16]])
    first = calculate(request_for(covariance))
    scaled = calculate(request_for(covariance * 0.0001))
    # Two-asset ERC has inverse volatility weights even with nonzero correlation.
    assert first["risk_parity"].weights == pytest.approx([2 / 3, 1 / 3], abs=1e-6)
    for strategy in ("minimum_variance", "maximum_sharpe", "risk_parity"):
        assert first[strategy].weights is not None
        assert scaled[strategy].weights == pytest.approx(first[strategy].weights, abs=1e-6)


def test_zero_variance_security_only_has_undefined_own_correlations() -> None:
    result = import_module("src.portfolio.construction.analytics").construct(
        request_for(np.diag([0, 0.16]))
    )
    assert result.covariance.correlation[0] == [None, None]
    assert result.covariance.correlation[1][0] is None
    assert result.covariance.correlation[1][1] == pytest.approx(1)
    minimum = next(item for item in result.comparisons if item.strategy == "minimum_variance")
    assert minimum.weights == pytest.approx([1, 0], abs=1e-8)
