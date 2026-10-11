"""Hand-derived matched interval, coverage, provenance and replay acceptance."""

from datetime import UTC, datetime
from math import prod, sqrt
from typing import Any

import pytest
from pydantic import ValidationError
from src.attribution.engine import build_contribution
from src.benchmark.contracts import BenchmarkEvidence, ComparisonReport
from src.benchmark.engine import active_statistics, build_comparison
from src.benchmark.replay import verify_comparison

from tests.test_performance_engine import funded, report, request, transaction


def evidence(*levels: str | None) -> BenchmarkEvidence:
    return BenchmarkEvidence.model_validate(
        dict(
            identity=dict(
                benchmark_id="analytical-total-return",
                revision="reviewed-1",
                name="Synthetic analytical benchmark",
                provider="Hand-derived test evidence",
                methodology_reference="Explicit total-return fixture, not a market index",
                currency="GBP",
                return_basis="net_total_return",
                hedging="not_applicable",
                calendar="UTC_calendar_daily",
                periods_per_year=365,
                currency_policy="already_in_portfolio_currency",
                effective_from="2025-01-01",
                effective_to="2025-12-31",
                published_at="2025-01-01T20:00:00Z",
                retrieved_at="2025-01-31T20:00:00Z",
            ),
            levels=[
                dict(
                    date=f"2025-01-{index + 1:02d}",
                    level=value,
                    observed_at=f"2025-01-{index + 1:02d}T20:00:00Z",
                    published_at=f"2025-01-{index + 1:02d}T21:00:00Z",
                    retrieved_at="2025-01-31T20:00:00Z",
                    source="Synthetic total-return level",
                )
                for index, value in enumerate(levels)
            ],
        )
    )


def measured() -> ComparisonReport:
    performance = report(funded(), request("100", "102", "106.08", "112.4448", expected_version=2))
    result = build_comparison(performance, evidence("100", "101", "103.02", "106.1106"))
    verify_comparison(ComparisonReport.model_validate_json(result.model_dump_json()))
    return result


def test_analytical_geometric_returns_active_moments_and_beta() -> None:
    result = measured()
    assert result.expected_intervals == result.paired_intervals == 3
    assert result.benchmark_return.value == pytest.approx(0.061106)
    assert result.performance.twr.value == pytest.approx(0.124448)
    assert result.cumulative_active_return.value == pytest.approx(0.063342)
    assert result.cumulative_relative_return.value == pytest.approx(112.4448 / 106.1106 - 1)
    stats = result.statistics
    assert stats["mean_daily_active_return"].value == pytest.approx(0.02)
    assert stats["annualized_arithmetic_active_return"].value == pytest.approx(0.02 * 365)
    assert stats["annualized_tracking_error"].value == pytest.approx(0.01 * sqrt(365))
    assert stats["information_ratio"].value == pytest.approx(2 * sqrt(365))
    assert stats["beta"].value == pytest.approx(2)
    assert stats["correlation"].value == pytest.approx(1)
    assert all(metric.observations == 3 for metric in stats.values())
    relative_values = [row.relative_return.value for row in result.daily]
    assert all(value is not None for value in relative_values)
    assert prod(
        1 + float(value) for value in relative_values if value is not None
    ) - 1 == pytest.approx(result.cumulative_relative_return.value)
    # Daily arithmetic differences neither geometrically link nor equal cumulative difference.
    active_values = [row.active_return.value for row in result.daily]
    assert sum(value for value in active_values if value is not None) != pytest.approx(
        result.cumulative_active_return.value
    )


def test_identical_series_zero_active_risk_and_undefined_information_ratio() -> None:
    performance = report(funded(), request("100", "110", "121"))
    result = build_comparison(performance, evidence("100", "110", "121"))
    assert result.cumulative_active_return.value == 0
    assert result.cumulative_relative_return.value == 0
    assert result.statistics["annualized_tracking_error"].value == 0
    assert result.statistics["information_ratio"].reason == "zero_tracking_error"
    # Constant benchmark returns have no centered beta/correlation denominator.
    assert result.statistics["beta"].reason == "zero_benchmark_variance"


def test_negative_beta_correlation_and_active_mean_are_not_clamped() -> None:
    result = active_statistics([(0.02, -0.01), (0.0, 0.0), (-0.02, 0.01)], 3)
    assert result["beta"].value == pytest.approx(-2)
    assert result["correlation"].value == pytest.approx(-1)
    assert result["information_ratio"].value == 0
    assert active_statistics([(-0.01, 0), (-0.02, 0.01)], 2)["information_ratio"].value < 0  # type: ignore[operator]


def test_constant_portfolio_keeps_valid_zero_beta_but_undefined_correlation() -> None:
    stats = active_statistics([(0, -0.01), (0, 0.01)], 2)
    assert stats["beta"].value == 0
    assert stats["correlation"].reason == "zero_portfolio_or_benchmark_variance"
    assert stats["annualized_tracking_error"].value == pytest.approx(0.01 * sqrt(2 * 365))


@pytest.mark.parametrize(
    "pairs,expected,reason",
    [
        ([], 1, "incomplete_paired_coverage"),
        ([(0, 0)], 1, "insufficient_observations"),
        ([(0.1, 0.2), (0.2, 0.3)], 3, "incomplete_paired_coverage"),
    ],
)
def test_no_partial_sample_or_one_observation_statistics(
    pairs: list[tuple[float, float]], expected: int, reason: str
) -> None:
    result = active_statistics(pairs, expected)
    assert all(m.value is None and m.reason == reason for m in result.values())
    assert all(m.observations == len(pairs) for m in result.values())


@pytest.mark.parametrize("kind", ["omit", "explicit_null", "stale"])
def test_missing_middle_level_withholds_full_window_but_keeps_independent_performance(
    kind: str,
) -> None:
    performance = measured().performance
    marks = evidence("100", "101", "103.02", "106.1106")
    if kind == "omit":
        del marks.levels[1]
    elif kind == "explicit_null":
        marks.levels[1].level = None
    else:
        marks.levels[1].observed_at = datetime(2025, 1, 1, 20, tzinfo=UTC)
    result = build_comparison(performance, marks)
    assert result.performance.twr.value == pytest.approx(0.124448)
    assert result.benchmark_return.reason == "incomplete_benchmark_coverage"
    assert result.paired_intervals == 1
    assert all(m.reason == "incomplete_paired_coverage" for m in result.statistics.values())
    assert result.daily[2].benchmark_return.value == pytest.approx(0.03)


def test_missing_portfolio_mark_retains_independent_complete_benchmark() -> None:
    result = build_comparison(
        report(funded(), request("100", None, "121")), evidence("100", "110", "121")
    )
    assert result.benchmark_return.value == pytest.approx(0.21)
    assert result.performance.twr.value is None
    assert result.cumulative_active_return.value is None
    assert result.paired_intervals == 0


def test_window_before_first_funding_has_no_false_matched_cumulative_comparison() -> None:
    rows = funded()
    for row in rows:
        row.effective_at = row.effective_at.replace(day=2)
    performance = report(rows, request(None, "100", "110", expected_version=2))
    result = build_comparison(performance, evidence("100", "105", "110"))
    assert result.performance.twr.value == pytest.approx(0.1)
    assert result.benchmark_return.value == pytest.approx(0.1)
    assert result.cumulative_active_return.reason == "portfolio_not_funded_at_opening"
    assert result.cumulative_relative_return.value is None
    assert result.paired_intervals == 1
    assert result.statistics["beta"].reason == "incomplete_paired_coverage"
    verify_comparison(result)


def test_explicit_utc_quote_age_allowance_does_not_automatically_fill_a_date() -> None:
    marks = evidence("100", "110")
    marks.levels[1].observed_at = datetime.fromisoformat("2025-01-01T23:30:00-02:00")
    result = build_comparison(report(funded(), request("100", "120")), marks)
    assert result.benchmark_return.value == pytest.approx(0.1)
    marks.levels[1].observed_at = datetime(2025, 1, 1, 20, tzinfo=UTC)
    marks.max_level_age_days = 1
    assert build_comparison(result.performance, marks).benchmark_return.value == pytest.approx(0.1)
    marks.levels.pop()
    assert build_comparison(result.performance, marks).benchmark_return.value is None


@pytest.mark.parametrize(
    "levels,reason",
    [
        (("0", "100"), "zero_benchmark_start_level"),
        (("100", "0", "110"), "benchmark_recovery_after_zero_level"),
    ],
)
def test_zero_initial_wealth_or_recovery_is_not_a_continuous_return(
    levels: tuple[str, ...], reason: str
) -> None:
    result = build_comparison(report(funded(), request(*["100"] * len(levels))), evidence(*levels))
    assert result.benchmark_return.reason == reason
    assert result.cumulative_active_return.value is None


def test_total_loss_benchmark_has_valid_loss_and_active_difference_but_no_relative_ratio() -> None:
    result = build_comparison(report(funded(), request("100", "110")), evidence("100", "0"))
    assert result.benchmark_return.value == -1
    assert result.cumulative_active_return.value == pytest.approx(1.1)
    assert result.cumulative_relative_return.reason == "zero_benchmark_wealth"
    assert result.daily[0].relative_return.value is None


def test_funding_and_costs_compare_flow_neutral_twr_not_nav_growth() -> None:
    rows = [
        *funded(),
        transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="110"),
        transaction(4, "FEE", "2025-01-03T12:00:00Z", amount="10"),
    ]
    from tests.test_performance_engine import price

    req = request(
        "100",
        "120",
        "130",
        expected_version=4,
        flow_marks=[
            dict(transaction_id=str(rows[2].id), prices=[price("110", "2025-01-02T12:00:00Z")])
        ],
    )
    performance = report(rows, req)
    contribution = build_contribution(performance)
    result = build_comparison(performance, evidence("100", "105", "110"), contribution)
    assert result.performance.daily[-1].nav == 230
    assert result.performance.twr.value == pytest.approx(0.15)
    assert result.cumulative_active_return.value == pytest.approx(0.05)
    assert result.cumulative_relative_return.value == pytest.approx(1.15 / 1.1 - 1)
    assert result.contribution == contribution
    verify_comparison(ComparisonReport.model_validate_json(result.model_dump_json()))


@pytest.mark.parametrize(
    "change",
    [
        "currency",
        "effective_start",
        "effective_end",
        "version_future",
        "observation_future",
        "retrieval_future",
        "outside_window",
    ],
)
def test_incompatible_or_future_benchmark_is_rejected(change: str) -> None:
    performance = report(funded(), request("100", "110"))
    marks = evidence("100", "110")
    if change == "currency":
        marks.identity.currency = "USD"
    elif change == "effective_start":
        marks.identity.effective_from = datetime(2025, 1, 2).date()
    elif change == "effective_end":
        marks.identity.effective_to = datetime(2025, 1, 1).date()
    elif change == "version_future":
        marks.identity.retrieved_at = datetime(2026, 1, 1, tzinfo=UTC)
    elif change == "observation_future":
        marks.levels[1].observed_at = datetime(2025, 1, 3, tzinfo=UTC)
    elif change == "retrieval_future":
        marks.levels[1].retrieved_at = datetime(2026, 1, 1, tzinfo=UTC)
    else:
        marks.levels[1].date = datetime(2025, 1, 3).date()
    with pytest.raises(ValueError):
        build_comparison(performance, marks)


@pytest.mark.parametrize(
    "change",
    [
        "price_only",
        "calendar",
        "year",
        "duplicates",
        "unsorted",
        "float",
        "negative",
        "nan",
        "provenance",
        "version_provenance",
    ],
)
def test_strict_evidence_contract_rejects_ambiguous_or_invalid_inputs(change: str) -> None:
    data = evidence("100", "110").model_dump(mode="json")
    if change == "price_only":
        data["identity"]["return_basis"] = "price_return"
    elif change == "calendar":
        data["identity"]["calendar"] = "trading_daily"
    elif change == "year":
        data["identity"]["periods_per_year"] = 252
    elif change == "duplicates":
        data["levels"].append(data["levels"][0])
    elif change == "unsorted":
        data["levels"].reverse()
    elif change in ("float", "negative", "nan"):
        data["levels"][0]["level"] = {"float": 100.1, "negative": "-1", "nan": "NaN"}[change]
    elif change == "provenance":
        data["levels"][0]["retrieved_at"] = "2024-01-01T00:00:00Z"
    else:
        data["identity"]["retrieved_at"] = "2024-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        BenchmarkEvidence.model_validate(data)


@pytest.mark.parametrize(
    "change", ["evidence", "revision", "statistic", "daily", "methodology", "contribution_setting"]
)
def test_replay_rejects_modified_inputs_results_and_conventions(change: str) -> None:
    result = measured()
    data: dict[str, Any] = result.model_dump(mode="json")
    if change == "evidence":
        data["benchmark"]["levels"][0]["level"] = "99"
    elif change == "revision":
        data["benchmark"]["identity"]["revision"] = "different"
    elif change == "statistic":
        data["statistics"]["beta"]["value"] = 3.0
    elif change == "daily":
        data["daily"][0]["active_return"]["value"] = 0.5
    elif change == "methodology":
        data["methodology"] = "different"
    else:
        data["include_contribution"] = True
    with pytest.raises(ValueError):
        verify_comparison(ComparisonReport.model_validate(data))


def test_snapshot_mismatch_and_numerical_overflow_are_honest_failures() -> None:
    original = measured().performance
    other = report(funded(), request("100", "110", "121"))
    with pytest.raises(ValueError, match="snapshot"):
        build_comparison(original, measured().benchmark, build_contribution(other))
    stats = active_statistics([(1e308, 0), (-1e308, 1)], 2)
    assert all(m.value is None and m.reason == "non_finite_result" for m in stats.values())
