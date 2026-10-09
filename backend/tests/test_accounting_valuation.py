"""Known-answer valuation with missing-data and currency boundaries."""

from datetime import timedelta
from decimal import ROUND_DOWN, Context, Decimal, Inexact, localcontext

import pytest
from src.accounting.contracts import FX, Price

from tests.test_accounting_domain import ASSET, T, state, transaction


def test_complete_price_and_fx_reconciles_nav_cash_and_unrealized() -> None:
    from src.accounting.contracts import ValuationRequest
    from src.accounting.valuation import value_state

    ledger = state(
        [
            transaction("DEPOSIT", 1, amount="1000", currency="USD"),
            transaction(
                "BUY", 2, security_id=ASSET, currency="USD", quantity="2", price="100", fees="2"
            ),
        ]
    )
    request = ValuationRequest(
        as_of=ledger.as_of,
        prices=[
            Price.model_validate(
                dict(
                    security_id=ASSET,
                    currency="USD",
                    price="150",
                    observed_at=T + timedelta(days=100),
                    source="fixture",
                )
            )
        ],
        fx=[
            FX.model_validate(
                dict(
                    currency="USD",
                    rate="0.8",
                    observed_at=T + timedelta(days=100),
                    source="fixture",
                )
            )
        ],
    )
    result = value_state(ledger, request)
    assert result.nav == Decimal("878.4")
    assert result.positions[0].market_value_local == 300
    assert result.positions[0].unrealized_pnl_local == 98
    assert result.positions[0].translated_unrealized_pnl_base == Decimal("78.4")
    assert result.cash[0].value_base == Decimal("638.4")
    assert result.cash[0].weight is not None and result.positions[0].weight is not None
    assert abs(result.cash[0].weight + result.positions[0].weight - 1) < Decimal("1e-55")


def test_partial_marks_never_produce_partial_nav_or_weights() -> None:
    from src.accounting.contracts import ValuationRequest
    from src.accounting.valuation import value_state

    ledger = state(
        [
            transaction("DEPOSIT", 1, amount="1000"),
            transaction("BUY", 2, security_id=ASSET, quantity="2", price="100"),
        ]
    )
    result = value_state(ledger, ValuationRequest(as_of=ledger.as_of))
    assert result.nav is None
    assert result.reason == "incomplete_valuation"
    assert result.positions[0].reason == "missing_price"
    assert result.cash[0].value_base == 800
    assert result.cash[0].weight is None


def test_zero_nav_is_not_fabricated_weights() -> None:
    from src.accounting.contracts import ValuationRequest
    from src.accounting.valuation import value_state

    result = value_state(state([]), ValuationRequest(as_of=T + timedelta(days=100)))
    assert result.nav == 0
    assert result.reason == "zero_nav"


@pytest.mark.parametrize(
    "change",
    [
        {"currency": "USD"},
        {"observed_at": T + timedelta(days=101)},
    ],
)
def test_bad_price_context_rejected(change: dict) -> None:
    from src.accounting.contracts import ValuationRequest
    from src.accounting.valuation import value_state

    ledger = state(
        [
            transaction("DEPOSIT", 1, amount="100"),
            transaction("BUY", 2, security_id=ASSET, quantity="1", price="100"),
        ]
    )
    price = dict(security_id=ASSET, currency="GBP", price="100", observed_at=T, source="s") | change
    with pytest.raises(ValueError):
        value_state(
            ledger, ValuationRequest(as_of=ledger.as_of, prices=[Price.model_validate(price)])
        )


def test_valid_large_price_and_fx_product_retains_all_exact_digits() -> None:
    from src.accounting.contracts import ValuationRequest
    from src.accounting.valuation import value_state

    ledger = state(
        [
            transaction("DEPOSIT", 1, amount="2", currency="USD"),
            transaction(
                "BUY", 2, security_id=ASSET, currency="USD", quantity="1.0000000001", price="1"
            ),
        ]
    )
    price = Price.model_validate(
        dict(
            security_id=ASSET,
            currency="USD",
            price="99999999999999999999.1234567891",
            observed_at=T,
            source="fixture",
        )
    )
    rate = FX.model_validate(
        dict(
            currency="USD", rate="99999999999999999999.9876543219", observed_at=T, source="fixture"
        )
    )
    request = ValuationRequest(as_of=ledger.as_of, prices=[price], fx=[rate])
    with localcontext(Context(prec=200)):
        expected_position = Decimal("1.0000000001") * price.price * rate.rate
        expected_nav = expected_position + Decimal("0.9999999999") * rate.rate
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        result = value_state(ledger, request)
    assert result.positions[0].market_value_base == expected_position
    assert result.nav == expected_nav
