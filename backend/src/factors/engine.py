"""Centered/scaled SVD OLS and HC3 inference on complete funded daily intervals."""

from datetime import UTC
from math import sqrt

import numpy as np

from src.attribution.contracts import ContributionReport
from src.benchmark.contracts import ComparisonReport
from src.benchmark.engine import metric
from src.factors.contracts import (
    Coefficient,
    FactorEvidence,
    FactorReport,
    RegressionInterval,
)
from src.performance.contracts import PerformanceReport
from src.performance.engine import close
from src.performance.identity import digest
from src.performance.metrics import Metric

MINIMUM = 30
CONDITION_LIMIT = 1e8
STATS = (
    "r_squared",
    "adjusted_r_squared",
    "residual_standard_deviation",
    "scaled_condition_number",
)
WARNINGS = [
    "Historical factor coefficients and daily alpha are model-dependent sample estimates, "
    "not forecasts, causal effects or evidence of persistent skill.",
    "Response is portfolio daily simple return minus supplied period-effective risk-free return. "
    "Excess-market and long-short factors are used as supplied, not reduced by risk-free again.",
    "HC3 standard errors address heteroskedasticity, not serial correlation. T-statistics are "
    "descriptive; no p-values, significance decisions, HAC or bootstrap inference are supplied.",
    "Complete funded UTC daily intervals, at least 30 observations, 365 periods/year. "
    "Trading-day/percentage/foreign-currency research data require explicit review; no fill or FX.",
    "Model choice, factors, risk-free values and provenance are supplied, not independently "
    "certified. Exposure can change over time; omitted factors and collinearity affect estimates.",
    "Alpha is a daily simple excess-return intercept, not CAGR or annualized expected return. "
    "Regression residuals and fitted values are not reconciled position-return attribution.",
]


def regress(
    response: list[float], factors: list[list[float]], ids: list[str], expected: int
) -> tuple[dict[str, Coefficient], dict[str, Metric], list[float], list[float], str | None]:
    n = len(response)
    reason = "incomplete_paired_coverage" if n != expected else "insufficient_observations"
    names = ["alpha", *ids]
    empty = metric(None, n, reason)
    coefficients = {
        name: Coefficient(coefficient=empty, standard_error=empty, t_statistic=empty)
        for name in names
    }
    stats = {name: empty for name in STATS}

    def failure(
        why: str,
    ) -> tuple[dict[str, Coefficient], dict[str, Metric], list[float], list[float], str | None]:
        missing = metric(None, n, why)
        return (
            {
                name: Coefficient(coefficient=missing, standard_error=missing, t_statistic=missing)
                for name in names
            },
            dict.fromkeys(STATS, missing),
            [],
            [],
            why,
        )

    if n != expected or n < MINIMUM:
        return coefficients, stats, [], [], reason
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            y, f = np.asarray(response, dtype=float), np.asarray(factors, dtype=float)
            if not np.all(np.isfinite(y)) or not np.all(np.isfinite(f)):
                return failure("non_finite_regression_input")
            if any(np.all(f[:, index] == f[0, index]) for index in range(len(ids))):
                return failure("constant_factor")
            means = np.mean(f, axis=0)
            centered = f - means
            scales = np.linalg.norm(centered, axis=0) / sqrt(n)
            x = np.column_stack((np.ones(n), centered / scales))
            u, singular, vt = np.linalg.svd(x, full_matrices=False)
            tolerance = max(x.shape) * np.finfo(float).eps * singular[0]
            if singular[-1] <= tolerance:
                return failure("rank_deficient_design")
            condition = singular[0] / singular[-1]
            if condition > CONDITION_LIMIT:
                return failure("ill_conditioned_design")
            inverse = (vt.T / singular) @ u.T
            scaled = inverse @ y
            transform = np.zeros((len(names), len(names)))
            transform[0, 0] = 1
            transform[0, 1:] = -means / scales
            transform[1:, 1:] = np.diag(1 / scales)
            values = transform @ scaled
            fitted = x @ scaled
            residuals = y - fitted
            sse = float(residuals @ residuals)
            df = n - len(names)
            tss = float((y - np.mean(y)) @ (y - np.mean(y)))
            constant_response = bool(np.all(y == y[0]))
            r2 = None if constant_response or tss == 0 else 1 - sse / tss
            stats = {
                "r_squared": metric(r2, n, "zero_response_variance"),
                "adjusted_r_squared": metric(
                    None if r2 is None else 1 - (1 - r2) * (n - 1) / df,
                    n,
                    "zero_response_variance",
                ),
                "residual_standard_deviation": metric(sqrt(sse / df), n),
                "scaled_condition_number": metric(condition, n),
            }
            # A declared backward-error test withholds misleading exact-fit inference.
            exact = np.linalg.norm(residuals) <= 64 * np.finfo(float).eps * max(
                np.linalg.norm(y), np.linalg.norm(fitted)
            )
            leverage_gap = 1 - np.sum(u * u, axis=1)
            inference_reason = (
                "numerically_exact_fit"
                if exact
                else (
                    "high_leverage_design"
                    if np.min(leverage_gap) <= 64 * np.finfo(float).eps
                    else None
                )
            )
            errors = (
                None
                if inference_reason
                else np.linalg.norm(
                    (transform @ inverse) * (residuals / leverage_gap)[None, :], axis=1
                )
            )
            for index, name in enumerate(names):
                se = None if errors is None else float(errors[index])
                coefficients[name] = Coefficient(
                    coefficient=metric(float(values[index]), n),
                    standard_error=metric(se, n, inference_reason or "non_finite_result"),
                    t_statistic=metric(
                        float(values[index]) / se if se else None,
                        n,
                        inference_reason or "zero_standard_error",
                    ),
                )
            return coefficients, stats, fitted.tolist(), residuals.tolist(), None
    except (FloatingPointError, OverflowError, ValueError, np.linalg.LinAlgError):
        return failure("numerical_regression_failure")


def build_factor_report(
    performance: PerformanceReport,
    evidence: FactorEvidence,
    contribution: ContributionReport | None = None,
    comparison: ComparisonReport | None = None,
) -> FactorReport:
    identity = evidence.identity
    if identity.currency != performance.base_currency:
        raise ValueError("Factor currency must match the portfolio")
    if identity.effective_from > performance.start or identity.effective_to < performance.end:
        raise ValueError("Factor revision must cover the complete report window")
    if identity.retrieved_at > performance.manifest.inputs.known_at:
        raise ValueError("Factor revision exceeds the knowledge cutoff")
    dates = {day.date for day in performance.daily[1:]}
    for row in evidence.rows:
        if row.date not in dates:
            raise ValueError("Factor rows must match portfolio interval closing dates")
        if row.observed_at.astimezone(UTC).date() != row.date or row.observed_at > close(row.date):
            raise ValueError("Factor observation must belong to its actual interval closing day")
        if row.retrieved_at > performance.manifest.inputs.known_at:
            raise ValueError("Factor evidence exceeds the knowledge cutoff")
    if contribution is not None and contribution.performance != performance:
        raise ValueError("Factor and contribution reports must share one snapshot")
    if comparison is not None and (
        comparison.performance != performance or comparison.contribution != contribution
    ):
        raise ValueError("Factor and comparison reports must share one snapshot and settings")
    ids = [factor.factor_id for factor in identity.factors]
    if "alpha" in ids:
        raise ValueError("The alpha identifier is reserved for the intercept")
    marks = {row.date: row for row in evidence.rows}
    daily: list[RegressionInterval] = []
    responses: list[float] = []
    matrix: list[list[float]] = []
    for opening, closing in zip(performance.daily, performance.daily[1:], strict=False):
        mark = marks.get(closing.date)
        pr = (
            closing.daily_return
            if opening.units is not None and opening.units > 0
            else metric(None, 0, "portfolio_not_funded_at_interval_start")
        )
        rf = metric(
            mark.risk_free_return if mark else None,
            1 if mark and mark.risk_free_return is not None else 0,
            "missing_risk_free_return",
        )
        factors = {
            name: metric(
                mark.factor_returns.get(name) if mark else None,
                1 if mark and mark.factor_returns.get(name) is not None else 0,
                "missing_factor_return",
            )
            for name in ids
        }
        excess = metric(
            pr.value - rf.value if pr.value is not None and rf.value is not None else None,
            1 if pr.value is not None and rf.value is not None else 0,
            pr.reason or rf.reason or "missing_excess_return",
        )
        if excess.value is not None and all(item.value is not None for item in factors.values()):
            responses.append(excess.value)
            matrix.append(
                [float(item.value) for item in factors.values() if item.value is not None]
            )
        daily.append(
            RegressionInterval(
                start=opening.date,
                end=closing.date,
                portfolio_return=pr,
                risk_free_return=rf,
                excess_return=excess,
                factor_returns=factors,
                fitted_excess_return=metric(None, 0, "regression_not_fitted"),
                residual=metric(None, 0, "regression_not_fitted"),
            )
        )
    coefficients, stats, fitted, residuals, reason = regress(responses, matrix, ids, len(daily))
    for index, day in enumerate(daily):
        day.fitted_excess_return = metric(
            fitted[index] if fitted else None, len(responses), reason or "regression_not_fitted"
        )
        day.residual = metric(
            residuals[index] if residuals else None,
            len(responses),
            reason or "regression_not_fitted",
        )
    return FactorReport(
        performance=performance,
        contribution=contribution,
        comparison=comparison,
        factors=evidence,
        factors_sha256=digest(evidence.model_dump(mode="json")),
        include_contribution=contribution is not None,
        expected_intervals=len(daily),
        paired_intervals=len(responses),
        residual_degrees_of_freedom=len(daily) - len(ids) - 1 if reason is None else None,
        fit_reason=reason,
        coefficients=coefficients,
        statistics=stats,
        daily=daily,
        warnings=[*WARNINGS]
        + (
            ["Short sample: fewer than 365 daily intervals; inference is unstable."]
            if len(responses) < 365
            else []
        ),
    )
