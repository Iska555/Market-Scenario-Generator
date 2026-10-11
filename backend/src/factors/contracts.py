"""Strict reviewed factor/risk-free interval evidence and nullable fit outputs."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BeforeValidator, Field, model_validator

from src.accounting.contracts import Contract, Currency, Text, exact_decimal
from src.attribution.contracts import ContributionReport
from src.benchmark.contracts import BenchmarkEvidence, ComparisonReport
from src.performance.contracts import PerformanceReport, PerformanceRequest
from src.performance.metrics import Metric

Return = Annotated[Decimal, Field(max_digits=30, decimal_places=10), BeforeValidator(exact_decimal)]


class FactorDefinition(Contract):
    factor_id: Text
    name: Text
    convention: Literal["excess_market_return", "long_short_spread_return"]
    description: Text


class FactorIdentity(Contract):
    model_id: Text
    revision: Text
    name: Text
    provider: Text
    methodology_reference: Text
    currency: Currency
    currency_policy: Literal["already_in_portfolio_currency"]
    calendar: Literal["UTC_calendar_daily"]
    periods_per_year: Literal[365]
    units: Literal["decimal_simple_return"]
    risk_free_convention: Literal["period_effective_return"]
    effective_from: date
    effective_to: date
    published_at: AwareDatetime
    retrieved_at: AwareDatetime
    factors: list[FactorDefinition] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        ids = [factor.factor_id for factor in self.factors]
        if len(ids) != len(set(ids)):
            raise ValueError("Factor identifiers must be unique")
        if self.effective_to < self.effective_from or self.retrieved_at < self.published_at:
            raise ValueError("Factor model provenance dates are inconsistent")
        return self


class FactorRow(Contract):
    date: date
    risk_free_return: Return | None
    factor_returns: dict[str, Return | None] = Field(max_length=6)
    observed_at: AwareDatetime
    published_at: AwareDatetime
    retrieved_at: AwareDatetime
    source: Text

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.risk_free_return is not None and self.risk_free_return <= -1:
            raise ValueError("A period-effective risk-free return must exceed -100%")
        if self.published_at < self.observed_at or self.retrieved_at < self.published_at:
            raise ValueError("Factor observation provenance times are inconsistent")
        return self


class FactorEvidence(Contract):
    identity: FactorIdentity
    rows: list[FactorRow] = Field(max_length=3660)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        dates = [row.date for row in self.rows]
        if dates != sorted(set(dates)):
            raise ValueError("Factor dates must be unique and ordered")
        ids = {factor.factor_id for factor in self.identity.factors}
        if any(set(row.factor_returns) - ids for row in self.rows):
            raise ValueError("Undeclared factor identifiers are not permitted")
        return self


class FactorRequest(Contract):
    performance: PerformanceRequest
    factors: FactorEvidence
    include_contribution: bool = False
    benchmark: BenchmarkEvidence | None = None


class Coefficient(Contract):
    coefficient: Metric
    standard_error: Metric
    t_statistic: Metric


class RegressionInterval(Contract):
    start: date
    end: date
    portfolio_return: Metric
    risk_free_return: Metric
    excess_return: Metric
    factor_returns: dict[str, Metric]
    fitted_excess_return: Metric
    residual: Metric


class FactorReport(Contract):
    methodology: str = "funded_daily_ols_hc3_v1"
    covariance_estimator: str = "HC3_heteroskedasticity_robust"
    performance: PerformanceReport
    contribution: ContributionReport | None = None
    comparison: ComparisonReport | None = None
    factors: FactorEvidence
    factors_sha256: str
    include_contribution: bool
    expected_intervals: int
    paired_intervals: int
    minimum_observations: int = 30
    residual_degrees_of_freedom: int | None
    fit_reason: str | None
    coefficients: dict[str, Coefficient]
    statistics: dict[str, Metric]
    daily: list[RegressionInterval]
    warnings: list[str]
