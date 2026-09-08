"""Research metric vocabulary and guarded arithmetic; see docs/RESEARCH_METRICS.md."""

from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import Literal


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    category: str
    unit: Literal["currency", "ratio", "fraction"]


METRICS: dict[str, MetricDefinition] = {
    metric.key: metric
    for metric in (
        MetricDefinition("market_cap", "Market capitalisation", "valuation", "currency"),
        MetricDefinition("enterprise_value", "Enterprise value", "valuation", "currency"),
        MetricDefinition("pe", "P/E", "valuation", "ratio"),
        MetricDefinition("forward_pe", "Forward P/E", "valuation", "ratio"),
        MetricDefinition("ev_ebit", "EV/EBIT", "valuation", "ratio"),
        MetricDefinition("ev_ebitda", "EV/EBITDA", "valuation", "ratio"),
        MetricDefinition("price_book", "Price/book", "valuation", "ratio"),
        MetricDefinition("price_sales", "Price/sales", "valuation", "ratio"),
        MetricDefinition("fcf_yield", "Free cash flow yield", "valuation", "fraction"),
        MetricDefinition("earnings_yield", "Earnings yield", "valuation", "fraction"),
        MetricDefinition("roe", "Return on equity", "profitability", "fraction"),
        MetricDefinition("roic", "Return on invested capital", "profitability", "fraction"),
        MetricDefinition("gross_margin", "Gross margin", "profitability", "fraction"),
        MetricDefinition("operating_margin", "Operating margin", "profitability", "fraction"),
        MetricDefinition("net_margin", "Net margin", "profitability", "fraction"),
        MetricDefinition(
            "fcf_conversion", "Free cash flow conversion", "profitability", "fraction"
        ),
        MetricDefinition("revenue_growth", "Revenue growth", "growth", "fraction"),
        MetricDefinition("eps_growth", "EPS growth", "growth", "fraction"),
        MetricDefinition("fcf_growth", "Free cash flow growth", "growth", "fraction"),
        MetricDefinition("net_debt", "Net debt", "balance_sheet", "currency"),
        MetricDefinition("net_debt_ebitda", "Net debt/EBITDA", "balance_sheet", "ratio"),
        MetricDefinition("interest_coverage", "Interest coverage", "balance_sheet", "ratio"),
        MetricDefinition("current_ratio", "Current ratio", "balance_sheet", "ratio"),
        MetricDefinition("dividends", "Cash dividends paid", "capital_allocation", "currency"),
        MetricDefinition("buybacks", "Share repurchases", "capital_allocation", "currency"),
        MetricDefinition("share_dilution", "Share dilution", "capital_allocation", "fraction"),
        MetricDefinition("capex", "Capital expenditure", "capital_allocation", "currency"),
        MetricDefinition(
            "acquisitions", "Acquisition expenditure", "capital_allocation", "currency"
        ),
    )
}


@dataclass(frozen=True)
class CalculationResult:
    value: Decimal | None
    reason: str | None


def _validate_operand(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")


def ratio(numerator: Decimal, denominator: Decimal) -> CalculationResult:
    """Divide with a positive denominator, retaining a negative numerator's sign.

    The caller establishes compatible currency, period and accounting basis.
    No percentage scaling, quantization or float conversion is performed.
    Arithmetic uses the caller's Decimal context.
    """
    _validate_operand(numerator, "numerator")
    _validate_operand(denominator, "denominator")
    if denominator <= 0:
        return CalculationResult(None, "denominator must be positive")
    try:
        value = numerator / denominator
    except DecimalException as exc:
        raise ValueError("ratio cannot be represented in the Decimal context") from exc
    if not value.is_finite():
        raise ValueError("ratio cannot be represented in the Decimal context")
    return CalculationResult(value, None)


def growth(current: Decimal, previous: Decimal) -> CalculationResult:
    """Return (current - previous) / previous for a strictly positive prior base.

    A loss-to-profit transition has no conventional percentage growth here.
    Comparable periods and consistently adjusted per-share inputs are caller duties.
    """
    _validate_operand(current, "current")
    _validate_operand(previous, "previous")
    if previous <= 0:
        return CalculationResult(None, "previous value must be positive")
    try:
        change = current - previous
    except DecimalException as exc:
        raise ValueError("growth cannot be represented in the Decimal context") from exc
    if not change.is_finite():
        raise ValueError("growth cannot be represented in the Decimal context")
    return ratio(change, previous)
