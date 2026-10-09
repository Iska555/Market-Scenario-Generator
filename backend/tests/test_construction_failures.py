"""Boundary and solver failure regressions: never report an invalid candidate."""

from importlib import import_module
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from tests.test_construction_quant import calculate, request_for


def test_zero_covariance_has_typed_undefined_ratios_and_correlations() -> None:
    request = request_for(np.zeros((2, 2)))
    result = import_module("src.portfolio.construction.analytics").construct(request)
    assert result.covariance.correlation == [[None, None], [None, None]]
    assert result.covariance.positive_definite is False
    items = {item.strategy: item for item in result.comparisons}
    report = items["current"].report
    assert report is not None
    assert report.current_covariance_volatility == 0
    assert report.expected_sharpe_ratio.reason == "zero_portfolio_volatility"
    assert report.absolute_risk_concentration_hhi.reason == "zero_absolute_risk_contribution"
    assert report.assets[0].marginal_risk_contribution.reason == "zero_portfolio_volatility"
    assert report.assets[0].component_risk_contribution == 0
    assert items["minimum_variance"].status == "available"
    assert items["maximum_sharpe"].status == "unavailable"
    assert items["risk_parity"].status == "unavailable"


def test_singular_covariance_allows_minimum_variance_only() -> None:
    results = calculate(request_for(np.array([[0.04, 0.04], [0.04, 0.04]])))
    assert results["minimum_variance"].status == "available"
    assert results["maximum_sharpe"].status == "unavailable"
    assert results["risk_parity"].status == "unavailable"


@pytest.mark.parametrize("views", [(0.01, 0.02), (-0.1, -0.2)])
def test_maximum_sharpe_requires_positive_feasible_excess(views: tuple[float, float]) -> None:
    result = calculate(request_for(views=views))["maximum_sharpe"]
    assert result.status == "unavailable"
    assert "positive" in str(result.reason)


def test_positive_asset_is_insufficient_if_bounds_preclude_positive_portfolio() -> None:
    result = calculate(
        request_for(
            views=(0.03, -0.9), constraints={"min_position_weight": 0.4, "max_position_weight": 0.6}
        )
    )["maximum_sharpe"]
    assert result.status == "unavailable"
    assert "positive" in str(result.reason)


@pytest.mark.parametrize(
    "bounds",
    [
        {"min_position_weight": 0.6},
        {"max_position_weight": 0.4},
        {"min_position_weight": 0.8, "max_position_weight": 0.2},
    ],
)
def test_infeasible_position_bounds_are_rejected(bounds: dict[str, float]) -> None:
    with pytest.raises(ValidationError, match=r"[Bb]ound|[Mm]inimum"):
        request_for(constraints=bounds)


@pytest.mark.parametrize(
    "success,x", [(False, [0.5, 0.5]), (True, [1.2, -0.2]), (True, [float("nan"), 0.5])]
)
def test_solver_failure_or_invalid_output_never_becomes_available(
    monkeypatch: pytest.MonkeyPatch, success: bool, x: list[float]
) -> None:
    module = import_module("src.portfolio.construction.algorithms")
    monkeypatch.setattr(
        module,
        "minimize",
        lambda *args, **kwargs: SimpleNamespace(
            success=success, x=np.array(x), nit=4, fun=0.1, message="Injected solver condition"
        ),
    )
    result = calculate(request_for())
    for name in ("minimum_variance", "maximum_sharpe", "risk_parity"):
        assert result[name].status == "unavailable"
        assert result[name].weights is None
        assert result[name].solver is not None


def test_covariance_numerical_overflow_is_rejected() -> None:
    request = request_for()
    payload = request.model_dump(mode="json")
    payload["history"]["observations"][0]["returns"] = [1e308, 1e308]
    request = type(request).model_validate(payload)
    with pytest.raises(ValueError, match=r"[Nn]umerical|[Ff]inite"):
        calculate(request)


def test_erc_solver_claiming_success_without_equal_risk_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("src.portfolio.construction.algorithms")
    monkeypatch.setattr(
        module,
        "minimize",
        lambda *args, **kwargs: SimpleNamespace(
            success=True, x=np.ones(2), nit=1, fun=0.1, message="Spurious success"
        ),
    )
    result = calculate(request_for())["risk_parity"]
    assert result.status == "unavailable"
    assert "equal" in str(result.reason)


def test_solver_exception_is_reported_for_each_alternative(monkeypatch: pytest.MonkeyPatch) -> None:
    module = import_module("src.portfolio.construction.algorithms")

    def numerical_failure(*args: object, **kwargs: object) -> None:
        raise np.linalg.LinAlgError("Injected numerical failure")

    monkeypatch.setattr(module, "minimize", numerical_failure)
    results = calculate(request_for())
    assert results["current"].status == "available"
    for strategy in ("minimum_variance", "maximum_sharpe", "risk_parity"):
        assert results[strategy].status == "unavailable"
        assert "Numerical solver failure" in str(results[strategy].reason)


@pytest.mark.parametrize(
    "strategy,solution",
    [
        ("minimum_variance", [0.5, 0.5]),
        ("maximum_sharpe", [0.625, 0.625]),
    ],
)
def test_feasible_but_nonoptimal_solver_success_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    strategy: str,
    solution: list[float],
) -> None:
    module = import_module("src.portfolio.construction.algorithms")
    monkeypatch.setattr(
        module,
        "minimize",
        lambda *args, **kwargs: SimpleNamespace(
            success=True, x=np.array(solution), nit=1, fun=0.1, message="Spurious optimality"
        ),
    )
    result = calculate(request_for())[strategy]
    assert result.status == "unavailable"
    assert "optimality" in str(result.reason)


def test_nonfinite_sharpe_is_rejected_as_a_numerical_failure() -> None:
    with pytest.raises(ValueError, match="Numerical result is not finite"):
        calculate(request_for(risk_free_rate=1e308, strategies=["current"]))
