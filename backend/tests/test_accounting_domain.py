"""Independent accounting identities; synthetic data only."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, ROUND_UP, Decimal, Inexact, localcontext
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from src.accounting.contracts import LedgerState, TransactionRead

T = datetime(2025, 1, 1, tzinfo=UTC)
ASSET = UUID(int=1)
PORTFOLIO = UUID(int=2)


def transaction(kind: str, sequence: int, **values: object) -> TransactionRead:
    from src.accounting.contracts import TransactionRead

    return TransactionRead.model_validate(
        dict(
            type=kind,
            effective_at=T + timedelta(days=sequence),
            currency="GBP",
            source="fixture",
            external_reference=str(sequence),
            id=uuid4(),
            portfolio_id=PORTFOLIO,
            sequence=sequence,
            recorded_at=T + timedelta(days=30),
            content_sha256="a" * 64,
        )
        | values
    )


def state(rows: list[TransactionRead]) -> LedgerState:
    from src.accounting.ledger import replay

    return replay(PORTFOLIO, "GBP", rows, T + timedelta(days=100), T + timedelta(days=100))


def test_moving_average_basis_and_cash_reconcile_after_partial_and_full_sale() -> None:
    rows = [
        transaction("DEPOSIT", 1, amount="1000"),
        transaction("BUY", 2, security_id=ASSET, quantity="2", price="100", fees="2"),
        transaction("BUY", 3, security_id=ASSET, quantity="3", price="120", fees="3"),
        transaction("SELL", 4, security_id=ASSET, quantity="1", price="150", fees="1"),
    ]
    result = state(rows)
    assert result.cash[0].amount == Decimal("584")
    position = result.positions[0]
    assert (position.quantity, position.cost_basis, position.average_cost) == (
        Decimal(4),
        Decimal(452),
        Decimal(113),
    )
    closed = state([*rows, transaction("SELL", 5, security_id=ASSET, quantity="4", price="50")])
    assert closed.positions == []
    assert closed.cash[0].amount == 784


def test_fx_net_dividend_fees_and_withdrawal() -> None:
    rows = [
        transaction("DEPOSIT", 1, amount="1000"),
        transaction(
            "FX_CONVERSION",
            2,
            amount="100",
            to_currency="USD",
            to_amount="125",
            fx_rate="1.25",
            fees="2",
        ),
        transaction("DIVIDEND", 3, security_id=ASSET, amount="9", currency="USD"),
        transaction("FEE", 4, amount="4", currency="USD"),
        transaction("WITHDRAWAL", 5, amount="8"),
    ]
    assert {c.currency: c.amount for c in state(rows).cash} == {"GBP": 890, "USD": 130}


def test_reversal_restates_history_only_when_known() -> None:
    from src.accounting.ledger import replay

    original = transaction("DEPOSIT", 1, amount="100")
    reverse = transaction(
        "REVERSAL",
        2,
        effective_at=original.effective_at,
        reverses_id=original.id,
        recorded_at=T + timedelta(days=40),
    )
    old = replay(
        PORTFOLIO, "GBP", [original, reverse], T + timedelta(days=10), T + timedelta(days=35)
    )
    assert old.cash[0].amount == 100
    assert state([original, reverse]).cash == []
    assert state([original, reverse]).active_transaction_ids == []


@pytest.mark.parametrize(
    "rows,match",
    [
        ([transaction("WITHDRAWAL", 1, amount="1")], "cash"),
        ([transaction("SELL", 1, security_id=ASSET, quantity="1", price="1")], "position"),
        ([transaction("BUY", 1, security_id=ASSET, quantity="1", price="1")], "cash"),
    ],
)
def test_impossible_running_balances_rejected(rows: list, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        state(rows)


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": "-1"},
        {"amount": "NaN"},
        {"amount": "0.00000000001"},
        {"quantity": "1"},
        {"currency": "GBp"},
        {"fees": "1"},
        {"effective_at": "2025-01-01"},
        {"type": "INTEREST"},
        {"unknown": 1},
    ],
)
def test_cash_contract_rejects_ambiguity(changes: dict) -> None:
    from src.accounting.contracts import TransactionCreate

    with pytest.raises(ValidationError):
        TransactionCreate.model_validate(
            dict(
                type="DEPOSIT",
                effective_at=T,
                currency="GBP",
                amount="1",
                source="s",
                external_reference="r",
            )
            | changes
        )


def test_fx_contract_requires_exact_legs_and_rate() -> None:
    with pytest.raises(ValidationError, match="FX"):
        transaction(
            "FX_CONVERSION", 1, amount="100", to_currency="USD", to_amount="120", fx_rate="1.3"
        )


def test_backdated_input_is_sorted_and_close_has_no_rounding_dust() -> None:
    rows = [
        transaction("DEPOSIT", 1, amount="1"),
        transaction("BUY", 2, security_id=ASSET, quantity="3", price="0.1", fees="0.1"),
        transaction("SELL", 3, security_id=ASSET, quantity="1", price="0.1"),
        transaction("SELL", 4, security_id=ASSET, quantity="2", price="0.1"),
    ]
    result = state(list(reversed(rows)))
    assert result.positions == []
    assert result.cash[0].amount == Decimal("0.9")


@pytest.mark.parametrize("amount", [0.1, True])
def test_accounting_rejects_binary_float_or_boolean_amounts(amount: object) -> None:
    with pytest.raises(ValidationError, match="decimal"):
        transaction("DEPOSIT", 1, amount=amount)


def test_pure_replay_rejects_cross_portfolio_rows() -> None:
    with pytest.raises(ValueError, match="portfolio"):
        state([transaction("DEPOSIT", 1, amount="100", portfolio_id=uuid4())])


def test_replay_is_independent_of_ambient_decimal_rounding_and_traps() -> None:
    rows = [
        transaction("DEPOSIT", 1, amount="1"),
        transaction("BUY", 2, security_id=ASSET, quantity="3", price="0.1", fees="0.1"),
        transaction("SELL", 3, security_id=ASSET, quantity="1", price="0.1"),
    ]
    expected = state(rows)
    for rounding in (ROUND_DOWN, ROUND_UP):
        with localcontext() as context:
            context.prec = 6
            context.rounding = rounding
            context.traps[Inexact] = True
            assert state(rows) == expected
