"""Explicit calendar, evidence and nullable realized-performance contracts."""

from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from src.accounting.contracts import FX, Contract, Price, TransactionRead
from src.performance.metrics import Metric


class Marks(Contract):
    prices: list[Price] = Field(default_factory=list, max_length=1000)
    fx: list[FX] = Field(default_factory=list, max_length=100)


class DailyMarks(Marks):
    date: date


class FlowMarks(Marks):
    transaction_id: UUID


class PerformanceRequest(Contract):
    expected_version: int = Field(ge=0)
    known_at: AwareDatetime
    daily_marks: list[DailyMarks] = Field(min_length=2, max_length=3661)
    flow_marks: list[FlowMarks] = Field(default_factory=list, max_length=20000)
    risk_free_rate: float = Field(default=0, gt=-1, le=10, allow_inf_nan=False)
    confidence: float = Field(default=0.95, gt=0, lt=1, allow_inf_nan=False)
    max_mark_age_days: int = Field(default=3, ge=0, le=30)
    calendar: Literal["UTC_calendar_daily"] = "UTC_calendar_daily"
    price_convention: Literal["unadjusted"] = "unadjusted"
    periods_per_year: Literal[365] = 365

    @model_validator(mode="after")
    def coherent(self) -> Self:
        dates = [m.date for m in self.daily_marks]
        if any(b - a != timedelta(days=1) for a, b in pairwise(dates)):
            raise ValueError("Daily valuation dates must be ordered and consecutive")
        ids = [m.transaction_id for m in self.flow_marks]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate flow marks are ambiguous")
        return self


class DailyResult(Contract):
    date: date
    nav: Decimal | None
    units: Decimal | None
    unit_value: Decimal | None
    daily_return: Metric
    cumulative_return: Metric
    reason: str | None


class ExternalFlow(Contract):
    transaction_id: UUID
    effective_at: AwareDatetime
    currency: str
    amount: Decimal
    amount_base: Decimal | None
    nav_before: Decimal | None
    units_delta: Decimal | None
    reason: str | None


class LinkedPeriod(Contract):
    label: str
    start: date
    end: date
    partial: bool
    return_value: Metric


class PerformanceManifest(Contract):
    methodology: str = "ledger_unitization_v1"
    portfolio_id: UUID
    base_currency: str
    ledger_version: int
    known_version: int
    inputs: PerformanceRequest
    ledger_records: list[TransactionRead]
    inputs_sha256: str
    ledger_sha256: str
    git_commit_sha: str | None
    build_timestamp: str | None
    libraries: dict[str, str]
    conventions: list[str]
    code_sha256: str | None = None


class PerformanceReport(Contract):
    portfolio_id: UUID
    base_currency: str
    scope: Literal["since_inception", "selected_period"]
    start: date
    end: date
    twr: Metric
    xirr: Metric
    daily: list[DailyResult]
    external_flows: list[ExternalFlow]
    linked: dict[str, list[LinkedPeriod]]
    statistics: dict[str, Metric]
    warnings: list[str]
    manifest: PerformanceManifest
