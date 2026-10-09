"""Financial domain rejection, uncertainty and numerical edge cases."""

from typing import Any
from uuid import uuid4

import pytest
from src.valuation.arithmetic import finite, from_annualized, from_cumulative
from src.valuation.contracts import (
    CapmRequest,
    FundamentalRequest,
    HistoricalRequest,
    Metric,
    ReturnPair,
    ReturnSample,
    ScenarioSetRequest,
    Uncertainty,
)
from src.valuation.models import fundamental
from src.valuation.service import code_identity
from src.views.expected_return import capm, historical

from tests.test_valuation_contracts import context
from tests.test_valuation_models import assumptions, sample


@pytest.mark.parametrize(
    "function,args",
    [
        (finite, [float("inf")]),
        (from_annualized, [1e300, 100]),
        (from_annualized, [-2, 1]),
        (from_cumulative, [-2, 1]),
        (from_cumulative, [1, 0]),
        (from_cumulative, [1e300, 0.001]),
    ],
)
def test_unrepresentable_returns_fail_explicitly(function: Any, args: list) -> None:
    with pytest.raises(ValueError, match="numerical"):
        function(*args)


def test_return_pair_overflow_and_complete_loss_conversion() -> None:
    with pytest.raises(ValueError, match="numerical"):
        ReturnPair(annualized_return=1e300, cumulative_return=1, horizon_years=100)
    assert from_cumulative(-1, 2).annualized_return == -1
    with pytest.raises(ValueError):
        context(observation_ids=[uuid4()] * 2)


@pytest.mark.parametrize(
    "payload",
    [
        {"lower_annualized": 0.1},
        {"upper_annualized": 0.1},
        {"lower_annualized": 0.2, "upper_annualized": 0.1},
    ],
)
def test_uncertainty_requires_ordered_pair(payload: dict) -> None:
    with pytest.raises(ValueError):
        Uncertainty(**payload)


def test_defined_metric_and_user_uncertainty_contract() -> None:
    with pytest.raises(ValueError):
        Metric(value=None)
    with pytest.raises(ValueError):
        Metric(value=0, reason="unavailable")
    assert Uncertainty(lower_annualized=-0.2, upper_annualized=0.3).upper_annualized == 0.3


@pytest.mark.parametrize(
    "updates",
    [
        {"periods_per_year": 252},
        {"frequency": "daily", "periods_per_year": 12},
        {"observations": [{"start": "2020-01-01", "end": "2020-01-01", "security_return": 0}]},
        {"observations": [{"start": "2020-01-01", "end": "2020-01-31", "security_return": 0}] * 2},
    ],
)
def test_samples_reject_incoherent_frequencies_and_intervals(updates: dict) -> None:
    with pytest.raises(ValueError):
        sample([0], **updates)


@pytest.mark.parametrize(
    "updates",
    [
        {"scenarios": [{"name": "base", "assumptions": assumptions()}] * 3},
        {"probability_source": "Owner"},
        {"probability_type": "user_assumption"},
    ],
)
def test_scenario_probability_metadata_cannot_be_invented(updates: dict) -> None:
    rows = [{"name": name, "assumptions": assumptions()} for name in ("bear", "base", "bull")]
    with pytest.raises(ValueError):
        ScenarioSetRequest.model_validate({"context": context(), "scenarios": rows, **updates})


def test_scenario_anchor_and_probability_source_validation() -> None:
    rows = [
        {"name": name, "assumptions": assumptions(), "probability": p}
        for name, p in zip(("bear", "base", "bull"), [0.2, 0.6, 0.2], strict=True)
    ]
    with pytest.raises(ValueError, match="source"):
        ScenarioSetRequest.model_validate({"context": context(), "scenarios": rows})
    rows[1]["assumptions"] = assumptions(current_price=99)
    with pytest.raises(ValueError, match="anchor"):
        ScenarioSetRequest.model_validate(
            {
                "context": context(),
                "scenarios": rows,
                "probability_source": "Owner",
                "probability_type": "user_assumption",
            }
        )


@pytest.mark.parametrize(
    "ctx,changes",
    [
        ({"money_basis": "real"}, {}),
        ({}, {"price_observed_at": "2026-09-08T10:00:00Z"}),
        ({}, {"price_observed_at": "2026-09-09T13:00:00Z"}),
        ({}, {"terminal_fx_base_per_local": 2}),
        ({"horizon_years": 100}, {"annual_per_share_growth": -0.999999999999999}),
        ({}, {"terminal_multiple": 1e-308, "current_fundamental_per_share": 1e-308}),
        (
            {"currency_basis": "base", "valuation_currency": "EUR"},
            {
                "current_price": 1e-308,
                "spot_fx_base_per_local": 1e-308,
                "terminal_fx_base_per_local": 1,
            },
        ),
    ],
)
def test_fundamental_unsupported_and_numerical_domains(ctx: dict, changes: dict) -> None:
    with pytest.raises(ValueError):
        fundamental(FundamentalRequest(context=context(**ctx), assumptions=assumptions(**changes)))


@pytest.mark.parametrize(
    "ctx,changes",
    [
        ({"money_basis": "real"}, {}),
        ({"valuation_date": "2019-01-01", "as_of": "2019-01-01T00:00:00Z"}, {}),
        ({"known_at": "2020-01-01T00:00:00Z"}, {}),
        ({}, {"retrieved_at": "2019-01-01T00:00:00Z"}),
    ],
)
def test_historical_availability_and_currency(ctx: dict, changes: dict) -> None:
    with pytest.raises(ValueError):
        historical(HistoricalRequest(context=context(**ctx), sample=sample([0.1], **changes)))


def test_capm_insufficient_data_missing_benchmark_price_basis_and_impossible_return() -> None:
    payload: dict[str, Any] = {
        "context": context(),
        "sample": sample([0.01, 0.02], [0.02, 0.04]),
        "benchmark": "Synthetic",
        "risk_free_rate": 0.03,
        "equity_risk_premium": 0.05,
        "assumption_source": "Owner",
        "horizon_assumption": "iid_annual_gross_mean",
    }
    result = capm(CapmRequest.model_validate(payload))
    assert result.returns is None and result.undefined_reason == "insufficient_observations"
    for update in (
        {"sample": sample([0.01, 0.02, 0.03])},
        {"context": context(return_basis="price")},
    ):
        with pytest.raises(ValueError):
            capm(CapmRequest.model_validate({**payload, **update}))
    result = capm(
        CapmRequest.model_validate(
            {
                **payload,
                "sample": sample([0.02, 0.04, 0.06], [0.01, 0.02, 0.03]),
                "equity_risk_premium": -2,
            }
        )
    )
    assert result.returns is None and result.undefined_reason == "capm_return_below_minus_one"


def test_manifest_without_git_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*args: Any, **kwargs: Any) -> None:
        raise OSError("Git not installed in container")

    monkeypatch.setattr("src.valuation.service.subprocess.run", unavailable)
    digest, sha, dirty = code_identity()
    assert len(digest) == 64 and sha is None and dirty is None


def test_valid_frequency_boundaries_and_nonzero_regression_error() -> None:
    payload = sample([0.01, 0.04, 0.02], [0.01, 0.02, 0.03]).model_dump()
    for frequency, periods, days in (("daily", 252, 1), ("weekly", 52, 7), ("annual", 1, 365)):
        from datetime import date, timedelta

        start = date(2020, 1, 1)
        rows = [
            {
                "start": start + timedelta(days=i * days),
                "end": start + timedelta(days=(i + 1) * days),
                "security_return": 0.01,
            }
            for i in range(3)
        ]
        ReturnSample.model_validate(
            {**payload, "observations": rows, "frequency": frequency, "periods_per_year": periods}
        )
    result = capm(
        CapmRequest.model_validate(
            {
                "context": context(),
                "sample": payload,
                "benchmark": "Synthetic",
                "risk_free_rate": 0,
                "equity_risk_premium": 0.05,
                "assumption_source": "Owner",
                "horizon_assumption": "iid_annual_gross_mean",
            }
        )
    )
    assert result.regression is not None
    assert result.regression.beta.value == pytest.approx(0.5)
    assert result.regression.r_squared.value == pytest.approx(3 / 28)
    assert result.regression.beta_standard_error.value == pytest.approx(1.4433756729740645)
