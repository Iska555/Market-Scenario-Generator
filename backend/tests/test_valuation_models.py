"""Known-answer and failure tests for every Phase 5 financial function."""

from datetime import date, timedelta
from typing import Any

import numpy as np
import pytest
from src.valuation.contracts import (
    CapmRequest,
    FundamentalRequest,
    HistoricalRequest,
    ResearchAssumptionSet,
    ReturnPair,
    ReturnSample,
    ReverseRequest,
    ScenarioInput,
    ScenarioSetRequest,
)
from src.valuation.models import fundamental, reverse, scenario_set
from src.views.expected_return import capm, historical

from tests.test_valuation_contracts import context


def assumptions(**updates: Any) -> ResearchAssumptionSet:
    return ResearchAssumptionSet.model_validate(
        {
            "metric": "eps",
            "current_price": 100,
            "current_fundamental_per_share": 5,
            "annual_per_share_growth": 0.1,
            "terminal_multiple": 20,
            "annual_cash_dividend": 2,
            "rationale": "Synthetic assumption",
            "price_source": "Synthetic owner input",
            "price_observed_at": "2026-09-09T10:00:00Z",
            **updates,
        }
    )


def sample(y: list[float], x: list[float] | None = None, **updates: Any) -> ReturnSample:
    start = date(2020, 1, 1)
    return ReturnSample.model_validate(
        {
            "observations": [
                {
                    "start": start + timedelta(days=i * 30),
                    "end": start + timedelta(days=(i + 1) * 30),
                    "security_return": value,
                    "benchmark_return": x[i] if x else None,
                }
                for i, value in enumerate(y)
            ],
            "frequency": "monthly",
            "periods_per_year": 12,
            "source": "Synthetic",
            "retrieved_at": "2026-09-09T10:00:00Z",
            "adjustment_policy": "total simple returns",
            "interval_alignment": "identical_start_end_and_valuation_cutoff",
            **updates,
        }
    )


def test_fundamental_exact_wealth_identity_and_reverse() -> None:
    request = FundamentalRequest(context=context(), assumptions=assumptions())
    result = fundamental(request)
    assert result.terminal_fundamental_per_share == pytest.approx(6.655)
    assert result.terminal_price_local == pytest.approx(133.1)
    assert result.cash_dividends_local == 6
    assert result.returns.cumulative_return == pytest.approx(0.391)
    assert (
        result.growth_factor
        * result.multiple_factor
        * result.dividend_wealth_factor
        * result.fx_factor
    ) == pytest.approx(1.391)
    inverse = reverse(
        ReverseRequest(
            context=request.context,
            assumptions=assumptions(terminal_multiple=99),
            required_annualized_return=result.returns.annualized_return,
        )
    )
    assert inverse.required_terminal_multiple.value == pytest.approx(20)


def test_price_basis_and_explicit_fx() -> None:
    result = fundamental(
        FundamentalRequest(context=context(return_basis="price"), assumptions=assumptions())
    )
    assert result.cash_dividends_local == 0
    assert result.returns.annualized_return == pytest.approx(0.1)
    result = fundamental(
        FundamentalRequest(
            context=context(currency_basis="base", valuation_currency="EUR"),
            assumptions=assumptions(spot_fx_base_per_local=0.9, terminal_fx_base_per_local=0.81),
        )
    )
    assert result.returns.cumulative_return == pytest.approx(1.391 * 0.9 - 1)


@pytest.mark.parametrize(
    "changes",
    [
        {"current_fundamental_per_share": 0},
        {"terminal_multiple": -1},
        {"annual_per_share_growth": -1},
        {"current_price": float("inf")},
    ],
)
def test_invalid_fundamental_domains(changes: dict) -> None:
    with pytest.raises(ValueError):
        assumptions(**changes)


def test_reverse_impossible_and_numeric_overflow() -> None:
    result = reverse(
        ReverseRequest(
            context=context(),
            assumptions=assumptions(annual_cash_dividend=100),
            required_annualized_return=0,
        )
    )
    assert result.required_terminal_multiple.value is None
    assert result.required_terminal_multiple.reason == "nonpositive_required_terminal_price"
    with pytest.raises(ValueError, match="numerical"):
        fundamental(
            FundamentalRequest(
                context=context(horizon_years=100),
                assumptions=assumptions(annual_per_share_growth=1e100),
            )
        )
    with pytest.raises(ValueError):
        ReturnPair(annualized_return=0.1, cumulative_return=0.1, horizon_years=3)


def test_probabilities_absent_and_weighted_terminal_wealth() -> None:
    rows = [
        {"name": name, "assumptions": assumptions(annual_per_share_growth=growth)}
        for name, growth in (("bear", -0.1), ("base", 0), ("bull", 0.1))
    ]
    unweighted = scenario_set(
        ScenarioSetRequest(
            context=context(), scenarios=[ScenarioInput.model_validate(row) for row in rows]
        )
    )
    assert unweighted.probability_weighted_return is None
    weighted = scenario_set(
        ScenarioSetRequest(
            context=context(),
            scenarios=[
                ScenarioInput.model_validate({**row, "probability": p})
                for row, p in zip(rows, [0.2, 0.6, 0.2], strict=True)
            ],
            probability_source="Owner",
            probability_type="user_assumption",
        )
    )
    expected = 0.2 * (0.9**3 + 0.06) + 0.6 * 1.06 + 0.2 * (1.1**3 + 0.06) - 1
    assert weighted.probability_weighted_return is not None
    assert weighted.probability_weighted_return.cumulative_return == pytest.approx(expected)
    assert weighted.probability_weighted_return.annualized_return == pytest.approx(
        (1 + expected) ** (1 / 3) - 1
    )
    for probabilities in ([0.2, None, 0.8], [0.2, 0.5, 0.2]):
        with pytest.raises(ValueError):
            ScenarioSetRequest(
                context=context(),
                scenarios=[
                    ScenarioInput.model_validate({**row, "probability": p})
                    for row, p in zip(rows, probabilities, strict=True)
                ],
            )


def test_historical_mean_and_iid_uncertainty() -> None:
    values = [-0.02, 0.01, 0.03, 0.04]
    result = historical(HistoricalRequest(context=context(), sample=sample(values)))
    assert result.annualized_arithmetic_mean.value == pytest.approx(0.18)
    assert result.annualized_mean_standard_error.value == pytest.approx(
        12 * np.std(values, ddof=1) / 2
    )
    assert result.label == "Historical estimate — not a forward forecast"
    single = historical(HistoricalRequest(context=context(), sample=sample([0.01])))
    assert single.annualized_mean_standard_error.reason == "insufficient_observations"


@pytest.mark.parametrize("beta", [0, 1.2, -1])
def test_capm_analytical_beta_and_expected_return(beta: float) -> None:
    x = [-0.05, -0.02, 0.01, 0.03, 0.06]
    rf_period = 1.03 ** (1 / 12) - 1
    y = [rf_period + beta * (value - rf_period) for value in x]
    result = capm(
        CapmRequest(
            context=context(),
            sample=sample(y, x),
            benchmark="SYNTH",
            risk_free_rate=0.03,
            equity_risk_premium=0.05,
            assumption_source="Owner",
            horizon_assumption="iid_annual_gross_mean",
        )
    )
    assert result.kind == "model_estimate"
    assert result.regression is not None and result.returns is not None
    assert result.regression.beta.value == pytest.approx(beta, abs=1e-12)
    assert result.returns.annualized_return == pytest.approx(0.03 + beta * 0.05)
    assert result.regression.beta_standard_error.value == pytest.approx(0, abs=1e-12)
    if beta == 0:
        assert result.regression.r_squared.reason == "zero_security_variance"
    else:
        assert result.regression.r_squared.value == pytest.approx(1)


def test_capm_undefined_variance() -> None:
    result = capm(
        CapmRequest(
            context=context(),
            sample=sample([0.01, 0.02, 0.03], [0.01] * 3),
            benchmark="Constant",
            risk_free_rate=0.03,
            equity_risk_premium=0.05,
            assumption_source="Owner",
            horizon_assumption="iid_annual_gross_mean",
        )
    )
    assert result.returns is None
    assert result.regression is not None
    assert result.regression.beta.reason == "zero_benchmark_variance"


def test_cross_currency_fx_cannot_be_omitted() -> None:
    with pytest.raises(ValueError, match="explicitly supplied"):
        fundamental(
            FundamentalRequest(
                context=context(currency_basis="base", valuation_currency="EUR"),
                assumptions=assumptions(),
            )
        )


def test_sample_cannot_mislabel_annual_intervals_as_monthly() -> None:
    with pytest.raises(ValueError, match="duration"):
        sample(
            [0.1, 0.2, 0.3],
            observations=[
                {"start": f"{2020 + i}-01-01", "end": f"{2021 + i}-01-01", "security_return": r}
                for i, r in enumerate([0.1, 0.2, 0.3])
            ],
        )


def test_reverse_underflow_never_returns_defined_zero_multiple() -> None:
    result = reverse(
        ReverseRequest(
            context=context(horizon_years=1),
            assumptions=assumptions(
                current_price=1e-308,
                current_fundamental_per_share=1e308,
                annual_per_share_growth=0,
                annual_cash_dividend=0,
            ),
            required_annualized_return=0,
        )
    )
    assert result.required_terminal_multiple.value is None
    assert result.required_terminal_multiple.reason == "numerical_underflow"


def test_positive_wealth_cannot_become_complete_loss_through_rounding() -> None:
    with pytest.raises(ValueError, match="numerical"):
        fundamental(
            FundamentalRequest(
                context=context(horizon_years=1),
                assumptions=assumptions(
                    current_price=1,
                    current_fundamental_per_share=1e-20,
                    terminal_multiple=1,
                    annual_cash_dividend=0,
                    annual_per_share_growth=0,
                ),
            )
        )
