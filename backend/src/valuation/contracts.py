"""Phase 5 units, horizons, evidence and model-specific contracts."""

import math
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from src.research.schemas import Currency

Finite = Annotated[float, Field(allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Rate = Annotated[float, Field(ge=-1, allow_inf_nan=False)]
Growth = Annotated[float, Field(gt=-1, allow_inf_nan=False)]
ExactRate = Annotated[Decimal, Field(ge=-1, allow_inf_nan=False, max_digits=30, decimal_places=15)]
Text = Annotated[str, Field(min_length=1, max_length=2000)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReturnContext(Contract):
    security_id: UUID
    valuation_date: date
    horizon_years: Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)]
    return_basis: Literal["price", "total"]
    money_basis: Literal["nominal", "real"]
    currency_basis: Literal["local", "base"]
    valuation_currency: Currency
    local_currency: Currency
    valuation_calendar: Text
    as_of: AwareDatetime
    known_at: AwareDatetime
    observation_ids: Annotated[list[UUID], Field(max_length=100)] = Field(default_factory=list)
    thesis_revision_id: UUID | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.currency_basis == "local" and self.local_currency != self.valuation_currency:
            raise ValueError("Local return must use the local currency")
        if self.as_of.date() > self.valuation_date:
            raise ValueError("Evidence publication cutoff cannot follow valuation date")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("Evidence IDs must be unique")
        return self


class ReturnPair(Contract):
    annualized_return: Rate
    cumulative_return: Rate
    horizon_years: Positive
    annualization: Literal["equivalent_compound_rate"] = "equivalent_compound_rate"

    @model_validator(mode="after")
    def reconcile(self) -> Self:
        try:
            expected = (
                math.expm1(self.horizon_years * math.log1p(self.annualized_return))
                if self.annualized_return > -1
                else -1.0
            )
        except (ValueError, OverflowError) as exc:
            raise ValueError("Return conversion exceeds numerical domain") from exc
        if not math.isclose(expected, self.cumulative_return, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError("Annualized and cumulative returns are inconsistent")
        return self


class Metric(Contract):
    value: Finite | None
    reason: str | None = None
    observation_count: int | None = None

    @model_validator(mode="after")
    def defined(self) -> Self:
        if (self.value is None) != (self.reason is not None):
            raise ValueError("Undefined metrics require a reason; defined metrics have none")
        return self


class Uncertainty(Contract):
    lower_annualized: Rate | None = None
    upper_annualized: Rate | None = None
    confidence_statement: Text | None = None
    parameter_uncertainty: Text = "Not propagated"
    model_uncertainty: Text = "Assumption-dependent; not quantified"
    sampling_uncertainty: Text = "No Monte Carlo sampling in this calculation"

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if (self.lower_annualized is None) != (self.upper_annualized is None):
            raise ValueError("Uncertainty bounds require both endpoints")
        if self.lower_annualized is not None and self.upper_annualized is not None:
            if self.lower_annualized > self.upper_annualized:
                raise ValueError("Uncertainty bounds must be ordered")
        return self


class UserViewRequest(Contract):
    model: Literal["user_specified"] = "user_specified"
    context: ReturnContext
    annualized_return: ExactRate | None = None
    cumulative_return: ExactRate | None = None
    rationale: Text
    reference: Text | None = None
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)

    @model_validator(mode="after")
    def explicit_rate(self) -> Self:
        if self.annualized_return is None and self.cumulative_return is None:
            raise ValueError("An explicit annualized or cumulative return is required")
        return self


class ReturnObservation(Contract):
    start: date
    end: date
    security_return: Rate
    benchmark_return: Rate | None = None

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.start >= self.end:
            raise ValueError("Return interval start must precede end")
        return self


class ReturnSample(Contract):
    observations: Annotated[list[ReturnObservation], Field(min_length=1, max_length=10000)]
    frequency: Literal["daily", "weekly", "monthly", "annual"]
    periods_per_year: Annotated[int, Field(ge=1, le=366, strict=True)]
    source: Text
    retrieved_at: AwareDatetime
    adjustment_policy: Text
    interval_alignment: Literal["identical_start_end_and_valuation_cutoff"]

    @model_validator(mode="after")
    def coherent_sample(self) -> Self:
        expected = {"weekly": 52, "monthly": 12, "annual": 1}
        if self.frequency in expected and self.periods_per_year != expected[self.frequency]:
            raise ValueError("Frequency and periods per year disagree")
        if self.frequency == "daily" and self.periods_per_year < 200:
            raise ValueError("Daily observations require an explicit daily annualization")
        low, high = {"daily": (1, 7), "weekly": (5, 9), "monthly": (25, 35), "annual": (350, 380)}[
            self.frequency
        ]
        if any(not low <= (row.end - row.start).days <= high for row in self.observations):
            raise ValueError("Return interval duration is inconsistent with declared frequency")
        for previous, current in zip(self.observations, self.observations[1:], strict=False):
            if previous.end > current.start:
                raise ValueError("Intervals must be sorted, unique and nonoverlapping")
        return self


class HistoricalRequest(Contract):
    model: Literal["historical"] = "historical"
    context: ReturnContext
    sample: ReturnSample


class CapmRequest(Contract):
    model: Literal["capm"] = "capm"
    context: ReturnContext
    sample: ReturnSample
    benchmark: Text
    risk_free_rate: Growth
    equity_risk_premium: Finite
    assumption_source: Text
    risk_free_convention: Literal["annual_effective"] = "annual_effective"
    horizon_assumption: Literal["iid_annual_gross_mean"]


class ResearchAssumptionSet(Contract):
    metric: Literal["eps", "fcf_per_share"]
    current_price: Positive
    current_fundamental_per_share: Positive
    annual_per_share_growth: Growth
    terminal_multiple: Positive
    annual_cash_dividend: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    spot_fx_base_per_local: Positive = 1
    terminal_fx_base_per_local: Positive = 1
    rationale: Text
    price_source: Text
    price_observed_at: AwareDatetime
    buyback_treatment: Literal["included_in_per_share_growth"] = "included_in_per_share_growth"
    dividend_treatment: Literal["cash_held_without_reinvestment_terminal_fx"] = (
        "cash_held_without_reinvestment_terminal_fx"
    )


class FundamentalRequest(Contract):
    model: Literal["fundamental"] = "fundamental"
    context: ReturnContext
    assumptions: ResearchAssumptionSet


class ScenarioInput(Contract):
    name: Literal["bear", "base", "bull"]
    assumptions: ResearchAssumptionSet
    probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None


class ScenarioSetRequest(Contract):
    model: Literal["scenario_set"] = "scenario_set"
    context: ReturnContext
    scenarios: Annotated[list[ScenarioInput], Field(min_length=3, max_length=3)]
    probability_source: Text | None = None
    probability_type: Literal["user_assumption", "model_assumption"] | None = None

    @model_validator(mode="after")
    def probability_contract(self) -> Self:
        if {s.name for s in self.scenarios} != {"bear", "base", "bull"}:
            raise ValueError("Exactly one bear, base and bull scenario is required")
        probabilities = [s.probability for s in self.scenarios if s.probability is not None]
        if probabilities:
            if len(probabilities) != 3 or not math.isclose(sum(probabilities), 1, abs_tol=1e-10):
                raise ValueError("Explicit probabilities must all be supplied and sum to one")
            if not self.probability_source or not self.probability_type:
                raise ValueError("Probability source and assumption type are required")
        elif self.probability_source is not None or self.probability_type is not None:
            raise ValueError("Probability metadata requires probabilities")
        first = self.scenarios[0].assumptions
        for scenario in self.scenarios[1:]:
            for field in (
                "current_price",
                "current_fundamental_per_share",
                "metric",
                "spot_fx_base_per_local",
                "price_observed_at",
            ):
                if getattr(scenario.assumptions, field) != getattr(first, field):
                    raise ValueError("Scenarios must share the same current valuation anchor")
        return self


class ReverseRequest(Contract):
    model: Literal["reverse"] = "reverse"
    context: ReturnContext
    assumptions: ResearchAssumptionSet
    required_annualized_return: Rate
    solve_for: Literal["terminal_multiple"] = "terminal_multiple"


EvaluationRequest = Annotated[
    UserViewRequest
    | HistoricalRequest
    | CapmRequest
    | FundamentalRequest
    | ScenarioSetRequest
    | ReverseRequest,
    Field(discriminator="model"),
]


class Regression(Contract):
    beta: Metric
    beta_standard_error: Metric
    r_squared: Metric
    intercept_per_period: Metric
    observation_count: int
    estimator: str = "OLS with intercept on aligned arithmetic excess period returns; IID SE"


class ReturnEstimate(Contract):
    context: ReturnContext
    returns: ReturnPair | None
    undefined_reason: str | None = None
    interpretation: str
    uncertainty: Uncertainty
    regression: Regression | None = None


class ExpectedReturnView(ReturnEstimate):
    kind: Literal["investor_view"] = "investor_view"
    model: Literal["user_specified"] = "user_specified"
    input: UserViewRequest


class CapmEstimate(ReturnEstimate):
    kind: Literal["model_estimate"] = "model_estimate"
    model: Literal["capm"] = "capm"
    input: CapmRequest


class HistoricalDiagnostic(Contract):
    kind: Literal["historical_diagnostic"] = "historical_diagnostic"
    label: str = "Historical estimate — not a forward forecast"
    context: ReturnContext
    annualized_arithmetic_mean: Metric
    annualized_mean_standard_error: Metric
    observation_count: int
    window_start: date
    window_end: date
    frequency: str
    periods_per_year: int
    annualization: str = "A * mean(simple period returns); IID SE = A * sample_sd / sqrt(n)"
    uncertainty: Uncertainty


class ValuationModelResult(Contract):
    kind: Literal["valuation_result"] = "valuation_result"
    model: Literal["fundamental"] = "fundamental"
    context: ReturnContext
    assumptions: ResearchAssumptionSet
    returns: ReturnPair
    terminal_fundamental_per_share: Positive
    terminal_price_local: Positive
    cash_dividends_local: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    terminal_wealth_valuation_currency: Positive
    growth_factor: Positive
    multiple_factor: Positive
    dividend_wealth_factor: Positive
    fx_factor: Positive
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)


class SecurityScenario(Contract):
    name: str
    probability: float | None
    valuation: ValuationModelResult


class ScenarioSetResult(Contract):
    kind: Literal["scenario_set"] = "scenario_set"
    context: ReturnContext
    scenarios: list[SecurityScenario]
    probability_weighted_return: ReturnPair | None
    probability_source: str | None
    probability_type: str | None
    interpretation: str = (
        "Conditional scenarios; weighted terminal wealth only with explicit probabilities. "
        "No automatic investor view."
    )


class ReverseResult(Contract):
    kind: Literal["reverse_valuation"] = "reverse_valuation"
    context: ReturnContext
    required_terminal_multiple: Metric
    required_return: ReturnPair
    held_fixed: ResearchAssumptionSet
    solved_field: str = "terminal_multiple; supplied terminal_multiple is ignored"


EvaluationOutput = Annotated[
    ExpectedReturnView
    | CapmEstimate
    | HistoricalDiagnostic
    | ValuationModelResult
    | ScenarioSetResult
    | ReverseResult,
    Field(discriminator="kind"),
]
