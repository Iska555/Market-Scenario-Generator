"""Supplied-price valuation; missing coverage never becomes a complete NAV."""

from decimal import Decimal, localcontext

from src.accounting.contracts import (
    FX,
    CashValue,
    LedgerState,
    PositionValue,
    Price,
    ValuationRequest,
    ValuationResult,
)
from src.accounting.precision import accounting_context


def value_state(state: LedgerState, request: ValuationRequest) -> ValuationResult:
    prices = {p.security_id: p for p in request.prices}
    rates = {f.currency: f.rate for f in request.fx}
    if len(prices) != len(request.prices) or len(rates) != len(request.fx):
        raise ValueError("Duplicate price or FX inputs are ambiguous")
    if set(prices) - {p.security_id for p in state.positions}:
        raise ValueError("Price supplied for a security with no open position")
    currencies = {p.currency for p in state.positions} | {c.currency for c in state.cash}
    if set(rates) - currencies - {state.base_currency}:
        raise ValueError("FX supplied for an unused currency")
    marks: list[Price | FX] = [*request.prices, *request.fx]
    for mark_input in marks:
        if mark_input.observed_at > state.as_of or mark_input.observed_at > state.known_at:
            raise ValueError("Mark timestamps must not exceed valuation or knowledge cutoff")
    if state.base_currency in rates and rates[state.base_currency] != 1:
        raise ValueError("Base-currency FX rate must equal one")
    rates[state.base_currency] = Decimal(1)
    positions: list[PositionValue] = []
    cash: list[CashValue] = []
    with localcontext(accounting_context()):
        for p in state.positions:
            mark, rate = prices.get(p.security_id), rates.get(p.currency)
            if mark and mark.currency != p.currency:
                raise ValueError("Price currency must match position currency")
            local = p.quantity * mark.price if mark else None
            pnl = local - p.cost_basis if local is not None else None
            reason = "missing_price" if mark is None else "missing_fx" if rate is None else None
            positions.append(
                PositionValue(
                    **p.model_dump(),
                    market_value_local=local,
                    unrealized_pnl_local=pnl,
                    market_value_base=local * rate
                    if local is not None and rate is not None
                    else None,
                    translated_unrealized_pnl_base=pnl * rate
                    if pnl is not None and rate is not None
                    else None,
                    weight=None,
                    reason=reason,
                )
            )
        for c in state.cash:
            rate = rates.get(c.currency)
            value = Decimal(0) if c.amount == 0 else c.amount * rate if rate is not None else None
            cash.append(
                CashValue(
                    **c.model_dump(),
                    value_base=value,
                    weight=None,
                    reason="missing_fx" if value is None else None,
                )
            )
        complete = all(p.market_value_base is not None for p in positions) and all(
            c.value_base is not None for c in cash
        )
        nav = (
            (
                sum(
                    (p.market_value_base for p in positions if p.market_value_base is not None),
                    Decimal(0),
                )
                + sum((c.value_base for c in cash if c.value_base is not None), Decimal(0))
            )
            if complete
            else None
        )
        reason = "incomplete_valuation" if nav is None else "zero_nav" if nav == 0 else None
        if nav is not None and nav > 0:
            for p in positions:
                assert p.market_value_base is not None
                p.weight = p.market_value_base / nav
            for c in cash:
                assert c.value_base is not None
                c.weight = c.value_base / nav
        return ValuationResult(
            state=state, positions=positions, cash=cash, nav=nav, reason=reason, inputs=request
        )
