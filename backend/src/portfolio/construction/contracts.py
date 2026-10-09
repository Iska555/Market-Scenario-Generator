"""Typed common units, aligned history and explicitly adopted investor views."""

import math
from datetime import date
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from src.research.schemas import Currency
from src.valuation.contracts import (
    Contract,
    Finite,
    Growth,
    Metric,
    Rate,
    ReturnSample,
    Text,
    UserViewRequest,
)

Weight = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Strategy = Literal["current", "equal_weight", "minimum_variance", "maximum_sharpe", "risk_parity"]


def default_strategies() -> list[Strategy]:
    return ["current", "equal_weight", "minimum_variance", "maximum_sharpe", "risk_parity"]


class JointObservation(Contract):
    start: date
    end: date
    returns: Annotated[list[Rate], Field(min_length=1, max_length=30)]


class JointHistory(Contract):
    security_ids: Annotated[list[UUID], Field(min_length=1, max_length=30)]
    observations: Annotated[list[JointObservation], Field(min_length=2, max_length=5000)]
    frequency: Literal["daily", "weekly", "monthly", "annual"]
    periods_per_year: Annotated[int, Field(ge=1, le=366, strict=True)]
    source: Text
    retrieved_at: AwareDatetime
    adjustment_policy: Text
    interval_alignment: Literal["identical_start_end_and_valuation_cutoff"]
    return_basis: Literal["total"] = "total"
    money_basis: Literal["nominal"] = "nominal"

    @model_validator(mode="after")
    def aligned(self) -> Self:
        if len(set(self.security_ids)) != len(self.security_ids):
            raise ValueError("History security IDs must be unique")
        if any(len(row.returns) != len(self.security_ids) for row in self.observations):
            raise ValueError("Each history row must match the ordered security IDs")
        # Share Phase 5's explicit calendar/frequency sanity contract.
        ReturnSample.model_validate(
            {
                "observations": [
                    {"start": row.start, "end": row.end, "security_return": row.returns[0]}
                    for row in self.observations
                ],
                "frequency": self.frequency,
                "periods_per_year": self.periods_per_year,
                "source": self.source,
                "retrieved_at": self.retrieved_at,
                "adjustment_policy": self.adjustment_policy,
                "interval_alignment": self.interval_alignment,
            }
        )
        if self.retrieved_at.date() < self.observations[-1].end:
            raise ValueError("History retrieval cannot precede its final interval")
        return self


class PositionBounds(Contract):
    min_position_weight: Weight = 0
    max_position_weight: Weight = 1
    long_only: Literal[True] = True

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.min_position_weight > self.max_position_weight:
            raise ValueError("Minimum position weight cannot exceed maximum")
        return self


class PortfolioAsset(Contract):
    security_id: UUID
    current_weight: Weight
    investor_view: UserViewRequest | None = None


class ConstructionRequest(Contract):
    assets: Annotated[list[PortfolioAsset], Field(min_length=1, max_length=30)]
    history: JointHistory
    valuation_date: date
    currency: Currency
    valuation_calendar: Text
    as_of: AwareDatetime
    known_at: AwareDatetime
    risk_free_rate: Growth
    risk_free_convention: Literal["annual_effective"] = "annual_effective"
    covariance_estimator: Literal["ledoit_wolf", "sample"] = "ledoit_wolf"
    annualization_assumption: Literal["iid_period_covariance"] = "iid_period_covariance"
    constraints: PositionBounds = Field(default_factory=PositionBounds)
    strategies: Annotated[list[Strategy], Field(min_length=1, max_length=5)] = Field(
        default_factory=default_strategies
    )

    @model_validator(mode="after")
    def coherent(self) -> Self:
        identifiers = [asset.security_id for asset in self.assets]
        if identifiers != self.history.security_ids:
            raise ValueError("Portfolio and history must use identical ordered security IDs")
        if not math.isclose(
            sum(a.current_weight for a in self.assets), 1, rel_tol=0, abs_tol=1e-10
        ):
            raise ValueError("Declared current weights must sum to one")
        if len(set(self.strategies)) != len(self.strategies):
            raise ValueError("Strategies must be unique")
        if (
            self.as_of.date() > self.valuation_date
            or self.history.observations[-1].end > self.as_of.date()
        ):
            raise ValueError("History/publication cutoff cannot follow valuation date")
        if self.history.retrieved_at > self.known_at:
            raise ValueError("History unavailable under knowledge cutoff")
        n = len(self.assets)
        if (
            n * self.constraints.min_position_weight > 1 + 1e-10
            or n * self.constraints.max_position_weight < 1 - 1e-10
        ):
            raise ValueError("Position bounds cannot form a fully invested portfolio")
        for asset in self.assets:
            if asset.investor_view is None:
                continue
            c = asset.investor_view.context
            if (
                c.security_id != asset.security_id
                or c.horizon_years != 1
                or c.return_basis != "total"
                or c.money_basis != "nominal"
                or c.currency_basis != "local"
                or c.local_currency != self.currency
                or c.valuation_currency != self.currency
                or c.valuation_date != self.valuation_date
                or c.as_of > self.as_of
                or c.known_at > self.known_at
                or c.valuation_calendar != self.valuation_calendar
            ):
                raise ValueError(
                    "Adopted views require matching one-year nominal total-return context"
                )
        return self


class AssetContribution(Contract):
    security_id: UUID
    weight: Weight
    annualized_asset_volatility: Finite
    marginal_risk_contribution: Metric
    component_risk_contribution: Finite
    percentage_risk_contribution: Metric
    expected_return_assumption: Metric
    expected_return_contribution: Metric


class PortfolioRiskReport(Contract):
    current_covariance_volatility: Finite
    expected_portfolio_return: Metric
    expected_excess_return: Metric
    expected_sharpe_ratio: Metric
    horizon_years: Literal[1] = 1
    return_basis: Literal["nominal_total_return"] = "nominal_total_return"
    weight_basis: str = "Declared or candidate initial security weights, fully invested"
    weight_concentration_hhi: Finite
    effective_number_of_positions: Finite
    absolute_risk_concentration_hhi: Metric
    assets: list[AssetContribution]


class SolverInfo(Contract):
    method: str
    converged: bool
    iterations: int
    objective: Finite | None = None
    diagnostic: str


class StrategyResult(Contract):
    strategy: Strategy
    status: Literal["available", "unavailable"]
    reason: str | None = None
    weights: list[Weight] | None = None
    report: PortfolioRiskReport | None = None
    constraints_satisfied: bool | None = None
    constraint_violations: list[str] = Field(default_factory=list)
    solver: SolverInfo | None = None


class CovarianceReport(Contract):
    annualized_simple_return_covariance: list[list[Finite]]
    correlation: list[list[Finite | None]]
    estimator: str
    shrinkage: Finite
    periods_per_year: int
    frequency: str
    observation_count: int
    window_start: date
    window_end: date
    positive_definite: bool
    uncertainty: str = (
        "Historical covariance estimate; IID annualization; "
        "parameter/model uncertainty not propagated"
    )


class ConstructionResult(Contract):
    kind: Literal["portfolio_construction"] = "portfolio_construction"
    currency: Currency
    valuation_date: date
    covariance: CovarianceReport
    comparisons: list[StrategyResult]
    interpretation: str = (
        "Conditional portfolio alternatives, not holdings, forecasts, orders "
        "or investment recommendations"
    )
    optimizer_warning: str = (
        "Maximum Sharpe is highly sensitive to expected-return assumptions; "
        "compare minimum variance and risk parity"
    )
