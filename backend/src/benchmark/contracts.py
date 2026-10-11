"""Versioned report-scoped total-return benchmark with exact dated evidence."""

from datetime import date
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from src.accounting.contracts import Contract, Currency, Nonnegative, Text
from src.attribution.contracts import ContributionReport
from src.performance.contracts import PerformanceReport, PerformanceRequest
from src.performance.metrics import Metric


class BenchmarkIdentity(Contract):
    benchmark_id: Text
    revision: Text
    name: Text
    provider: Text
    methodology_reference: Text
    currency: Currency
    return_basis: Literal["gross_total_return", "net_total_return"]
    hedging: Literal["unhedged", "hedged", "not_applicable"]
    calendar: Literal["UTC_calendar_daily"]
    periods_per_year: Literal[365]
    currency_policy: Literal["already_in_portfolio_currency"]
    effective_from: date
    effective_to: date
    published_at: AwareDatetime
    retrieved_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.effective_to < self.effective_from or self.retrieved_at < self.published_at:
            raise ValueError("Benchmark version dates are inconsistent")
        return self


class BenchmarkLevel(Contract):
    date: date
    level: Nonnegative | None
    observed_at: AwareDatetime
    published_at: AwareDatetime
    retrieved_at: AwareDatetime
    source: Text

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.published_at < self.observed_at or self.retrieved_at < self.published_at:
            raise ValueError("Benchmark observation provenance times are inconsistent")
        return self


class BenchmarkEvidence(Contract):
    identity: BenchmarkIdentity
    max_level_age_days: int = Field(default=0, ge=0, le=30)
    levels: list[BenchmarkLevel] = Field(max_length=3661)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        dates = [r.date for r in self.levels]
        if dates != sorted(set(dates)):
            raise ValueError("Benchmark dates must be unique and ordered")
        return self


class ComparisonRequest(Contract):
    performance: PerformanceRequest
    benchmark: BenchmarkEvidence
    include_contribution: bool = False


class DailyComparison(Contract):
    start: date
    end: date
    portfolio_return: Metric
    benchmark_return: Metric
    active_return: Metric
    relative_return: Metric


class ComparisonReport(Contract):
    methodology: str = "aligned_total_return_comparison_v1"
    performance: PerformanceReport
    contribution: ContributionReport | None = None
    benchmark: BenchmarkEvidence
    benchmark_sha256: str
    include_contribution: bool
    expected_intervals: int
    paired_intervals: int
    benchmark_return: Metric
    cumulative_active_return: Metric
    cumulative_relative_return: Metric
    statistics: dict[str, Metric]
    daily: list[DailyComparison]
    warnings: list[str]
