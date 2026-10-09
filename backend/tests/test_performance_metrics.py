"""Analytical realized-performance fixtures independent of the implementation."""

from datetime import date, timedelta
from decimal import Decimal
from math import sqrt

import pytest
from pydantic import ValidationError
from src.performance.metrics import Metric, realized_statistics, xirr


def dates(count: int, start: date = date(2025, 1, 1)) -> list[date]:
    return [start + timedelta(days=i) for i in range(count)]


@pytest.mark.parametrize("final, expected", [("110", 0.1), ("75", -0.25), ("100", 0)])
def test_xirr_actual_365_days(final: str, expected: float) -> None:
    result = xirr([(date(2025, 1, 1), Decimal(-100)), (date(2026, 1, 1), Decimal(final))])
    assert result.value == pytest.approx(expected, abs=1e-12)
    assert result.reason is None
    assert result.observations == 2


def test_xirr_same_date_aggregation_and_scaling() -> None:
    for scale in [Decimal("1e-500"), Decimal(1), Decimal("1e500")]:
        result = xirr(
            [
                (date(2025, 1, 1), Decimal(-100) * scale),
                (date(2025, 1, 1), Decimal(-50) * scale),
                (date(2025, 1, 1), Decimal(50) * scale),
                (date(2026, 1, 1), Decimal(110) * scale),
            ]
        )
        assert result.value == pytest.approx(0.1, abs=1e-12)
        assert result.observations == 2
    assert (
        xirr([(date(2025, 1, 1), Decimal(-1)), (date(2025, 1, 1), Decimal(1))]).reason
        == "no_nonzero_cash_flows"
    )


def test_xirr_refuses_ambiguous_and_out_of_bounds_roots() -> None:
    assert xirr(list(zip(dates(3), map(Decimal, [-100, 230, -132]), strict=True))).reason == (
        "non_conventional_cash_flows"
    )
    assert xirr(list(zip(dates(2), map(Decimal, [-1, 10]), strict=True))).reason == (
        "root_outside_supported_bounds"
    )
    assert xirr([(date(2025, 1, 1), Decimal(10))]).reason == "cash_flows_need_both_signs"


def test_sharpe_uses_arithmetic_excess_and_sample_volatility() -> None:
    report = realized_statistics(dates(4), [-0.1, 0.1, -0.1, 0.1])
    assert report["sharpe"].value == pytest.approx(0)
    assert report["annualized_volatility"].value == pytest.approx(sqrt(0.04 / 3 * 365))
    assert report["sortino"].value == pytest.approx(0)
    assert report["hit_rate"].value == 0.5


def test_drawdown_includes_opening_peak_and_unrecovered_duration() -> None:
    report = realized_statistics(dates(3), [0.2, -0.25, 2 / 9])
    assert report["max_drawdown"].value == pytest.approx(0.25)
    assert report["longest_drawdown_days"].value == 2
    assert report["recovery_days"].reason == "unrecovered_drawdown"
    recovered = realized_statistics(dates(4), [0.2, -0.25, 2 / 9, 1 / 11])
    assert recovered["recovery_days"].value == 3
    loss = realized_statistics(dates(2), [-1, 0])
    assert loss["max_drawdown"].value == 1
    assert loss["longest_drawdown_days"].value == 2


def test_short_and_constant_records_have_typed_undefined_ratios() -> None:
    report = realized_statistics(dates(3), [0.01] * 3)
    assert report["annualized_volatility"].value == 0
    assert report["sharpe"].reason == "zero_volatility"
    assert report["sortino"].reason == "zero_downside_deviation"
    assert report["skewness"].reason == "zero_volatility"
    assert report["excess_kurtosis"].reason == "insufficient_observations"
    assert report["annualized_return"].reason == "window_shorter_than_one_year"
    assert report["calmar"].value is None
    assert realized_statistics(dates(1), [0.01])["annualized_volatility"].reason == (
        "insufficient_observations"
    )
    assert all(item.reason == "no_observations" for item in realized_statistics([], []).values())


def test_complete_month_links_and_partial_months() -> None:
    report = realized_statistics(dates(61), [0.01] + [0] * 30 + [-0.02] + [0] * 29)
    assert report["best_month"].value == pytest.approx(0.01)
    assert report["worst_month"].value == pytest.approx(-0.02)
    assert report["best_month"].observations == 2
    assert realized_statistics(dates(20), [0] * 20)["best_month"].reason == (
        "no_complete_calendar_months"
    )


def test_annual_geometric_link_and_total_loss() -> None:
    result = realized_statistics(dates(365), [0.1] + [0] * 364)
    assert result["annualized_return"].value == pytest.approx(0.1)
    assert result["calmar"].reason == "zero_drawdown"
    assert realized_statistics(dates(365), [-1.0] + [0.0] * 364)["annualized_return"].value == -1


def test_fractional_tail_mass_is_not_inclusive_quantile_average() -> None:
    report = realized_statistics(dates(4), [-0.4, -0.2, 0.1, 0.3], confidence=0.625)
    assert report["realized_var"].value == pytest.approx(0.1625)
    assert report["realized_cvar"].value == pytest.approx(1 / 3)
    assert report["effective_tail_observations"].value == 1.5
    assert report["skewness"].value == pytest.approx(0, abs=1e-14)
    # Centered values ±.35, ±.15 give m2=.0725 and m4=.00775625.
    assert report["excess_kurtosis"].value == pytest.approx(-2.4328180737217617)


def test_small_nonzero_denominators_are_not_treated_as_zero() -> None:
    result = realized_statistics(dates(2), [1e-150, -1e-150])
    assert result["annualized_volatility"].value == pytest.approx(
        sqrt(730) * 1e-150, rel=1e-12, abs=0
    )
    assert result["sharpe"].value == 0


@pytest.mark.parametrize("values", [[float("nan")], [float("inf")], [-1.01], [True]])
def test_malformed_returns_rejected(values: list[float]) -> None:
    with pytest.raises(ValueError):
        realized_statistics(dates(1), values)


def test_bad_dates_and_assumptions_rejected() -> None:
    for ds in [dates(2), [date(2025, 1, 1), date(2025, 1, 3)]]:
        with pytest.raises(ValueError):
            realized_statistics(ds, [0.1] if len(ds) == 2 and ds[1].day == 2 else [0.1, 0.2])
    for rf, confidence in [(-1, 0.95), (float("nan"), 0.95), (0, 1), (0, 0)]:
        with pytest.raises(ValueError):
            realized_statistics(dates(1), [0], rf, confidence)
    with pytest.raises(ValueError):
        xirr([(date(2025, 1, 1), Decimal("NaN"))])


def test_metric_never_serializes_nonfinite_or_ambiguous_output() -> None:
    for payload in [
        dict(value=float("nan"), reason=None, observations=1),
        dict(value=None, reason=None, observations=1),
        dict(value=1, reason="bad", observations=1),
        dict(value=1, reason="", observations=1),
        dict(value=True, reason=None, observations=1),
    ]:
        with pytest.raises(ValidationError):
            Metric.model_validate(payload)


def test_nonzero_skew_and_kurtosis_use_unbiased_corrections() -> None:
    report = realized_statistics(dates(4), [0, 0, 0, 0.4])
    assert report["skewness"].value == pytest.approx(2)
    assert report["excess_kurtosis"].value == pytest.approx(4)


def test_risk_free_rate_is_annual_effective() -> None:
    daily_rate = 1.1 ** (1 / 365) - 1
    report = realized_statistics(dates(2), [daily_rate - 0.01, daily_rate + 0.01], 0.1)
    assert report["sharpe"].value == pytest.approx(0, abs=1e-10)


def test_overflow_is_typed_and_tail_can_be_negative() -> None:
    report = realized_statistics(dates(365), [1e100] * 365)
    assert report["annualized_return"].reason == "non_finite_result"
    assert report["realized_var"].value == -1e100
    assert report["realized_cvar"].value == pytest.approx(-1e100)
    large = realized_statistics(dates(2), [1e308, -1])
    assert large["annualized_volatility"].reason == "non_finite_result"


def test_xirr_sorts_dates_and_supports_reverse_conventional_schedule() -> None:
    result = xirr([(date(2026, 1, 1), Decimal(-110)), (date(2025, 1, 1), Decimal(100))])
    assert result.value == pytest.approx(0.1, abs=1e-12)
