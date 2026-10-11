"""Independent analytical OLS/HC3 identities, interval provenance and replay."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from math import sqrt

import pytest
from pydantic import ValidationError
from src.attribution.engine import build_contribution
from src.benchmark.engine import build_comparison
from src.factors.contracts import FactorEvidence, FactorReport
from src.factors.engine import build_factor_report, regress
from src.factors.replay import verify_factor_report
from src.performance.contracts import PerformanceRequest

from tests.test_benchmark_engine import evidence as benchmark_evidence
from tests.test_performance_engine import funded, price, report, transaction


def factor_evidence(n: int = 32) -> FactorEvidence:
    return FactorEvidence.model_validate(
        dict(
            identity=dict(
                model_id="synthetic-market",
                revision="reviewed-v1",
                name="Synthetic research factor",
                provider="Hand-derived acceptance",
                methodology_reference="Synthetic, not public market data",
                currency="GBP",
                currency_policy="already_in_portfolio_currency",
                calendar="UTC_calendar_daily",
                periods_per_year=365,
                units="decimal_simple_return",
                risk_free_convention="period_effective_return",
                effective_from="2025-01-01",
                effective_to="2025-12-31",
                published_at="2025-01-01T20:00:00Z",
                retrieved_at="2025-03-01T00:00:00Z",
                factors=[
                    dict(
                        factor_id="market",
                        name="Market",
                        convention="excess_market_return",
                        description="Explicit reviewed excess-market return",
                    )
                ],
            ),
            rows=[
                dict(
                    date=(date(2025, 1, 2) + timedelta(days=i)).isoformat(),
                    risk_free_return="0.0001",
                    factor_returns={"market": str([-0.02, -0.01, 0.01, 0.02][i % 4])},
                    observed_at=(date(2025, 1, 2) + timedelta(days=i)).isoformat() + "T20:00:00Z",
                    published_at=(date(2025, 1, 2) + timedelta(days=i)).isoformat() + "T21:00:00Z",
                    retrieved_at="2025-03-01T00:00:00Z",
                    source="Synthetic daily research factors",
                )
                for i in range(n)
            ],
        )
    )


def measured(n: int = 32) -> FactorReport:
    levels = [Decimal(100)]
    for i in range(n):
        growth = (
            Decimal("1.0001")
            + Decimal("0.002")
            + Decimal("1.5") * Decimal(str([-0.02, -0.01, 0.01, 0.02][i % 4]))
            + Decimal(str([0.001, -0.001, -0.001, 0.001][i % 4]))
        )
        levels.append((levels[-1] * growth).quantize(Decimal("0.0000000001")))
    req = PerformanceRequest.model_validate(
        dict(
            expected_version=2,
            known_at="2025-03-01T00:00:00Z",
            daily_marks=[
                dict(
                    date=(date(2025, 1, 1) + timedelta(days=i)).isoformat(),
                    prices=[
                        price(
                            str(value),
                            (date(2025, 1, 1) + timedelta(days=i)).isoformat() + "T20:00:00Z",
                        )
                    ],
                )
                for i, value in enumerate(levels)
            ],
        )
    )
    performance = report(funded(), req)
    return build_factor_report(performance, factor_evidence(n), build_contribution(performance))


def test_analytical_hc3_single_factor_coefficients_errors_and_residual_identity() -> None:
    x = [-0.02, -0.01, 0.01, 0.02] * 8
    e = [0.001, -0.001, -0.001, 0.001] * 8
    y = [0.002 + 1.5 * a + b for a, b in zip(x, e, strict=True)]
    coefficients, stats, fitted, residuals, reason = regress(y, [[a] for a in x], ["market"], 32)
    assert reason is None
    assert coefficients["alpha"].coefficient.value == pytest.approx(0.002)
    assert coefficients["market"].coefficient.value == pytest.approx(1.5)
    xx = sum(a * a for a in x)
    weights = [b / (1 - 1 / 32 - a * a / xx) for a, b in zip(x, e, strict=True)]
    alpha_se = sqrt(sum(w * w for w in weights)) / 32
    beta_se = sqrt(sum((a * w) ** 2 for a, w in zip(x, weights, strict=True))) / xx
    assert coefficients["alpha"].standard_error.value == pytest.approx(alpha_se)
    assert coefficients["market"].standard_error.value == pytest.approx(beta_se)
    assert coefficients["alpha"].t_statistic.value == pytest.approx(0.002 / alpha_se)
    assert coefficients["market"].t_statistic.value == pytest.approx(1.5 / beta_se)
    assert stats["r_squared"].value == pytest.approx(
        1 - sum(b * b for b in e) / sum((v - 0.002) ** 2 for v in y)
    )
    assert stats["residual_standard_deviation"].value == pytest.approx(
        sqrt(sum(b * b for b in e) / 30)
    )
    assert sum(residuals) == pytest.approx(0, abs=1e-15)
    assert sum(a * b for a, b in zip(x, residuals, strict=True)) == pytest.approx(0, abs=1e-15)
    assert all(p + r == pytest.approx(v) for p, r, v in zip(fitted, residuals, y, strict=True))


def test_centered_multifactor_negative_coefficients_and_nonzero_factor_means() -> None:
    f = [[0.03 + [-0.02, -0.01, 0.01, 0.02][i % 4], [-0.01, 0.01][(i // 4) % 2]] for i in range(32)]
    y = [0.004 - 2 * a + 0.5 * b for a, b in f]
    coefficients, stats, _, _, reason = regress(y, f, ["market", "value"], 32)
    assert reason is None
    assert coefficients["alpha"].coefficient.value == pytest.approx(0.004)
    assert coefficients["market"].coefficient.value == pytest.approx(-2)
    assert coefficients["value"].coefficient.value == pytest.approx(0.5)
    assert stats["r_squared"].value == pytest.approx(1)
    assert all(c.standard_error.reason == "numerically_exact_fit" for c in coefficients.values())


@pytest.mark.parametrize(
    "case, expected",
    [
        ("gap", "incomplete_paired_coverage"),
        ("short", "insufficient_observations"),
        ("constant", "constant_factor"),
        ("duplicate", "rank_deficient_design"),
        ("near", "ill_conditioned_design"),
        ("overflow", "numerical_regression_failure"),
        ("nan", "non_finite_regression_input"),
    ],
)
def test_regression_failure_cases_do_not_publish_partial_or_regularized_fits(
    case: str, expected: str
) -> None:
    f = [[float(i)] for i in range(32)]
    y = [float(i % 3) for i in range(32)]
    ids, count = ["market"], 32
    if case == "gap":
        count = 33
    if case == "short":
        y = y[:20]
        f = f[:20]
        count = 20
    if case == "constant":
        f = [[1.0] for _ in y]
    if case in ("duplicate", "near"):
        f = [[a[0], a[0] + (1e-8 * (i % 2) if case == "near" else 0)] for i, a in enumerate(f)]
        ids.append("value")
    if case == "overflow":
        y = [1e308] * 32
    if case == "nan":
        y[0] = float("nan")
    coefficients, stats, fitted, residuals, reason = regress(y, f, ids, count)
    assert reason == expected and not fitted and not residuals
    assert all(
        c.coefficient.value is None and c.coefficient.reason == expected
        for c in coefficients.values()
    )
    assert all(v.value is None for v in stats.values())


def test_constant_response_and_unit_leverage_withhold_unreliable_inference() -> None:
    f = [[float(i)] for i in range(32)]
    coefficients, stats, _, _, reason = regress([0.01] * 32, f, ["market"], 32)
    assert reason is None and stats["r_squared"].reason == "zero_response_variance"
    assert coefficients["alpha"].standard_error.reason == "numerically_exact_fit"
    f = [[0.0] for _ in range(31)] + [[1.0]]
    coefficients, _, _, _, reason = regress([float(i % 3) for i in range(32)], f, ["market"], 32)
    assert reason is None and coefficients["alpha"].standard_error.reason == "high_leverage_design"


def test_complete_ledger_report_excess_returns_replays_with_contribution() -> None:
    result = measured()
    assert result.fit_reason is None and result.paired_intervals == 32
    assert result.residual_degrees_of_freedom == 30
    assert result.coefficients["alpha"].coefficient.value == pytest.approx(0.002, abs=1e-10)
    assert result.coefficients["market"].coefficient.value == pytest.approx(1.5, abs=1e-9)
    assert result.daily[0].portfolio_return.value is not None
    assert result.daily[0].excess_return.value == pytest.approx(
        result.daily[0].portfolio_return.value - 0.0001
    )
    verify_factor_report(FactorReport.model_validate_json(result.model_dump_json()))


@pytest.mark.parametrize("field", ["row", "rf", "factor", "portfolio", "unfunded"])
def test_gaps_and_initial_funding_keep_independent_performance(field: str) -> None:
    result = measured()
    performance, evidence = result.performance, result.factors
    if field == "row":
        evidence.rows.pop(4)
    if field == "rf":
        evidence.rows[4].risk_free_return = None
    if field == "factor":
        evidence.rows[4].factor_returns.clear()
    if field == "portfolio":
        performance.daily[5].daily_return = performance.daily[5].daily_return.model_copy(
            update={"value": None, "reason": "coverage_gap"}
        )
    if field == "unfunded":
        performance.daily[0].units = Decimal(0)
    changed = build_factor_report(performance, evidence)
    assert changed.fit_reason == "incomplete_paired_coverage" and changed.paired_intervals == 31
    assert changed.performance.twr == performance.twr
    assert changed.coefficients["alpha"].coefficient.value is None


@pytest.mark.parametrize(
    "case",
    [
        "currency",
        "window",
        "version_future",
        "row_future",
        "outside",
        "older",
        "offset_future",
        "alpha",
        "snapshot",
    ],
)
def test_cross_report_provenance_and_snapshot_validation(case: str) -> None:
    result = measured(2)
    ev = result.factors
    contribution = None
    if case == "currency":
        ev.identity.currency = "USD"
    if case == "window":
        ev.identity.effective_from = date(2025, 1, 2)
    if case == "version_future":
        ev.identity.retrieved_at = datetime(2999, 1, 1, tzinfo=UTC)
    if case == "row_future":
        ev.rows[0].retrieved_at = datetime(2999, 1, 1, tzinfo=UTC)
    if case == "outside":
        ev.rows[0].date = date(2024, 1, 1)
    if case == "older":
        ev.rows[0].observed_at = datetime(2025, 1, 1, 20, tzinfo=UTC)
    if case == "offset_future":
        ev.rows[0].observed_at = datetime.fromisoformat("2025-01-02T23:00:00-02:00")
    if case == "alpha":
        ev.identity.factors[0].factor_id = "alpha"
    if case == "snapshot":
        assert result.contribution is not None
        contribution = result.contribution.model_copy(deep=True)
        contribution.performance.end = date(2025, 1, 4)
    with pytest.raises(ValueError):
        build_factor_report(result.performance, ev, contribution)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "order",
        "unknown",
        "float",
        "rf_loss",
        "units",
        "calendar",
        "risk_free",
        "factor_basis",
        "times",
        "duplicate_id",
        "zero_factors",
        "too_many",
    ],
)
def test_invalid_factor_evidence_contract(case: str) -> None:
    data = factor_evidence(2).model_dump(mode="json")
    if case == "duplicate":
        data["rows"].append(data["rows"][0])
    if case == "order":
        data["rows"].reverse()
    if case == "unknown":
        data["rows"][0]["factor_returns"]["invented"] = "0.01"
    if case == "float":
        data["rows"][0]["factor_returns"]["market"] = 0.01
    if case == "rf_loss":
        data["rows"][0]["risk_free_return"] = "-1"
    if case == "units":
        data["identity"]["units"] = "percent"
    if case == "calendar":
        data["identity"]["periods_per_year"] = 252
    if case == "risk_free":
        data["identity"]["risk_free_convention"] = "annual_effective"
    if case == "factor_basis":
        data["identity"]["factors"][0]["convention"] = "price_return"
    if case == "times":
        data["rows"][0]["retrieved_at"] = "2024-01-01T00:00:00Z"
    if case == "duplicate_id":
        data["identity"]["factors"].append(data["identity"]["factors"][0])
    if case == "zero_factors":
        data["identity"]["factors"] = []
    if case == "too_many":
        data["identity"]["factors"] *= 7
    with pytest.raises(ValidationError):
        FactorEvidence.model_validate(data)


@pytest.mark.parametrize(
    "case",
    [
        "evidence",
        "coefficient",
        "se",
        "residual",
        "methodology",
        "setting",
        "statistics",
        "comparison",
    ],
)
def test_offline_replay_rejects_changed_evidence_results_and_settings(case: str) -> None:
    result = measured(2 if case == "comparison" else 32)
    if case == "evidence":
        result.factors.identity.revision = "tampered"
    if case == "coefficient":
        result.coefficients["alpha"].coefficient = result.coefficients[
            "alpha"
        ].coefficient.model_copy(update={"value": 0.9})
    if case == "se":
        result.coefficients["alpha"].standard_error = result.coefficients[
            "alpha"
        ].standard_error.model_copy(update={"value": 0.9})
    if case == "residual":
        result.daily[0].residual = result.daily[0].residual.model_copy(update={"value": 0.9})
    if case == "methodology":
        result.methodology = "unknown"
    if case == "setting":
        result.include_contribution = False
    if case == "statistics":
        result.statistics["r_squared"] = result.statistics["r_squared"].model_copy(
            update={"value": 0.9}
        )
    if case == "comparison":
        result.comparison = build_comparison(
            result.performance, benchmark_evidence("100", "101", "102"), result.contribution
        )
        result.comparison.performance = result.performance.model_copy(deep=True)
        result.comparison.performance.end = date(2025, 1, 4)
    with pytest.raises(ValueError):
        verify_factor_report(result)


def test_coherent_optional_benchmark_replays_and_mismatched_settings_fail() -> None:
    result = measured(2)
    comparison = build_comparison(
        result.performance, benchmark_evidence("100", "101", "102"), result.contribution
    )
    result = build_factor_report(
        result.performance, result.factors, result.contribution, comparison
    )
    verify_factor_report(result)
    with pytest.raises(ValueError):
        build_factor_report(result.performance, result.factors, None, comparison)


def test_first_funding_actual_ledger_is_not_a_complete_factor_day() -> None:
    rows = [transaction(1, "DEPOSIT", "2025-01-02T09:00:00Z", amount="100")]
    req = PerformanceRequest.model_validate(
        dict(
            expected_version=1,
            known_at="2025-03-01T00:00:00Z",
            daily_marks=[dict(date=f"2025-01-0{i}") for i in range(1, 4)],
        )
    )
    result = build_factor_report(report(rows, req), factor_evidence(2))
    assert result.performance.twr.value == 0
    assert result.daily[0].portfolio_return.reason == "portfolio_not_funded_at_interval_start"
    assert result.paired_intervals == 1 and result.fit_reason == "incomplete_paired_coverage"
    verify_factor_report(result)


def test_six_orthogonal_factors_with_independent_hc3_errors() -> None:
    slopes = [-2, -1, 0.5, 1, 1.5, 2]
    f = [[0.01 * (-1 if (i & (j + 1)).bit_count() % 2 else 1) for j in range(6)] for i in range(64)]
    errors = [0.001 * (-1 if (i & 7).bit_count() % 2 else 1) for i in range(64)]
    y = [
        0.002 + sum(a * b for a, b in zip(row, slopes, strict=True)) + e
        for row, e in zip(f, errors, strict=True)
    ]
    ids = ["market", "size", "value", "profitability", "investment", "momentum"]
    coefficients, stats, _, residuals, reason = regress(y, f, ids, 64)
    assert reason is None
    expected_alpha_se = 0.001 / (1 - 7 / 64) / sqrt(64)
    assert coefficients["alpha"].coefficient.value == pytest.approx(0.002)
    assert coefficients["alpha"].standard_error.value == pytest.approx(expected_alpha_se)
    for name, slope in zip(ids, slopes, strict=True):
        assert coefficients[name].coefficient.value == pytest.approx(slope)
        assert coefficients[name].standard_error.value == pytest.approx(expected_alpha_se / 0.01)
    assert stats["scaled_condition_number"].value == pytest.approx(1)
    assert residuals == pytest.approx(errors)
