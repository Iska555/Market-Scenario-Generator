"""Exact linked decimal-return contributions and explicit reconciliation."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import model_validator

from src.accounting.contracts import CashValue, Contract, PositionValue
from src.performance.contracts import PerformanceReport


class ContributionValue(Contract):
    value: Decimal | None
    reason: str | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (self.value is None) != (self.reason is not None):
            raise ValueError("Contribution needs either a finite value or an undefined reason")
        if self.value is not None and not self.value.is_finite():
            raise ValueError("Contribution must be finite")
        return self


class Component(Contract):
    key: str
    kind: Literal["security", "cash", "account_fees", "fx_conversion"]
    security_id: UUID | None = None
    currency: str | None = None
    price: ContributionValue
    dividends: ContributionValue
    fees: ContributionValue
    fx: ContributionValue
    total: ContributionValue
    pnl_base: Decimal | None


class Segment(Contract):
    start: datetime
    end: datetime
    before_flow_id: UUID | None
    transaction_ids: list[UUID]
    units: Decimal
    opening_nav: Decimal
    closing_nav: Decimal
    opening_positions: list[PositionValue]
    opening_cash: list[CashValue]
    components: list[Component]
    linked_total: ContributionValue


class Reconciliation(Contract):
    component_total: ContributionValue
    residual: ContributionValue
    tolerance: Decimal | None
    within_tolerance: bool | None


class ContributionReport(Contract):
    methodology: str = "ledger_endpoint_contribution_v1"
    linking: str = "forward_unit_wealth_increments"
    fx_convention: str = "end_fx_for_local_pnl; opening_exposure_fx; conversion_principal_separate"
    units: str = "decimal_portfolio_return; display_percentage_points"
    performance: PerformanceReport
    components: list[Component]
    segments: list[Segment]
    top_contributors: list[str]
    bottom_contributors: list[str]
    reconciliation: Reconciliation
    warnings: list[str]
