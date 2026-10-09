"""Pure deterministic replay; no database or provider access."""

from datetime import datetime
from decimal import Decimal, localcontext
from uuid import UUID

from src.accounting.contracts import Cash, LedgerState, Position, TransactionRead
from src.accounting.precision import accounting_context


def replay(
    portfolio_id: UUID,
    base_currency: str,
    rows: list[TransactionRead],
    as_of: datetime,
    known_at: datetime,
) -> LedgerState:
    """Restate economic history using only records available by known_at."""
    if any(row.portfolio_id != portfolio_id for row in rows):
        raise ValueError("Every transaction must belong to this portfolio")
    visible = [r for r in rows if r.recorded_at <= known_at]
    canceled = {r.reverses_id for r in visible if r.type == "REVERSAL"}
    active = sorted(
        (
            r
            for r in visible
            if r.type != "REVERSAL" and r.id not in canceled and r.effective_at <= as_of
        ),
        key=lambda r: (r.effective_at, r.sequence),
    )
    cash: dict[str, Decimal] = {}
    positions: dict[UUID, Position] = {}
    with localcontext(accounting_context()):
        for row in active:
            delta = Decimal(0)
            if row.type in ("BUY", "SELL"):
                assert row.security_id is not None and row.quantity is not None
                assert row.price is not None
                position = positions.setdefault(
                    row.security_id,
                    Position(
                        security_id=row.security_id,
                        currency=row.currency,
                        quantity=Decimal(0),
                        cost_basis=Decimal(0),
                        average_cost=Decimal(0),
                    ),
                )
                if position.currency != row.currency:
                    raise ValueError("Position currency changes require explicit reconciliation")
                gross = row.quantity * row.price
                if row.type == "BUY":
                    position.quantity += row.quantity
                    position.cost_basis += gross + row.fees
                    delta = -gross - row.fees
                else:
                    if row.quantity > position.quantity:
                        raise ValueError("Insufficient position for sale")
                    if row.quantity == position.quantity:
                        position.cost_basis = Decimal(0)
                    else:
                        position.cost_basis -= (
                            position.cost_basis * row.quantity / position.quantity
                        )
                    position.quantity -= row.quantity
                    delta = gross - row.fees
                position.average_cost = (
                    position.cost_basis / position.quantity if position.quantity else Decimal(0)
                )
            elif row.type in ("DEPOSIT", "DIVIDEND"):
                assert row.amount is not None
                delta = row.amount
            elif row.type in ("WITHDRAWAL", "FEE"):
                assert row.amount is not None
                delta = -row.amount
            elif row.type == "FX_CONVERSION":
                assert row.amount is not None and row.to_amount is not None
                assert row.to_currency is not None
                delta = -row.amount - row.fees
                cash[row.to_currency] = cash.get(row.to_currency, Decimal(0)) + row.to_amount
            cash[row.currency] = cash.get(row.currency, Decimal(0)) + delta
            if cash[row.currency] < 0:
                raise ValueError("Insufficient running cash; supply full funding history")
        return LedgerState(
            portfolio_id=portfolio_id,
            base_currency=base_currency,
            version=max((r.sequence for r in visible), default=0),
            as_of=as_of,
            known_at=known_at,
            cash=[Cash(currency=c, amount=v) for c, v in sorted(cash.items())],
            positions=[p for _, p in sorted(positions.items()) if p.quantity],
            active_transaction_ids=[r.id for r in active],
        )
