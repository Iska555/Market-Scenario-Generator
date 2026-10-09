"""Deterministic terminal-wealth models; no probability or investor view is inferred."""

import math

from src.valuation.arithmetic import finite, from_annualized, from_cumulative
from src.valuation.contracts import (
    FundamentalRequest,
    Metric,
    ResearchAssumptionSet,
    ReturnContext,
    ReverseRequest,
    ReverseResult,
    ScenarioSetRequest,
    ScenarioSetResult,
    SecurityScenario,
    ValuationModelResult,
)


def validate_assumptions(context: ReturnContext, assumptions: ResearchAssumptionSet) -> None:
    if context.money_basis != "nominal":
        raise ValueError("Fundamental model supports nominal returns only; no inflation model")
    if assumptions.price_observed_at.date() != context.valuation_date:
        raise ValueError("Price observation must be on valuation date")
    if (
        assumptions.price_observed_at > context.as_of
        or assumptions.price_observed_at > context.known_at
    ):
        raise ValueError("Price is not available under the requested cutoffs")
    if context.local_currency == context.valuation_currency:
        if assumptions.spot_fx_base_per_local != 1 or assumptions.terminal_fx_base_per_local != 1:
            raise ValueError("Same-currency scenarios require unit FX factors")
    elif not {"spot_fx_base_per_local", "terminal_fx_base_per_local"}.issubset(
        assumptions.model_fields_set
    ):
        raise ValueError(
            "Cross-currency scenarios require explicitly supplied spot and terminal FX"
        )


def terminal_fundamental(
    context: ReturnContext, assumptions: ResearchAssumptionSet
) -> tuple[float, float]:
    try:
        factor = math.exp(context.horizon_years * math.log1p(assumptions.annual_per_share_growth))
        value = finite(assumptions.current_fundamental_per_share * factor)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Fundamental growth exceeds numerical domain") from exc
    if value <= 0:
        raise ValueError("Fundamental growth underflows numerical domain")
    return value, factor


def dividends(context: ReturnContext, assumptions: ResearchAssumptionSet) -> float:
    return (
        finite(assumptions.annual_cash_dividend * context.horizon_years)
        if context.return_basis == "total"
        else 0.0
    )


def fundamental(request: FundamentalRequest) -> ValuationModelResult:
    context, a = request.context, request.assumptions
    validate_assumptions(context, a)
    terminal, growth_factor = terminal_fundamental(context, a)
    price = finite(terminal * a.terminal_multiple)
    if price <= 0:
        raise ValueError("Terminal price underflows numerical domain")
    cash = dividends(context, a)
    wealth = finite((price + cash) * a.terminal_fx_base_per_local)
    initial = finite(a.current_price * a.spot_fx_base_per_local)
    if initial <= 0:
        raise ValueError("Initial valuation underflows numerical domain")
    cumulative = finite(wealth / initial - 1)
    if cumulative <= -1:
        raise ValueError("Positive terminal wealth falls below return numerical resolution")
    return ValuationModelResult(
        context=context,
        assumptions=a,
        returns=from_cumulative(cumulative, context.horizon_years),
        terminal_fundamental_per_share=terminal,
        terminal_price_local=price,
        cash_dividends_local=cash,
        terminal_wealth_valuation_currency=wealth,
        growth_factor=growth_factor,
        multiple_factor=finite(
            a.terminal_multiple * a.current_fundamental_per_share / a.current_price
        ),
        dividend_wealth_factor=finite(1 + cash / price),
        fx_factor=finite(a.terminal_fx_base_per_local / a.spot_fx_base_per_local),
    )


def scenario_set(request: ScenarioSetRequest) -> ScenarioSetResult:
    scenarios = [
        SecurityScenario(
            name=item.name,
            probability=item.probability,
            valuation=fundamental(
                FundamentalRequest(context=request.context, assumptions=item.assumptions)
            ),
        )
        for item in request.scenarios
    ]
    weighted = None
    if request.scenarios[0].probability is not None:
        wealth = math.fsum(
            (1 + item.valuation.returns.cumulative_return) * item.probability
            for item in scenarios
            if item.probability is not None
        )
        weighted = from_cumulative(finite(wealth - 1), request.context.horizon_years)
    return ScenarioSetResult(
        context=request.context,
        scenarios=scenarios,
        probability_weighted_return=weighted,
        probability_source=request.probability_source,
        probability_type=request.probability_type,
    )


def reverse(request: ReverseRequest) -> ReverseResult:
    context, a = request.context, request.assumptions
    validate_assumptions(context, a)
    target = from_annualized(request.required_annualized_return, context.horizon_years)
    terminal, _ = terminal_fundamental(context, a)
    wealth_local = finite(
        a.current_price
        * a.spot_fx_base_per_local
        * (1 + target.cumulative_return)
        / a.terminal_fx_base_per_local
    )
    required_price = finite(wealth_local - dividends(context, a))
    multiple = (
        Metric(value=None, reason="nonpositive_required_terminal_price")
        if required_price <= 0
        else Metric(value=finite(required_price / terminal))
    )
    if multiple.value == 0:
        multiple = Metric(value=None, reason="numerical_underflow")
    return ReverseResult(
        context=context, required_terminal_multiple=multiple, required_return=target, held_fixed=a
    )
