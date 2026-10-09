"""Stable arithmetic independent of ambient Decimal settings."""

from decimal import ROUND_HALF_EVEN, Context, DivisionByZero, InvalidOperation, Overflow


def accounting_context() -> Context:
    # Inputs have <=30 digits. Three-factor marks plus <=20,000-row totals
    # require <100 digits; 120 leaves room for exact cash/NAV aggregation.
    # Proportional basis, translated rounded basis, and weights may be recurring.
    return Context(
        prec=120,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )
